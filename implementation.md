# CodeExec AI: Smart Code Execution Assistant - Implementation Plan & Step-by-Step Process

## 1. Project Overview
CodeExec AI is a system that enables Large Language Models (LLMs) to dynamically generate and execute Python code for rapid computations, transformations, and data processing. It exposes these capabilities via the Model Context Protocol (MCP) using a FastAPI framework, allowing any MCP-compatible LLM client to call the `run_python_code` tool seamlessly.

## 2. Architecture & Tech Stack
*   **Language:** Python 3.11+
*   **API Framework:** FastAPI (for handling SSE MCP transport and providing standard REST endpoints)
*   **Protocol:** Model Context Protocol (MCP) - via the `mcp` Python SDK
*   **Execution Engine:** Python's `subprocess` for executing scripts in a controlled environment.
*   **Security:** Timeout enforcement, standard library restriction considerations, environment sandboxing via temporary directories.

---

## 3. Step-by-Step Implementation Process

We will build out the project sequentially. Below is the step-by-step process required to implement the full system.

### Step 1: Environment & Project Setup
**Goal:** Initialize the project directory, virtual environment, and install required libraries.
1. Create project directories: `CodeExecAI`
2. Create `requirements.txt` with the following contents:
   ```text
   fastapi>=0.109.0
   uvicorn>=0.27.0
   mcp>=1.0.0
   ```
3. Open a terminal in `CodeExecAI` and run:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Step 2: Implement the Code Execution Engine (`executor.py`)
**Goal:** Create a robust and safe way to execute LLM-provided Python code using temporary files.
1. Create `executor.py`.
2. Implement an `execute_python_code(code: str, timeout: int = 15) -> dict` function.
3. **Logic:**
   * Use Python's `tempfile` module to safely write the `code` string into a `.py` file.
   * Use `subprocess.run(["python", temp_file_path], capture_output=True, text=True, timeout=timeout)`.
   * Capture `stdout`, `stderr`, and `returncode`.
   * Ensure the temporary file is deleted in a `finally` block.
   * Return a structured dict containing `output`, `error`, and `success` status to feed back to the LLM.

### Step 3: Define the MCP Tools (`mcp_server.py`)
**Goal:** Setup the Model Context Protocol logic so the LLM understands it has a tool available to run Python code.
1. Create `mcp_server.py`.
2. Import `mcp.server.Server`.
3. Instantiate the server: `server = Server("codeexec-ai")`.
4. Register the tool:
   ```python
   @server.list_tools()
   async def handle_list_tools() -> list[mcp.types.Tool]:
       return [
           mcp.types.Tool(
               name="run_python_code",
               description="Executes a given string of Python code and returns its standard output and errors.",
               inputSchema={
                   "type": "object",
                   "properties": {
                       "code": {
                           "type": "string",
                           "description": "The raw Python code string to execute. Example: 'print(5+5)'"
                       }
                   },
                   "required": ["code"]
               }
           )
       ]
   ```
5. Register the tool call handler (`@server.call_tool()`) that routes the `run_python_code` request directly to the `execute_python_code` function built in Step 2.

### Step 4: Add FastAPI Transport Layer (`main.py`)
**Goal:** Run the MCP server over SSE (Server-Sent Events) so standard LLM interfaces can connect to it easily.
1. Create `main.py`.
2. Initialize the FastAPI app: `app = FastAPI()`.
3. Configure the SSE Transport endpoints:
   * Setup a global `SSETransport`.
   * `GET /mcp/sse`: The endpoint LLMs hit to establish the SSE connection.
   * `POST /mcp/messages`: The endpoint for fielding ongoing requests and tool calls.
4. Mount the MCP server to the SSE transport using `app.add_route` and `app.add_api_route`.

### Step 5: Testing the Integration
**Goal:** Verify everything runs end-to-end.
1. Start the server using Uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. Once running, you can connect to it securely using the standard `npx @modelcontextprotocol/inspector` test harness:
   ```bash
   npx @modelcontextprotocol/inspector --transport sse --url http://127.0.0.0:8000/mcp/sse
   ```
3. Test a tool call with the payload `{"code": "print('Hello from the LLM Executor!')"}` and verify that the output securely returns back through the MCP layer.

### Step 6: Security Hardening (Production Only)
1. Add custom exception handling for syntax errors vs timeouts.
2. Consider swapping `subprocess.run("python")` with an execution inside of a sandboxed execution layer (like firejail or a secure Docker container `docker run --rm python:3.11-alpine python -c "..."`) if public-facing.

## 4. Let's Begin
Now that the plan is set:
If the user approves, we can automatically implement Step 1 and Step 2 directly.

---

## 5. Advanced Enhancements (Implemented)
*   **Secure Sandboxing**: Added `ast`-based code validation to block dangerous imports (`os`, `sys`, `subprocess`) and built-ins (`eval`, `exec`). Enforced a 5-second execution timeout.
*   **Smart Data Analysis**: Automatically detects dataset headers and instructs the LLM to generate summary statistics, missing value analyses, and column insights.
*   **Code Explanation Engine**: Added selectable modes (Technical vs. Beginner-Friendly) via the UI that alter the generated explanation.
*   **Session Memory**: Uses in-memory uuid-based session storage to pass conversation history for follow-up questions and multi-step execution.
*   **Code Optimization Suggestions**: Prompts the LLM to provide optimization suggestions that are dynamically rendered in the UI.
*   **Export Feature**: Added client-side export functionality to download execution reports (code, output, errors) as text files.
*   **Plugin Stub Architecture**: Simulated extensibility with `run_sql_query`, `call_api`, and `analyze_text` injected directly into the Python execution namespace and LLM context.
