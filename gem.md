# 🚀 CodeExec AI — Enterprise Code Execution & Analysis Engine

> **A secure, context-aware AI coding assistant + data analyst + execution engine**

CodeExec AI is an advanced, enterprise-grade intelligent coding assistant that leverages the **Model Context Protocol (MCP)** and **Mistral LLM via Hugging Face Inference API** to dynamically generate, execute, and analyze Python code in a secure, sandboxed environment.

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Mistral (`mistralai/Mistral-Small-24B-Instruct-2501`) via Hugging Face API |
| **Backend** | FastAPI (Python) |
| **Execution** | Python `subprocess` with Tempfile Sandboxing |
| **Protocol** | Model Context Protocol (MCP) via SSE Transport |
| **Frontend** | Vanilla HTML/CSS/JS with Glassmorphism UI |
| **Auth** | Environment variable (`HF_API_KEY`) — no hardcoded keys |

---

## 🌟 All 11 Features — Fully Implemented

### 1. 🔐 Secure Sandboxed Execution
- **AST Validation**: Every code string is parsed through Python's `ast` module via `SecurityScanner` before execution.
- **Blocked Modules**: `os`, `sys`, `subprocess`, `shutil`, `socket`, `urllib`, `requests`, `pty`
- **Blocked Built-ins**: `eval()`, `exec()`, `open()`, `__import__()`, `compile()`
- **Timeout**: Hard 5-second execution limit enforced via `subprocess.run(timeout=...)`.
- **Isolation**: Code runs in a temporary directory that is cleaned up immediately after execution.
- **Files**: `executor.py` → `SecurityScanner`, `validate_python_code()`, `execute_python_code()`

### 2. 📊 Smart Data Analysis Mode
- **Auto-Detection**: When a `.csv` or `.json` dataset is selected, the backend reads headers and sample rows.
- **Context Injection**: Dataset schema is passed directly to the LLM for accurate code generation.
- **Auto-Prompting**: If the prompt contains "analyze" or "summary" (or is very short), the system auto-instructs the LLM to generate summary statistics, missing value analysis, and column insights.
- **Files**: `main.py` → `process_query()` context assembly block

### 3. 🧠 Code Explanation Engine
- **Two Modes**:
  - **Technical**: Precise, covers performance, reasoning, and edge cases.
  - **Beginner-Friendly**: Simple, everyday language — no jargon.
- **UI**: Dropdown selector in the AI Prompt panel (`#explanationMode`).
- **Backend**: Mode string injected into LLM system prompt.
- **Files**: `main.py` → `explain_instruction`, `index.html` → `<select id="explanationMode">`

### 4. 🔁 Session Memory (In-Memory, No External DB)
- **UUID Sessions**: Every AI prompt session gets a UUID. Stored in `session_store: Dict[str, List[dict]]`.
- **Context Replay**: Last 4 prompt/code pairs are injected into the LLM message history for follow-up awareness.
- **Follow-up Support**: e.g. "Now plot that data" works because the LLM sees previous context.
- **Files**: `main.py` → `session_store`, `app.js` → `currentSessionId`

### 5. 📈 Visualization Engine
- **Matplotlib Interception**: A Python preamble is injected before every script that overrides matplotlib to `Agg` backend.
- **Base64 Capture**: All figures are captured at exit via `atexit`, saved as Base64 PNG.
- **Inline Rendering**: Plots are rendered directly in the output panel as `<img>` elements.
- **Auto-generation**: LLM is instructed to generate charts when data is present (line, bar, scatter, heatmap).
- **Files**: `executor.py` → `PLOT_CAPTURE_PREAMBLE`

### 6. 🧪 Multi-Step Execution
- **Decomposition**: The LLM system prompt instructs it to break complex requests into labeled steps (`# Step 1`, `# Step 2`, etc.) within a single script.
- **Sequential Execution**: All steps run in one subprocess call — no fragmented execution.
- **Example**: "Clean data, compute averages, and plot results" → 3 labeled steps in one script.
- **Files**: `main.py` → `multistep_instruction` in system prompt

### 7. 🛠️ Debug Mode
- **Toggle**: Checkbox in the AI Prompt panel (`#debugToggle`).
- **Execution Debug**: When enabled, the `/api/execute` endpoint returns:
  - AST validation result
  - Code length & line count
  - Exit status & execution time
  - Stderr preview
- **Query Debug**: When enabled, the `/api/query` endpoint returns:
  - LLM model name
  - Session ID & turn count
  - Prompt token estimate
  - Response length
  - Dataset & explanation mode used
- **UI**: Debug info rendered in a styled block below the output.
- **Files**: `main.py` → `debug_info`, `app.js` → `result.debug_info` rendering

### 8. ⚡ Code Optimization Suggestions
- **LLM-Driven**: The system prompt mandates a `suggestions` key in every response.
- **Content**: Loop → vectorization, memory improvements, time complexity reduction, library alternatives.
- **UI**: Rendered in a dedicated `#generatedSuggestions` panel with a 💡 icon.
- **Files**: `main.py` → system prompt `suggestions` key, `app.js` → suggestions rendering

### 9. 📦 Export Feature
- **Three Formats**:
  - **TXT**: Plain text report (code, output, error, timing).
  - **CSV**: Structured field/value pairs.
  - **JSON**: Full structured object with timestamp.
- **Client-Side**: Downloads generated entirely in the browser via `Blob` + `URL.createObjectURL`.
- **UI**: Three export buttons (`Export TXT`, `Export CSV`, `Export JSON`) on every result block.
- **Files**: `app.js` → `downloadFile()`, `csvEscape()`, export button event listeners

### 10. 🧩 Plugin Architecture
- **Injected Tools**: Three stub functions are available inside every execution context:
  - `run_sql_query(query: str)` → returns mock SQL results
  - `call_api(endpoint: str, payload: dict)` → returns mock API response
  - `analyze_text(text: str)` → returns mock sentiment analysis
- **LLM Awareness**: System prompt lists these functions so the LLM can generate code that calls them.
- **Extensible**: Add real implementations by replacing the stubs in `PLOT_CAPTURE_PREAMBLE`.
- **Files**: `executor.py` → plugin stubs in preamble, `main.py` → plugin list in system prompt

### 11. 🔁 Error Handling & Auto-Recovery
- **Detection**: If code execution fails (non-zero exit), the backend checks if it's a runtime error (not a security block).
- **LLM Fix**: The error + original code are sent to the LLM with a "fix this code" prompt.
- **Retry**: The fixed code is executed. If successful, the result is returned with `retried: true`.
- **UI Indicator**: A "🔁 Auto-Recovery" banner is shown when code was auto-corrected.
- **Safety**: Security-blocked code is never retried. Only runtime errors trigger recovery.
- **Files**: `main.py` → auto-recovery block in `api_execute_code()`, `app.js` → `result.retried` rendering

---

## 📤 Output Format (Strict JSON from LLM)

```json
{
  "code": "generated python code",
  "explanation": "step-by-step explanation",
  "suggestions": "optimization tips",
  "visualization": "chart description or null"
}
```

## 🏗️ Project Structure

```
CodeExecAI/
├── main.py              # FastAPI app, all 11 features, MCP transport
├── executor.py          # Sandbox engine, AST scanner, plugin stubs
├── mcp_server.py        # MCP tool registration (run_python_code)
├── requirements.txt     # Python dependencies
├── .env                 # HF_API_KEY (gitignored)
├── .env.example         # Template for API key
├── vercel.json          # Vercel deployment config
├── datasets/            # Uploaded user datasets
├── static/
│   ├── index.html       # UI shell with all controls
│   ├── style.css        # Warm premium dark theme
│   └── app.js           # Frontend logic, export, debug, sessions
└── gem.md               # This file
```

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Hugging Face API key
echo HF_API_KEY=hf_your_key_here > .env

# 3. Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. Open http://localhost:8000
```

---

*Built with a focus on **Security**, **Intelligence**, and **Developer Experience**.*
