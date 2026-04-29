"""
CodeExec AI - Enhanced Python Code Execution Engine
Supports stdout capture, matplotlib chart rendering (as base64),
execution timing, safe sandboxing, and output file capture.
"""

import subprocess
import tempfile
import os
import sys
import time
import base64
import json
import glob
import ast
import re


import prompts

# Preamble injected before every script to capture matplotlib plots
PLOT_CAPTURE_PREAMBLE = prompts.PLOT_CAPTURE_PREAMBLE

# Preamble to neutralize input() calls so scripts never hang
INPUT_SANITIZER_PREAMBLE = """
# --- Auto-neutralize input() to prevent hangs ---
import builtins as _builtins
_original_input = _builtins.input
def _safe_input(prompt=''):
    print(f"[Auto-skipped input prompt: {prompt}]")
    return ''
_builtins.input = _safe_input
"""


class SecurityScanner(ast.NodeVisitor):
    """AST-based security scanner that blocks dangerous operations
    while allowing safe file I/O for data analysis."""
    def __init__(self):
        # Only block truly dangerous modules — allow os.path for file operations
        self.blocked_modules = {'subprocess', 'shutil', 'socket', 'urllib', 'urllib3', 'requests', 'pty', 'ctypes'}
        self.blocked_functions = {'eval', 'exec', '__import__', 'compile'}
        # Specific os functions that are dangerous
        self.blocked_os_attrs = {'system', 'popen', 'execv', 'execve', 'spawn', 'spawnl',
                                  'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve',
                                  'spawnvp', 'spawnvpe', 'kill', 'killpg', 'remove', 'unlink',
                                  'rmdir', 'removedirs'}
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            mod = alias.name.split('.')[0]
            if mod in self.blocked_modules:
                self.errors.append(f"Import of '{alias.name}' is blocked for security reasons.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            mod = node.module.split('.')[0]
            if mod in self.blocked_modules:
                self.errors.append(f"Import from '{node.module}' is blocked for security reasons.")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.blocked_functions:
                self.errors.append(f"Call to '{node.func.id}()' is blocked for security reasons.")
        # Block dangerous os.system(), os.popen(), etc. but allow os.path.*
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                if node.func.attr in self.blocked_os_attrs:
                    self.errors.append(f"Call to 'os.{node.func.attr}()' is blocked for security reasons.")
        self.generic_visit(node)

def validate_python_code(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    
    scanner = SecurityScanner()
    scanner.visit(tree)
    if scanner.errors:
        return False, "Security Error: " + " | ".join(scanner.errors)
    
    return True, "Code is safe."


def _strip_input_calls(code: str) -> str:
    """Remove or neutralize input() calls from generated code to prevent hangs."""
    # Replace standalone input() assignments with empty string
    code = re.sub(r'(\w+)\s*=\s*input\s*\([^)]*\)', r'\1 = ""  # input() auto-removed', code)
    # Replace bare input() calls
    code = re.sub(r'\binput\s*\([^)]*\)', '"" # input() auto-removed', code)
    return code


# Output file extensions we'll capture
OUTPUT_FILE_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json', '.txt', '.html', '.md',
                          '.png', '.jpg', '.jpeg', '.svg', '.pdf'}


def execute_python_code(code: str, timeout: int = 30) -> dict:
    """
    Executes a string of Python code in a separate process.

    Features:
        - Captures stdout and stderr
        - Captures matplotlib plots as base64-encoded PNGs
        - Captures any output files (csv, xlsx, json, etc.) as downloadable blobs
        - Measures execution wall-clock time
        - Enforces a timeout
        - Strips input() calls to prevent hangs

    Args:
        code: The Python code to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        dict with keys: success, output, error, plots (list of base64 PNGs),
                        output_files (list of {name, data_b64, mime}),
                        execution_time_ms
    """
    tmpdir = tempfile.mkdtemp(prefix="codeexec_")
    script_path = os.path.join(tmpdir, "script.py")

    # Strip input() calls before validation
    code = _strip_input_calls(code)

    # Security Validation
    is_safe, validation_msg = validate_python_code(code)
    if not is_safe:
        return {
            "success": False,
            "output": "",
            "error": validation_msg,
            "plots": [],
            "output_files": [],
            "execution_time_ms": 0
        }

    try:
        # Build the full script with preambles
        full_code = INPUT_SANITIZER_PREAMBLE + "\n" + PLOT_CAPTURE_PREAMBLE + "\n" + code

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(full_code)

        env = os.environ.copy()
        env["CODEEXEC_PLOT_DIR"] = tmpdir
        # Ensure the virtual-env's python is used
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        start = time.perf_counter()

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            env=env
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Check for captured plots
        plots = []
        plots_manifest = os.path.join(tmpdir, "_plots.json")
        if os.path.exists(plots_manifest):
            with open(plots_manifest, 'r') as f:
                plots = json.load(f)

        # --- Capture output files ---
        output_files = []
        for fpath in glob.glob(os.path.join(tmpdir, "*")):
            fname = os.path.basename(fpath)
            # Skip internal files
            if fname in ("script.py", "_plots.json") or fname.startswith("_codeexec"):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in OUTPUT_FILE_EXTENSIONS:
                try:
                    with open(fpath, 'rb') as bf:
                        file_data = bf.read()
                    # Determine MIME type
                    mime_map = {
                        '.csv': 'text/csv',
                        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        '.xls': 'application/vnd.ms-excel',
                        '.json': 'application/json',
                        '.txt': 'text/plain',
                        '.html': 'text/html',
                        '.md': 'text/markdown',
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.svg': 'image/svg+xml',
                        '.pdf': 'application/pdf',
                    }
                    mime = mime_map.get(ext, 'application/octet-stream')
                    output_files.append({
                        "name": fname,
                        "data_b64": base64.b64encode(file_data).decode('utf-8'),
                        "mime": mime,
                        "size": len(file_data)
                    })
                except Exception:
                    pass

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "plots": plots,
            "output_files": output_files,
            "execution_time_ms": elapsed_ms
        }

    except subprocess.TimeoutExpired:
        elapsed_ms = timeout * 1000
        return {
            "success": False,
            "output": "",
            "error": f"⏱️ Execution timed out after {timeout} seconds.",
            "plots": [],
            "output_files": [],
            "execution_time_ms": elapsed_ms
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": f"Internal execution error: {str(e)}",
            "plots": [],
            "output_files": [],
            "execution_time_ms": 0
        }
    finally:
        # Cleanup temp directory
        try:
            for f in glob.glob(os.path.join(tmpdir, "*")):
                os.remove(f)
            os.rmdir(tmpdir)
        except OSError:
            pass
