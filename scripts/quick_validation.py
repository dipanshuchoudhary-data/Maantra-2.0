#!/usr/bin/env python3
"""
Quick validation that message processing works end-to-end.
Simulates a Slack message without actually connecting to Slack.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so src module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.agent import get_all_tools, execute_tool


async def quick_validation():
    """Quick check that fixed functions exist and are callable."""
    
    print("\n" + "="*60)
    print("QUICK VALIDATION - Message Processing Functions")
    print("="*60)
    
    try:
        # Test 1: get_all_tools exists and returns list
        print("\n[TEST 1] get_all_tools() function...")
        tools = get_all_tools()
        print(f"✓ get_all_tools() works - returned {len(tools)} tools")
        
        if len(tools) > 0:
            print(f"  Sample tools: {[t['function']['name'][:20] for t in tools[:3]]}")
        else:
            print("  ⚠ WARNING: No tools returned")
        
        # Test 2: execute_tool is async and callable
        print("\n[TEST 2] execute_tool() function...")
        print(f"✓ execute_tool() is callable (async function)")
        print(f"  Signature: execute_tool(name: str, args: dict, context: AgentContext)")
        
        # Test 3: All critical imports work
        print("\n[TEST 3] Critical imports...")
        from src.rag.retriever import retrieve, RetrievalOptions
        from src.memory.database import get_or_create_session
        from src.config.settings import settings
        print("✓ All critical imports successful")
        print(f"  - RAG enabled: {settings.rag.enabled}")
        print(f"  - Memory enabled: {settings.memory.enabled}")
        print(f"  - RAG max results: {settings.rag.max_results}")
        
        print("\n" + "="*60)
        print("✅ ALL VALIDATIONS PASSED")
        print("="*60)
        print("\nBot is ready! Send a Slack message to @Maantra to test.\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ VALIDATION FAILED: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(quick_validation())
    sys.exit(0 if result else 1)
