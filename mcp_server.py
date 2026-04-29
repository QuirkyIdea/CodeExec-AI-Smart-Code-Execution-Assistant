"""
CodeExec AI - MCP Server Definition
Registers the run_python_code tool for LLM clients.
"""

import mcp.types as types
from mcp.server import Server
from executor import execute_python_code

# Initialize the MCP server
server = Server("codeexec-ai")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for the LLM Client."""
    return [
        types.Tool(
            name="run_python_code",
            description=(
                "Executes a given string of Python 3 code and returns its "
                "standard output, errors, and any matplotlib charts as base64 PNGs. "
                "Libraries available: numpy, pandas, matplotlib, math, json, "
                "collections, itertools, datetime, statistics, csv, re. "
                "Use print() to return results. "
                "Use matplotlib to generate charts — they will be captured automatically."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The raw Python 3 code string to execute."
                    }
                },
                "required": ["code"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls initiated by the LLM Client."""

    if name != "run_python_code":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments or "code" not in arguments:
        raise ValueError("Missing required 'code' argument.")

    result = execute_python_code(arguments["code"])

    # Build the response content list
    content: list[types.TextContent | types.ImageContent] = []

    if result["success"]:
        text = f"✅ Execution successful ({result['execution_time_ms']}ms)\n\n"
        if result["output"]:
            text += f"Output:\n{result['output']}"
        else:
            text += "Output: (no output)"
    else:
        text = f"❌ Execution failed ({result['execution_time_ms']}ms)\n\n"
        if result["error"]:
            text += f"Error:\n{result['error']}\n"
        if result["output"]:
            text += f"\nPartial Output:\n{result['output']}"

    content.append(types.TextContent(type="text", text=text))

    # Attach any captured plots as image content
    for i, plot_b64 in enumerate(result.get("plots", [])):
        content.append(
            types.ImageContent(
                type="image",
                data=plot_b64,
                mimeType="image/png"
            )
        )

    return content
