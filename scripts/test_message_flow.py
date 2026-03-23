#!/usr/bin/env python3
"""
Test script to verify the message flow works end-to-end without Slack.

This simulates what happens when a Slack message arrives.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.agents.agent import Agent, AgentContext
from src.memory.database import initialize_database, get_or_create_session
from src.utils.logger import get_logger

logger = get_logger("test-flow")


async def test_message_flow():
    """Test complete message flow."""
    
    logger.info("=" * 60)
    logger.info("Testing Message Flow (No Slack)")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Step 1: Initializing database...")
        initialize_database()
        logger.info("[OK] Database initialized")
        
        # Initialize agent
        logger.info("Step 2: Initializing agent...")
        agent = Agent()
        logger.info("[OK] Agent initialized")
        
        # Create session
        user_id = "U_TEST_USER"
        channel_id = "C_TEST_CHANNEL"
        thread_ts = None
        
        logger.info("Step 3: Creating session...")
        session = get_or_create_session(user_id, channel_id, thread_ts)
        logger.info(f"[OK] Session created: {session['id']}")
        
        # Create context
        logger.info("Step 4: Creating agent context...")
        context = AgentContext(
            session_id=session["id"],
            user_id=user_id,
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_name="Test User",
            channel_name="test-channel",
        )
        logger.info(f"[OK] Context created: {context.session_id}")
        
        # Test message
        test_message = "hello, what can you do?"
        logger.info(f"Step 5: Processing message: '{test_message}'")
        
        response = await agent.process_message(test_message, context)
        
        logger.info("=" * 60)
        logger.info("[SUCCESS] Message processed!")
        logger.info("=" * 60)
        logger.info(f"Response: {response.content[:200]}")
        logger.info(f"RAG used: {response.rag_used}")
        logger.info(f"Memory used: {response.memory_used}")
        logger.info(f"Should thread: {response.should_thread}")
        
        return True
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"[FAILED] {type(e).__name__}: {e}")
        logger.error("=" * 60, exc_info=True)
        return False


if __name__ == "__main__":
    result = asyncio.run(test_message_flow())
    sys.exit(0 if result else 1)
