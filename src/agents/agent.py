"""
Maantra AI Agent

Central orchestration layer integrating:

1. RAG retrieval (Slack knowledge search)
2. Long-term user memory
3. Tool execution
4. Multi-LLM providers
5. MCP external integrations

Architecture Flow

User Message
      ↓
Memory Retrieval
      ↓
RAG Retrieval
      ↓
LLM Reasoning
      ↓
Tool Execution Loop
      ↓
Final Response
      ↓
Memory Update
"""

import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from src.config.settings import settings
from src.utils.logger import get_logger

from src.memory.database import (
    get_session_history,
    add_message,
)

from src.rag.retriever import retrieve

from src.tools.slack_actions import send_message, list_channels
from src.tools.scheduler import task_scheduler

from src.llm.provider_factory import get_llm_provider

logger = get_logger("agent")


# ------------------------------------------------------------------
# SYSTEM PROMPT
# ------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a helpful AI assistant integrated into Slack.

Capabilities:
• Search Slack discussion history
• Use tools to perform actions
• Access external integrations
• Use long-term memory

Guidelines:

1. Use knowledge search when asked about past discussions
2. Use tools when actions are required
3. Never invent tool capabilities
4. Keep answers concise and Slack-friendly
5. Prefer structured responses when possible
"""


# ------------------------------------------------------------------
# DATA STRUCTURES
# ------------------------------------------------------------------

@dataclass
class AgentContext:
    session_id: str
    user_id: str
    channel_id: Optional[str]
    thread_ts: Optional[str]

    channel_name: Optional[str] = None
    user_name: Optional[str] = None


@dataclass
class AgentResponse:
    content: str
    should_thread: bool

    rag_used: bool
    sources_count: int

    memory_used: bool
    memories_count: int


# ------------------------------------------------------------------
# AGENT IMPLEMENTATION
# ------------------------------------------------------------------


class Agent:
    """
    Core AI orchestration engine.
    Responsible for reasoning, tool usage, memory and RAG integration.
    """

    def __init__(self):

        self.llm = get_llm_provider()

        self.max_history_messages = 10
        self.max_tool_iterations = 5

    # ------------------------------------------------------------------
    # MEMORY RETRIEVAL
    # ------------------------------------------------------------------

    async def _retrieve_memory(
        self,
        user_message: str,
        user_id: str,
    ) -> tuple[str, int]:

        if not settings.memory_enabled:
            return "", 0

        try:

            from src.memory_ai.mem0_client import (
                search_memory,
                build_memory_context,
            )

            memories = await search_memory(
                user_message,
                user_id,
                limit=5,
            )

            if not memories:
                return "", 0

            context = build_memory_context(memories)

            return context, len(memories)

        except Exception as e:

            logger.error(f"Memory retrieval failed: {e}")

            return "", 0

    # ------------------------------------------------------------------
    # RAG RETRIEVAL
    # ------------------------------------------------------------------

    async def _retrieve_rag(self, query: str) -> tuple[str, int]:

        if not settings.rag_enabled:
            return "", 0

        try:

            results = await retrieve(
                query=query,
                limit=settings.rag_max_results,
                min_score=settings.rag_min_similarity,
            )

            if not results:
                return "", 0

            context_chunks = [r["text"] for r in results]

            context = "\n\n".join(context_chunks)

            return context, len(results)

        except Exception as e:

            logger.error(f"RAG retrieval failed: {e}")

            return "", 0

    # ------------------------------------------------------------------
    # MESSAGE BUILDER
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        history,
        memory_context: str,
        rag_context: str,
    ) -> List[Dict[str, Any]]:

        messages: List[Dict[str, Any]] = []

        messages.append(
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        )

        if memory_context:

            messages.append(
                {
                    "role": "system",
                    "content": f"User memory:\n{memory_context}",
                }
            )

        if rag_context:

            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant Slack discussions:\n{rag_context}",
                }
            )

        for msg in history[-self.max_history_messages:]:

            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return messages

    # ------------------------------------------------------------------
    # TOOL EXECUTION LOOP
    # ------------------------------------------------------------------

    async def _run_tool_loop(
        self,
        messages: List[Dict[str, Any]],
        tools,
        context: AgentContext,
    ) -> Dict[str, Any]:

        iteration = 0

        response = await self.llm.chat(
            messages=messages,
            tools=tools,
        )

        assistant_message = response["message"]

        while assistant_message.get("tool_calls"):

            if iteration >= self.max_tool_iterations:

                logger.warning("Max tool iterations reached")
                break

            iteration += 1

            messages.append(assistant_message)

            for tool_call in assistant_message["tool_calls"]:

                tool_name = tool_call["name"]

                arguments = tool_call.get("arguments", {})

                if isinstance(arguments, str):
                    arguments = json.loads(arguments)

                logger.info(f"Executing tool: {tool_name}")

                try:

                    result = await execute_tool(
                        name=tool_name,
                        args=arguments,
                        context=context,
                    )

                except Exception as e:

                    logger.error(f"Tool failed: {e}")

                    result = f"Tool execution failed: {str(e)}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )

            response = await self.llm.chat(
                messages=messages,
                tools=tools,
            )

            assistant_message = response["message"]

        return assistant_message

    # ------------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------------

    async def process_message(
        self,
        user_message: str,
        context: AgentContext,
    ) -> AgentResponse:

        logger.info(f"Processing session {context.session_id}")

        add_message(context.session_id, "user", user_message)

        # --------------------------------------------------------------
        # MEMORY
        # --------------------------------------------------------------

        memory_context, memories_count = await self._retrieve_memory(
            user_message,
            context.user_id,
        )

        memory_used = memories_count > 0

        # --------------------------------------------------------------
        # RAG
        # --------------------------------------------------------------

        rag_context, sources_count = await self._retrieve_rag(user_message)

        rag_used = sources_count > 0

        # --------------------------------------------------------------
        # BUILD MESSAGE CONTEXT
        # --------------------------------------------------------------

        history = get_session_history(context.session_id)

        messages = self._build_messages(
            user_message=user_message,
            history=history,
            memory_context=memory_context,
            rag_context=rag_context,
        )

        # --------------------------------------------------------------
        # TOOL REGISTRY
        # --------------------------------------------------------------

        tools = get_all_tools()

        logger.info(f"LLM call with {len(tools)} tools")

        # --------------------------------------------------------------
        # TOOL LOOP
        # --------------------------------------------------------------

        assistant_message = await self._run_tool_loop(
            messages=messages,
            tools=tools,
            context=context,
        )

        content = assistant_message.get(
            "content",
            "I encountered an issue processing your request.",
        )

        add_message(context.session_id, "assistant", content)

        # --------------------------------------------------------------
        # STORE MEMORY
        # --------------------------------------------------------------

        if settings.memory_enabled:

            try:

                from src.memory_ai.mem0_client import add_memory

                await add_memory(
                    [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": content},
                    ],
                    context.user_id,
                )

            except Exception as e:

                logger.error(f"Memory storage failed: {e}")

        # --------------------------------------------------------------
        # RETURN RESPONSE
        # --------------------------------------------------------------

        return AgentResponse(
            content=content,
            should_thread=context.thread_ts is not None or len(content) > 500,

            rag_used=rag_used,
            sources_count=sources_count,

            memory_used=memory_used,
            memories_count=memories_count,
        )


# ------------------------------------------------------------------
# THREAD SUMMARIZATION
# ------------------------------------------------------------------


async def summarize_thread(messages, context: AgentContext) -> str:

    if not messages:
        return "No messages to summarize."

    conversation = "\n\n".join(
        f"[{m.role}] {m.content}" for m in messages
    )

    prompt = f"""
Summarize this Slack thread.

Focus on:
• Key topics
• Decisions
• Action items
• Unresolved questions

Conversation:
{conversation}

Summary:
"""

    llm = get_llm_provider()

    response = await llm.chat(
        messages=[
            {
                "role": "system",
                "content": "You summarize Slack discussions.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    return response["message"].get(
        "content",
        "Failed to generate summary.",
    )