"""
CodeExec AI - FastAPI Application
Serves the web UI, REST API for code execution, and MCP SSE transport.
All 11 Features Enabled:
  1. Secure Sandbox  2. Smart Data Analysis  3. Explanation Engine
  4. Session Memory  5. Visualization  6. Multi-Step Execution
  7. Debug Mode  8. Optimization Suggestions  9. Export
  10. Plugin Architecture  11. Error Recovery
"""

import os
import asyncio
import json
import uuid
import traceback
import logging
import re
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from mcp.server.sse import SseServerTransport
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from mcp_server import server as mcp_server_instance
from executor import execute_python_code, validate_python_code
import prompts
import supabase_helper

load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY", "your_huggingface_token_here")
HF_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
hf_client = InferenceClient(token=HF_API_KEY) if HF_API_KEY else None

logger = logging.getLogger("codeexec")

# --- Pydantic Models ---
class CodeRequest(BaseModel):
    code: str
    timeout: int = 30
    debug: bool = False

class NaturalLanguageRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    explanation_mode: str = "technical"  # "beginner" or "technical"
    debug: bool = False

session_store: Dict[str, List[dict]] = {}

# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="CodeExec AI", lifespan=lifespan)

# Serve static files (the web UI)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Page Routes ---
@app.get("/")
async def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/home")

@app.get("/auth")
async def serve_auth():
    return FileResponse(os.path.join(STATIC_DIR, "auth.html"))

@app.get("/home")
async def serve_home():
    return FileResponse(os.path.join(STATIC_DIR, "home.html"))

@app.get("/app")
async def serve_app():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# --- Simple Auth API (in-memory) ---
import hashlib
user_store: Dict[str, dict] = {}  # email -> {name, email, password_hash}

class AuthRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

@app.post("/api/auth/signup")
async def auth_signup(req: AuthRequest):
    if not req.name or not req.email or not req.password:
        return JSONResponse(status_code=400, content={"success": False, "error": "All fields are required."})
    if req.email in user_store:
        return JSONResponse(status_code=400, content={"success": False, "error": "Email already registered."})
    if len(req.password) < 6:
        return JSONResponse(status_code=400, content={"success": False, "error": "Password must be at least 6 characters."})
    pw_hash = hashlib.sha256(req.password.encode()).hexdigest()
    user_store[req.email] = {"name": req.name, "email": req.email, "password_hash": pw_hash}
    return {"success": True, "user": {"name": req.name, "email": req.email}}

@app.post("/api/auth/login")
async def auth_login(req: AuthRequest):
    if not req.email or not req.password:
        return JSONResponse(status_code=400, content={"success": False, "error": "Email and password are required."})
    user = user_store.get(req.email)
    if not user:
        return JSONResponse(status_code=401, content={"success": False, "error": "No account found with this email."})
    pw_hash = hashlib.sha256(req.password.encode()).hexdigest()
    if user["password_hash"] != pw_hash:
        return JSONResponse(status_code=401, content={"success": False, "error": "Invalid password."})
    return {"success": True, "user": {"name": user["name"], "email": user["email"]}}


# --- REST API ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CodeExec AI", "hf_configured": bool(HF_API_KEY)}


# --- Feature 7: Debug Mode + Feature 11: Error Recovery ---
@app.post("/api/execute")
async def api_execute_code(req: CodeRequest):
    """Execute Python code with optional debug mode and auto-error-recovery."""
    debug_info = ""
    code_to_run = req.code

    if req.debug:
        is_safe, msg = validate_python_code(code_to_run)
        debug_info += f"[AST Validation] {msg}\n"
        debug_info += f"[Code Length] {len(code_to_run)} chars, {code_to_run.count(chr(10))+1} lines\n"
        debug_info += f"[Timeout] {req.timeout}s\n"

    result = execute_python_code(code_to_run, timeout=req.timeout)

    if req.debug:
        debug_info += f"[Exit Status] {'Success' if result['success'] else 'Failed'}\n"
        debug_info += f"[Exec Time] {result['execution_time_ms']}ms\n"
        if result["error"]:
            debug_info += f"[Stderr] {result['error'][:300]}\n"
        result["debug_info"] = debug_info

    # --- Feature 11: Error Auto-Recovery ---
    if not result["success"] and result["error"] and hf_client:
        error_text = result["error"]
        # Only attempt recovery for runtime errors, not security blocks
        if "Security Error" not in error_text and "blocked" not in error_text:
            try:
                fix_messages = [
                    {"role": "system", "content": prompts.SYSTEM_PROMPT_FIX},
                    {"role": "user", "content": f"Fix this Python code. Error: {error_text[:300]}\n\nCode:\n{code_to_run}"}
                ]
                fix_response = hf_client.chat_completion(
                    model=HF_MODEL,
                    messages=fix_messages,
                    max_tokens=1500,
                    temperature=0.1,
                )
                fixed_code = fix_response.choices[0].message.content.strip()
                # Strip markdown fencing if present
                if fixed_code.startswith("```"):
                    lines = fixed_code.split("\n")
                    fixed_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])


                retry_result = execute_python_code(fixed_code, timeout=req.timeout)
                if retry_result["success"]:
                    retry_result["retried"] = True
                    retry_result["original_error"] = error_text
                    retry_result["fixed_code"] = fixed_code
                    if req.debug:
                        retry_result["debug_info"] = debug_info + "[Auto-Recovery] LLM fixed the code and re-executed successfully.\n"
                    return JSONResponse(content=retry_result)
            except Exception as e:
                logger.warning(f"Auto-recovery failed: {e}")

    return JSONResponse(content=result)


@app.get("/api/examples")
async def api_get_examples():
    """Return available example templates."""
    examples = [
        {"id": "chart", "title": "📈 Sine Wave Chart", "description": "Generate a beautiful sine wave visualization"},
        {"id": "barchart", "title": "📊 Bar Chart", "description": "Programming language popularity comparison"},
        {"id": "scatter", "title": "🔬 Scatter Plot", "description": "Correlation analysis with regression line"},
        {"id": "dataframe", "title": "🗃️ Sales Report", "description": "Pandas DataFrame analysis with summary stats"},
        {"id": "fibonacci", "title": "🔢 Fibonacci", "description": "Generate Fibonacci sequence and golden ratio"},
        {"id": "sort", "title": "⚡ Sort Benchmark", "description": "Compare sorting algorithm performance"},
        {"id": "average", "title": "📐 Statistics", "description": "Calculate statistics on a dataset"},
    ]
    return JSONResponse(content=examples)


@app.get("/api/examples/{example_id}")
async def api_get_example_code(example_id: str):
    """Return the code for a specific example."""
    template = prompts.EXAMPLE_TEMPLATES.get(example_id)
    if not template:
        return JSONResponse(status_code=404, content={"error": "Example not found"})
    if example_id == "average":
        template = template.format(data="[85, 92, 78, 95, 88, 76, 91, 83, 97, 70]")
    return JSONResponse(content={"code": template})


# --- Datasets API (Supabase-backed) ---
@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """Upload a dataset file — parse it and store rows in Supabase."""
    import pandas as pd
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        dataset_name = os.path.splitext(file.filename)[0]
        contents = await file.read()

        import io
        if file_ext == '.csv':
            df = pd.read_csv(io.BytesIO(contents))
        elif file_ext in ('.xlsx', '.xls'):
            df = pd.read_excel(io.BytesIO(contents))
        elif file_ext == '.json':
            df = pd.read_json(io.BytesIO(contents))
        elif file_ext == '.tsv':
            df = pd.read_csv(io.BytesIO(contents), sep='\t')
        else:
            return JSONResponse(status_code=400, content={"error": f"Unsupported file type: {file_ext}"})

        result = supabase_helper.upload_dataset(dataset_name, df)
        if result["status"] == "success":
            return {"filename": file.filename, "status": "success", "rows": result["rows_inserted"]}
        else:
            return JSONResponse(status_code=500, content={"error": result.get("error", "Upload failed")})
    except Exception as e:
        logger.exception("Upload error")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/datasets")
async def list_datasets():
    """List available datasets from Supabase."""
    return supabase_helper.list_datasets()


@app.delete("/api/datasets/{filename}")
async def delete_dataset(filename: str):
    """Delete a dataset from Supabase."""
    dataset_name = os.path.splitext(filename)[0] if '.' in filename else filename
    result = supabase_helper.delete_dataset(dataset_name)
    if result["status"] == "success":
        return {"status": "success"}
    return JSONResponse(status_code=500, content={"error": result.get("error", "Delete failed")})




def _sanitize_generated_code(code: str) -> str:
    """Remove input() calls, fix imports, and clean up LLM-generated code."""
    # Remove input() calls
    code = re.sub(r'(\w+)\s*=\s*input\s*\([^)]*\)', r'\1 = ""  # input() auto-removed', code)
    code = re.sub(r'\binput\s*\([^)]*\)', '"" # input() auto-removed', code)
    # Remove 'from datasets import ...' lines
    code = re.sub(r'^from datasets import.*$', '# (removed: use pandas instead)', code, flags=re.MULTILINE)
    return code


def _postprocess_code(generated_code: str) -> str:
    """Post-process generated code: inject imports, clean up."""
    if not generated_code:
        return generated_code

    generated_code = _sanitize_generated_code(generated_code)

    # Always ensure pandas and matplotlib are imported
    auto_imports = "import pandas as pd\nimport matplotlib.pyplot as plt\n"
    # Remove duplicate imports the LLM may have added
    generated_code = re.sub(r'^import pandas as pd\s*$', '', generated_code, flags=re.MULTILINE)
    generated_code = re.sub(r'^import matplotlib\.pyplot as plt\s*$', '', generated_code, flags=re.MULTILINE)

    generated_code = auto_imports + generated_code

    return generated_code


def _extract_json_from_llm(text: str) -> Optional[dict]:
    """Robustly extract JSON from LLM output with multiple fallbacks."""
    # Extract JSON from possible markdown wrapping
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Try to find JSON object in the text
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1:
        text = text[start_idx:end_idx + 1]

    # Attempt 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Fix triple-quoted strings
    fixed = text.replace('"""', '"').replace("'''", "'")
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Attempt 3: Regex extract code and explanation
    code_match = re.search(r'"code"\s*:\s*(?:"""(.*?)"""|"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\')', text, re.DOTALL)
    explanation_match = re.search(r'"explanation"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    if code_match:
        extracted_code = code_match.group(1) or code_match.group(2) or code_match.group(3) or ""
        extracted_code = extracted_code.replace("\\n", "\n").replace('\\"', '"')
        if extracted_code:
            return {
                "code": extracted_code,
                "explanation": (explanation_match.group(1).replace("\\n", "\n") if explanation_match else "Code extracted from AI response."),
                "suggestions": "",
                "visualization": ""
            }

    # Attempt 4: Treat entire response as code if it looks like Python
    raw = text.strip()
    if any(kw in raw for kw in ["import ", "print(", "def ", "pd.", "plt.", "df ", "df.", "DATASET_PATH"]):
        return {"code": raw, "explanation": "Raw code extracted from AI response.", "suggestions": "", "visualization": ""}

    return None


# --- Feature 6: Multi-Step + Feature 7: Debug + Feature 11: Error Recovery in AI Query ---
@app.post("/api/query")
async def process_query(req: NaturalLanguageRequest):
    """Generate code and explanation based on a natural language prompt.
    Supports: multi-step decomposition, debug mode, session memory, error recovery.
    """
    if not hf_client:
        return JSONResponse(status_code=400, content={"error": "HF API Key not configured. Add HF_API_KEY to your .env file."})

    try:
        session_id = req.session_id or str(uuid.uuid4())
        if session_id not in session_store:
            session_store[session_id] = []

        # --- Explanation mode instructions ---
        explain_instruction = prompts.EXPLAIN_BEGINNER if req.explanation_mode == "beginner" else prompts.EXPLAIN_TECHNICAL

        system_msg = prompts.SYSTEM_PROMPT_QUERY.format(
            explain_instruction=explain_instruction,
            multistep_instruction=prompts.MULTISTEP_INSTRUCTION
        )

        user_msg = (
            f"User request: {req.prompt}\n"
            f"Do NOT use 'from datasets import load_dataset'. "
            f"Do NOT use input() or any interactive prompts. "
            f"Produce print output and/or matplotlib charts."
        )

        messages = [{"role": "system", "content": system_msg}]

        # Add session history for follow-up context
        for msg in session_store[session_id][-4:]:
            messages.append({"role": "user", "content": msg.get("prompt", "")})
            messages.append({"role": "assistant", "content": json.dumps({"code": msg.get("code", "")})})

        messages.append({"role": "user", "content": user_msg})

        response = hf_client.chat_completion(
            model=HF_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()

        # Robust JSON extraction
        data = _extract_json_from_llm(text)

        if data is None:
            return {
                "code": f"# AI returned non-JSON response. Raw output:\n# {text[:500]}",
                "explanation": "The model response could not be parsed. Try rephrasing your prompt.",
                "suggestions": "",
                "visualization": "",
                "session_id": session_id
            }

        # --- Post-process code ---
        data["code"] = _postprocess_code(data.get("code", ""))

        # Save to session
        session_store[session_id].append({
            "prompt": req.prompt,
            "code": data.get("code", "")
        })

        result = {
            "code": data.get("code", ""),
            "explanation": data.get("explanation", ""),
            "suggestions": data.get("suggestions", ""),
            "visualization": data.get("visualization", ""),
            "session_id": session_id
        }

        # --- Feature 7: Debug Mode ---
        if req.debug:
            result["debug_info"] = (
                f"[LLM Model] {HF_MODEL}\n"
                f"[Session] {session_id} ({len(session_store[session_id])} turns)\n"
                f"[Prompt Tokens] ~{len(user_msg.split())}\n"
                f"[Response Length] {len(text)} chars\n"
                f"[Explanation Mode] {req.explanation_mode}\n"
            )

        return result

    except json.JSONDecodeError:
        return {
            "code": f"# AI returned non-JSON response. Raw output:\n# {text[:500]}",
            "explanation": "The model response could not be parsed. Try rephrasing your prompt.",
            "suggestions": "",
            "visualization": "",
            "session_id": session_id if 'session_id' in dir() else None
        }
    except Exception as e:
        logger.exception("LLM Error in /api/query")
        return JSONResponse(status_code=500, content={"error": f"LLM Error: {str(e)}"})




# --- MCP SSE Transport ---
sse_transport = None

@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    global sse_transport
    sse_transport = SseServerTransport("/mcp/messages")

    async def run_mcp():
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server_instance.run(
                streams[0], streams[1],
                mcp_server_instance.create_initialization_options()
            )

    return await run_mcp()

@app.post("/mcp/messages")
async def mcp_messages_endpoint(request: Request):
    global sse_transport
    if sse_transport is None:
        return JSONResponse(status_code=400, content={"error": "SSE connection not established"})
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)
    return JSONResponse(status_code=202, content={"status": "accepted"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
