"""
mem0 Memory Client

Integrates mem0.ai for long-term memory extraction.

Workflow:

Conversation
     ↓
mem0 LLM extracts facts
     ↓
Facts stored in vector memory
     ↓
Semantic retrieval
     ↓
Personalized responses
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("mem0-client")

# -------------------------------------------------------
# Data Models
# -------------------------------------------------------

@dataclass
class MemoryItem:
    id: str
    memory: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    score: Optional[float] = None


# -------------------------------------------------------
# Client State
# -------------------------------------------------------

memory_client = None
is_initialized = False


# -------------------------------------------------------
# Initialize Memory
# -------------------------------------------------------

async def initialize_memory():
    """
    Initialize mem0 Cloud client.
    """

    global memory_client, is_initialized

    if is_initialized:
        logger.debug("Memory already initialized")
        return

    try:

        logger.info("Initializing mem0 client")

        api_key = os.getenv("MEM0_API_KEY")

        if not api_key:
            raise RuntimeError("MEM0_API_KEY not configured")

        from mem0 import MemoryClient

        memory_client = MemoryClient(api_key=api_key)

        is_initialized = True

        logger.info(" mem0 memory initialized")

    except Exception as e:

        logger.error(f"Failed to initialize mem0: {e}")

        memory_client = None
        is_initialized = False


# -------------------------------------------------------
# Add Memory
# -------------------------------------------------------

async def add_memory(
    messages: List[Dict[str, str]],
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[MemoryItem]:
    """
    Add conversation messages to memory.

    mem0 automatically extracts facts.
    """

    if not is_initialized or not memory_client:
        logger.warning("Memory not initialized")
        return []

    try:

        result = await memory_client.add(
            messages,
            user_id=user_id,
            metadata={
                "source": "slack",
                **(metadata or {}),
            },
        )

        memories = result.get("results", [])

        parsed = [
            MemoryItem(
                id=m.get("id"),
                memory=m.get("memory"),
                user_id=m.get("user_id"),
                metadata=m.get("metadata"),
                created_at=m.get("created_at"),
                updated_at=m.get("updated_at"),
            )
            for m in memories
        ]

        logger.info(f"Stored {len(parsed)} memories")

        return parsed

    except Exception as e:

        logger.error(f"Failed to add memory: {e}")

        return []


# -------------------------------------------------------
# Search Memory
# -------------------------------------------------------

async def search_memory(
    query: str,
    user_id: str,
    limit: int = 5,
) -> List[MemoryItem]:
    """
    Semantic search of memories.
    """

    if not is_initialized or not memory_client:
        logger.warning("Memory not initialized")
        return []

    try:

        result = await memory_client.search(
            query,
            user_id=user_id,
            limit=limit,
        )

        memories = result.get("results", [])

        parsed = [
            MemoryItem(
                id=m.get("id"),
                memory=m.get("memory"),
                user_id=m.get("user_id"),
                metadata=m.get("metadata"),
                score=m.get("score"),
            )
            for m in memories
        ]

        return parsed

    except Exception as e:

        logger.error(f"Memory search failed: {e}")

        return []


# -------------------------------------------------------
# Get All Memories
# -------------------------------------------------------

async def get_all_memories(user_id: str) -> List[MemoryItem]:
    """
    Retrieve all stored memories.
    """

    if not is_initialized or not memory_client:
        return []

    try:

        result = await memory_client.get_all(user_id=user_id)

        memories = result.get("results", [])

        return [
            MemoryItem(
                id=m.get("id"),
                memory=m.get("memory"),
                user_id=m.get("user_id"),
                metadata=m.get("metadata"),
            )
            for m in memories
        ]

    except Exception as e:

        logger.error(f"Failed to retrieve memories: {e}")

        return []


# -------------------------------------------------------
# Delete Memory
# -------------------------------------------------------

async def delete_memory(memory_id: str) -> bool:

    if not is_initialized or not memory_client:
        return False

    try:

        await memory_client.delete(memory_id)

        logger.info(f"Deleted memory {memory_id}")

        return True

    except Exception as e:

        logger.error(f"Failed to delete memory: {e}")

        return False


# -------------------------------------------------------
# Delete All Memories
# -------------------------------------------------------

async def delete_all_memories(user_id: str) -> bool:

    if not is_initialized or not memory_client:
        return False

    try:

        await memory_client.delete_all(user_id=user_id)

        logger.info(f"Deleted all memories for {user_id}")

        return True

    except Exception as e:

        logger.error(f"Failed to delete all memories: {e}")

        return False


# -------------------------------------------------------
# Build Context For LLM
# -------------------------------------------------------

def build_memory_context(memories: List[MemoryItem]) -> str:

    if not memories:
        return ""

    header = "## What I Remember About You\n\n"

    items = "\n".join(
        f"{i+1}. {m.memory}" for i, m in enumerate(memories)
    )

    footer = "\n\nUse this information to personalize responses."

    return header + items + footer


# -------------------------------------------------------
# Status
# -------------------------------------------------------

def is_memory_enabled() -> bool:

    return settings.memory.enabled and is_initialized


def get_memory_status():

    return {
        "enabled": settings.memory.enabled,
        "initialized": is_initialized,
    }