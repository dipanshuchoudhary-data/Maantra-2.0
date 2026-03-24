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
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from src.config.settings import settings
from src.utils.logger import get_logger

from src.memory.database import (
    get_session_history,
    add_message,
)

from src.rag.retriever import retrieve, RetrievalOptions

from src.tools.slack_actions import send_message, list_channels
from src.tools.scheduler import (
    task_scheduler,
    parse_relative_time,
    to_cron_expression,
)

from src.llm.provider_factory import get_llm_provider

# MCP tools
from src.mcp import (
    get_all_mcp_tools,
    execute_mcp_tool,
    parse_tool_name,
    format_mcp_result,
    mcp_tools_to_openai,
)

logger = get_logger("agent")


def _has_usable_key(api_key: str | None) -> bool:

    if not api_key:
        return False

    lowered = api_key.strip().lower()

    placeholders = {
        "",
        "sk-xxxxxxxx",
        "your_openai_api_key",
        "replace_me",
        "changeme",
    }

    return lowered not in placeholders


def _has_rag_embedding_key() -> bool:

    provider = (settings.rag.embedding_provider or "openai").lower()

    if provider == "cohere":
        return _has_usable_key(settings.ai.cohere_api_key)

    if provider == "openrouter":
        return _has_usable_key(settings.ai.openrouter_api_key)

    return _has_usable_key(settings.ai.openai_api_key)


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
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


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

        self.default_llm = get_llm_provider()

        self.max_history_messages = 5
        self.max_tool_iterations = 5

    # ------------------------------------------------------------------
    # MEMORY RETRIEVAL
    # ------------------------------------------------------------------

    async def _retrieve_memory(
        self,
        user_message: str,
        user_id: str,
    ) -> tuple[str, int]:

        if not settings.memory.enabled:
            return "", 0

        try:

            from src.memory_ai.mem0_client import (
                search_memory,
                build_memory_context,
            )

            memories = await search_memory(
                user_message,
                user_id,
                limit=3,
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

        if not settings.rag.enabled:
            return "", 0

        if not _has_rag_embedding_key():
            return "", 0

        try:

            response = await retrieve(
                query=query,
                options=RetrievalOptions(
                    limit=settings.rag.max_results,
                    min_score=settings.rag.min_similarity,
                )
            )

            if not response.results:
                return "", 0

            # Truncate each chunk to max 500 chars to save tokens
            context_chunks = []
            for r in response.results:
                text = r.text[:500] + "..." if len(r.text) > 500 else r.text
                context_chunks.append(text)

            context = "\n\n".join(context_chunks)

            # Cap total RAG context at 2000 chars
            if len(context) > 2000:
                context = context[:2000] + "\n\n[truncated]"

            return context, len(response.results)

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
                    "role": msg["role"],
                    "content": msg["content"],
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
        llm_provider,
    ) -> Dict[str, Any]:

        iteration = 0

        # If no tools, make a simple chat call (no tool_calls expected)
        if not tools:
            response = await llm_provider.chat(messages=messages, tools=None)
            return response["message"]

        response = await llm_provider.chat(
            messages=messages,
            tools=tools,
        )

        assistant_message = response["message"]
        assistant_message["tool_calls"] = response.get("tool_calls", [])

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

            response = await llm_provider.chat(
                messages=messages,
                tools=tools,
            )

            assistant_message = response["message"]
            assistant_message["tool_calls"] = response.get("tool_calls", [])

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
        # SMART TOOL LOADING
        # --------------------------------------------------------------

        # Use keyword-based tool loading to reduce token count
        # Only loads MCP tools when query indicates they're needed
        tools = get_tools_for_query(user_message)

        logger.info(f"LLM call with {len(tools)} tools")

        if context.llm_provider:
            llm_provider = get_llm_provider(
                provider_name=context.llm_provider,
                model_name=context.llm_model,
            )
            logger.info(
                f"Using session-selected provider={context.llm_provider} "
                f"model={context.llm_model or 'default'}"
            )
        else:
            llm_provider = self.default_llm

        # --------------------------------------------------------------
        # TOOL LOOP
        # --------------------------------------------------------------

        assistant_message = await self._run_tool_loop(
            messages=messages,
            tools=tools,
            context=context,
            llm_provider=llm_provider,
        )

        content = assistant_message.get("content")
        if not content:
            content = "I encountered an issue processing your request."

        add_message(context.session_id, "assistant", content)

        # --------------------------------------------------------------
        # STORE MEMORY
        # --------------------------------------------------------------

        if settings.memory.enabled:

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
# TOOL EXECUTION
# ------------------------------------------------------------------

async def execute_tool(
    name: str,
    args: dict,
    context: AgentContext,
) -> str:
    """Execute a tool by name and return the result as a string."""
    
    logger.info(f"Executing tool: {name} with args: {args}")
    
    # Try to execute as MCP tool first
    parsed = parse_tool_name(name)
    
    if parsed:
        try:
            result = await execute_mcp_tool(
                server_name=parsed["serverName"],
                tool_name=parsed["toolName"],
                args=args,
            )
            
            formatted = format_mcp_result(result)
            
            logger.info(f"MCP tool succeeded: {formatted[:100]}")
            
            return formatted
            
        except Exception as e:
            logger.error(f"MCP tool failed: {e}")
            raise
    
    # Local tools
    if name == "send_message":
        result = await send_message(
            target=args.get("target"),
            message=args.get("message"),
        )
        return str(result)
    
    if name == "list_channels":
        channels = await list_channels()
        return "\n".join([f"#{c.name}" for c in channels])
    
    if name == "schedule_task":
        scheduled_time = args.get("scheduled_time")
        cron_expression = args.get("cron_expression")

        if isinstance(scheduled_time, str):
            parsed_relative_time = parse_relative_time(scheduled_time)

            if parsed_relative_time:
                scheduled_time = parsed_relative_time
            else:
                try:
                    scheduled_time = datetime.fromisoformat(scheduled_time)
                except ValueError:
                    scheduled_time = None

        if not cron_expression and isinstance(args.get("description"), str):
            cron_expression = to_cron_expression(args["description"])

        task = await task_scheduler.schedule_task(
            user_id=context.user_id,
            channel_id=context.channel_id,
            description=args.get("description"),
            scheduled_time=scheduled_time,
            cron_expression=cron_expression,
            thread_ts=context.thread_ts,
        )
        return f"Task scheduled: {task}"
    
    raise ValueError(f"Unknown tool: {name}")


def get_all_tools():
    """Get all available tools for the agent."""

    tools = []

    # Local tools
    tools.append({
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to a Slack channel or user",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Channel ID, channel name (with #), or user ID"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message text to send"
                    }
                },
                "required": ["target", "message"]
            }
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "list_channels",
            "description": "List all Slack channels the bot is a member of",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    })

    tools.append({
        "type": "function",
        "function": {
            "name": "schedule_task",
            "description": "Schedule a task or reminder",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What to remind about"
                    },
                    "scheduled_time": {
                        "type": "string",
                        "description": "When to execute (ISO format or relative like 'in 5 minutes')"
                    },
                    "cron_expression": {
                        "type": "string",
                        "description": "Recurring schedule (cron format, optional)"
                    }
                },
                "required": ["description"]
            }
        }
    })

    return tools


def _needs_tools(query: str) -> bool:
    """
    Determine if query likely needs tool execution.
    Returns False for simple conversational queries to skip tools entirely.
    """
    query_lower = query.lower().strip()

    # Action keywords that indicate tools might be needed
    action_keywords = [
        # Slack actions
        "send", "message", "post", "channel", "dm", "notify",
        # Scheduling
        "remind", "schedule", "timer", "alarm", "later", "tomorrow",
        "in 5 minutes", "in an hour", "at",
        # MCP/external actions
        "github", "repo", "repository", "pull request", "pr",
        "issue", "commit", "branch", "merge", "code review",
        "notion", "page", "database", "doc", "document",
        "notes", "wiki", "knowledge base",
        # General action words
        "create", "list", "show me", "find", "search for", "look up",
    ]

    return any(kw in query_lower for kw in action_keywords)


def get_tools_for_query(query: str):
    """
    Smart tool loading - only load tools when query indicates need.
    Saves thousands of tokens on conversational queries.
    """
    query_lower = query.lower()

    # Skip tools entirely for simple conversational queries
    if not _needs_tools(query):
        logger.info("No tools needed for this query (conversational)")
        return []

    # Start with local tools for action queries
    tools = get_all_tools()

    # Keywords that indicate GitHub tools needed
    github_keywords = [
        "github", "repo", "repository", "pull request", "pr",
        "issue", "commit", "branch", "merge", "code review"
    ]

    # Keywords that indicate Notion tools needed
    notion_keywords = [
        "notion", "page", "database", "doc", "document",
        "notes", "wiki", "knowledge base"
    ]

    need_github = any(kw in query_lower for kw in github_keywords)
    need_notion = any(kw in query_lower for kw in notion_keywords)

    # If no MCP tools needed, return just local tools
    if not need_github and not need_notion:
        logger.info(f"Using {len(tools)} local tools only")
        return tools

    # Load only needed MCP tools
    try:
        mcp_tools = get_all_mcp_tools()

        filtered_tools = []
        for tool in mcp_tools:
            server_name = tool.get("serverName", "").lower()
            if need_github and "github" in server_name:
                filtered_tools.append(tool)
            elif need_notion and "notion" in server_name:
                filtered_tools.append(tool)

        if filtered_tools:
            tools.extend(mcp_tools_to_openai(filtered_tools))
            logger.info(f"Added {len(filtered_tools)} MCP tools (filtered)")

    except Exception as e:
        logger.warning(f"Failed to load MCP tools: {e}")

    return tools




async def summarize_thread(messages, context: AgentContext) -> str:

    if not messages:
        return "No messages to summarize."

    conversation = "\n\n".join(
        f"[{m.get('role', 'user')}] {m.get('text') or m.get('content', '')}"
        for m in messages
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
