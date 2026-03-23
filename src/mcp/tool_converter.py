"""
MCP Tool Converter

Converts MCP tool definitions to OpenAI-style tool format
so LLM providers can call them.

Example MCP Tool:

{
  "name": "create_issue",
  "description": "Create a GitHub issue",
  "inputSchema": {
      "type": "object",
      "properties": {...},
      "required": [...]
  }
}

Converted Tool:

{
  "type": "function",
  "function": {
      "name": "github_create_issue",
      "description": "[Github] Create a GitHub issue",
      "parameters": {...}
  }
}
"""

from typing import Dict, List, Any


# ---------------------------------------------------------
# Convert Single MCP Tool
# ---------------------------------------------------------

def mcp_tool_to_openai(tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single MCP tool into OpenAI tool schema.
    """

    return {
        "type": "function",
        "function": {
            "name": tool["name"],  # already prefixed server_tool
            "description": format_description(
                tool.get("description"),
                tool.get("serverName", ""),
            ),
            "parameters": tool.get(
                "inputSchema",
                {
                    "type": "object",
                    "properties": {},
                },
            ),
        },
    }


# ---------------------------------------------------------
# Convert Multiple Tools
# ---------------------------------------------------------

def mcp_tools_to_openai(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert multiple MCP tools into LLM tool schema.
    """

    return [mcp_tool_to_openai(tool) for tool in tools]


# ---------------------------------------------------------
# Description Formatter
# ---------------------------------------------------------

def format_description(description: str | None, server_name: str) -> str:
    """
    Add server context to tool description.
    """

    if not server_name:
        return description or "No description available"

    server_label = server_name.capitalize()

    base_desc = description or "No description available"

    return f"[{server_label}] {base_desc}"


# ---------------------------------------------------------
# Format MCP Tool Result
# ---------------------------------------------------------

def format_mcp_result(result: Any) -> str:
    """
    Convert MCP tool results into readable text.
    """

    if result is None:
        return "Operation completed successfully."

    # MCP structured content format
    if isinstance(result, dict) and "content" in result:

        content = result["content"]

        if isinstance(content, list):

            texts = []

            for item in content:

                if (
                    isinstance(item, dict)
                    and item.get("type") == "text"
                    and item.get("text")
                ):
                    texts.append(item["text"])

            if texts:
                return "\n\n".join(texts)

    # plain object
    if isinstance(result, dict):

        import json

        return json.dumps(result, indent=2)

    # string
    if isinstance(result, str):
        return result

    # fallback
    return str(result)