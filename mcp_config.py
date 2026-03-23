import os
import sys
from src.utils.logger import get_logger

logger = get_logger("mcp-config")


def build_mcp_config():

    logger.info("Building MCP config from environment variables")

    python_exec = sys.executable

    servers = []

    # GitHub MCP
    if os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        servers.append({
            "name": "github",
            "type": "stdio",
            "command": python_exec,
            "args": ["-m", "src.mcp.servers.github_server"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
            }
        })
        logger.info("GitHub MCP server configured")

    # Notion MCP
    if os.getenv("NOTION_API_TOKEN"):
        servers.append({
            "name": "notion",
            "type": "stdio",
            "command": python_exec,
            "args": ["-m", "src.mcp.servers.notion_server"],
            "env": {
                "NOTION_API_TOKEN": os.getenv("NOTION_API_TOKEN"),
                "NOTION_VERSION": "2022-06-28"
            }
        })
        logger.info("Notion MCP server configured")

    return {"servers": servers}