"""
Slack AI Assistant v2 - Main Entry Point

Startup order
-------------
1. Load configuration
2. Initialize database
3. Initialize RAG vector store
4. Initialize mem0 memory
5. Initialize MCP servers
6. Start background indexer
7. Start task scheduler
8. Start Slack bot
"""

import asyncio
import sys
import signal

from src.config.settings import config
from src.utils.logger import get_logger

from src.memory.database import initialize_database, close_database
from src.channels.slack import start_slack_app, stop_slack_app
from src.tools.scheduler import task_scheduler

# RAG
from src.rag import (
    initialize_vector_store,
    start_indexer,
    stop_indexer,
    get_document_count,
)

# Memory
from src.memory_ai import (
    initialize_memory,
    is_memory_enabled,
)

# MCP
from src.mcp import (
    initialize_mcp,
    shutdown_mcp,
    is_mcp_enabled,
    get_connected_servers,
)

logger = get_logger("main")

shutdown_event = asyncio.Event()


# =========================================================
# Main Startup
# =========================================================

async def main():

    logger.info("=" * 50)
    logger.info("Starting Slack AI Assistant v2")
    logger.info("=" * 50)

    try:

        # -------------------------------------------------
        # Database
        # -------------------------------------------------

        logger.info("Initializing database...")
        initialize_database()
        logger.info("Database initialized")

        # -------------------------------------------------
        # RAG
        # -------------------------------------------------

        if config.rag.enabled:

            logger.info("Initializing RAG system...")

            await initialize_vector_store()

            doc_count = await get_document_count()

            logger.info(f"Vector store initialized ({doc_count} documents)")

            await start_indexer()

            logger.info("Background indexer started")

        else:

            logger.info("RAG system disabled")

        # -------------------------------------------------
        # Memory
        # -------------------------------------------------

        if config.memory.enabled:

            logger.info("Initializing mem0 memory system...")

            await initialize_memory()

            if is_memory_enabled():
                logger.info("Memory initialized")
            else:
                logger.warning("Memory failed to initialize")

        else:

            logger.info("Memory disabled")

        # -------------------------------------------------
        # MCP
        # -------------------------------------------------

        logger.info("Initializing MCP servers...")

        await initialize_mcp()

        if is_mcp_enabled():

            servers = get_connected_servers()

            logger.info(f"MCP connected: {', '.join(servers)}")

        else:

            logger.info("No MCP servers connected")

        # -------------------------------------------------
        # Scheduler
        # -------------------------------------------------

        logger.info("Starting task scheduler...")

        task_scheduler.start()

        logger.info("Scheduler started")

        # -------------------------------------------------
        # Slack Bot
        # -------------------------------------------------

        logger.info("Starting Slack app...")

        # Run Slack bot as background task
        asyncio.create_task(start_slack_app())

        logger.info("Slack bot running")

        logger.info("=" * 50)
        logger.info("Slack AI Assistant v2 is ready")
        logger.info("=" * 50)

        # Wait until shutdown signal
        await shutdown_event.wait()

    except Exception as e:

        logger.error(f"Startup failed: {e}")

        await shutdown()

        sys.exit(1)


# =========================================================
# Graceful Shutdown
# =========================================================

async def shutdown():

    logger.info("Shutting down application...")

    try:

        logger.info("Stopping Slack bot...")
        await stop_slack_app()

        logger.info("Stopping MCP...")
        await shutdown_mcp()

        if config.rag.enabled:
            logger.info("Stopping indexer...")
            stop_indexer()

        logger.info("Stopping scheduler...")
        task_scheduler.stop()

        logger.info("Closing database...")
        close_database()

        logger.info("Shutdown complete")

    except Exception as e:

        logger.error(f"Shutdown error: {e}")


# =========================================================
# Signal Handlers
# =========================================================

def handle_shutdown_signal():

    logger.info("Shutdown signal received")

    shutdown_event.set()


# =========================================================
# Entrypoint
# =========================================================

if __name__ == "__main__":

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Register signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_shutdown_signal)
        except NotImplementedError:
            pass

    try:

        loop.run_until_complete(main())

    finally:

        loop.run_until_complete(shutdown())
        loop.close()

        sys.exit(0)