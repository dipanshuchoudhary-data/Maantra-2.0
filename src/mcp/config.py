"""
MCP Configuration Loader

Loads MCP server configuration from:

1. mcp-config.json file
2. Environment variables fallback
"""

import os
import json
import shutil
import sys
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger("mcp-config")


def _resolve_npx_command() -> str | None:
    """Resolve a runnable npx executable path for the current OS."""

    candidates = ["npx"]

    if sys.platform.startswith("win"):
        candidates = ["npx.cmd", "npx.exe", "npx"]

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    return None


# ---------------------------------------------------------
# Data Models
# ---------------------------------------------------------


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None


@dataclass
class MCPConfig:
    servers: List[MCPServerConfig]


# ---------------------------------------------------------
# Load Configuration
# ---------------------------------------------------------


def load_mcp_config() -> MCPConfig:
    """
    Load MCP configuration from file or environment variables.
    """

    config_path = Path.cwd() / "mcp-config.json"

    # -----------------------------------------------------
    # 1️⃣ Load from file
    # -----------------------------------------------------

    if config_path.exists():

        try:

            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logger.info(f"Loaded MCP config from {config_path}")

            servers = []

            for server in data.get("servers", []):

                env = server.get("env", {})

                # Replace env references
                for key, value in env.items():

                    if isinstance(value, str) and value.startswith("$"):

                        env_var = value[1:]

                        env[key] = os.getenv(env_var, "")

                servers.append(
                    MCPServerConfig(
                        name=server["name"],
                        command=server["command"],
                        args=server.get("args"),
                        env=env,
                    )
                )

            return MCPConfig(servers=servers)

        except Exception as e:

            logger.error(f"Failed loading MCP config file: {e}")

    # -----------------------------------------------------
    # 2️⃣ Environment variable fallback
    # -----------------------------------------------------

    logger.info("Building MCP config from environment variables")

    servers: List[MCPServerConfig] = []
    npx_command = _resolve_npx_command()

    if not npx_command:
        logger.warning(
            "npx not found in PATH; skipping npm-based MCP servers "
            "(install Node.js to enable GitHub/Notion MCP)"
        )
        return MCPConfig(servers=servers)

    # -----------------------------------------------------
    # GitHub MCP
    # -----------------------------------------------------

    github_token = (
        os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )

    if github_token:

        servers.append(
            MCPServerConfig(
                name="github",
                command=npx_command,
                args=["-y", "@modelcontextprotocol/server-github"],
                env={
                    "GITHUB_PERSONAL_ACCESS_TOKEN": github_token,
                },
            )
        )

        logger.info("GitHub MCP server configured")

    else:

        logger.warning(
            "GitHub MCP server not configured "
            "(missing GITHUB_PERSONAL_ACCESS_TOKEN)"
        )

    # -----------------------------------------------------
    # Notion MCP
    # -----------------------------------------------------

    notion_token = (
        os.getenv("NOTION_API_TOKEN")
        or os.getenv("NOTION_TOKEN")
    )

    if notion_token:

        servers.append(
            MCPServerConfig(
                name="notion",
                command=npx_command,
                args=["-y", "@notionhq/notion-mcp-server"],
                env={
                    "OPENAPI_MCP_HEADERS": json.dumps(
                        {
                            "Authorization": f"Bearer {notion_token}",
                            "Notion-Version": "2022-06-28",
                        }
                    )
                },
            )
        )

        logger.info("Notion MCP server configured")

    else:

        logger.warning(
            "Notion MCP server not configured "
            "(missing NOTION_API_TOKEN)"
        )

    return MCPConfig(servers=servers)


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------


def validate_mcp_config(config: MCPConfig) -> List[str]:

    errors = []

    for server in config.servers:

        if not server.name:
            errors.append("Server missing name")

        if not server.command:
            errors.append(f"Server {server.name}: missing command")

    return errors