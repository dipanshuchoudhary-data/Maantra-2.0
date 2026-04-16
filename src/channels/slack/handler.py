"""
Slack Channel Adapter - Implements BaseChannelAdapter for Slack.

Handles:
- Slack events (messages, reactions)
- Message normalization
- Thread summarization
- DM security policy
- LLM provider settings
- Help commands
- Agent processing
"""

import re
import ssl
from typing import Optional, Dict, Any, List
from datetime import datetime

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from src.channels.base_channel import (
    BaseChannelAdapter,
    PlatformMessage,
    PlatformResponse,
)
from src.config.settings import settings
from src.utils.logger import get_logger

from src.memory.database import (
    get_or_create_session,
    get_or_create_unified_user,
    get_session_metadata,
    update_session_metadata,
    is_user_approved,
    generate_pairing_code,
    approve_pairing,
)

from src.agents.agent import Agent, AgentContext, summarize_thread
from src.llm.provider_factory import get_available_providers

logger = get_logger("slack-adapter")


class SlackChannelAdapter(BaseChannelAdapter):
    """Slack implementation of channel adapter"""

    platform_name = "slack"
    supports_threads = True
    supports_reactions = True
    supports_rich_formatting = True
    supports_media = True
    max_message_length = 40000  # Slack limit

    def __init__(self):
        """Initialize Slack adapter"""
        self.app = AsyncApp(
            token=settings.slack_bot_token,
            signing_secret=settings.slack_signing_secret,
        )
        self.app.client.ssl = ssl.create_default_context()
        self.handler: Optional[AsyncSocketModeHandler] = None
        self.bot_id: Optional[str] = None
        self.agent = Agent()
        self._setup_handlers()

    def _setup_handlers(self):
        """Register Slack event handlers"""

        @self.app.event("message")
        async def handle_message(event, say):
            await self._process_message(event, say)

        @self.app.event("reaction_added")
        async def handle_reaction(event, say):
            await self._process_reaction(event, say)

        @self.app.command("/approve")
        async def approve_command(ack, respond, command):
            await ack()
            code = command["text"].strip().upper()

            if not code:
                await respond("Usage: /approve CODE")
                return

            success = approve_pairing(code, command["user_id"])

            if success:
                await respond(f"Pairing code {code} approved")
            else:
                await respond(f"Invalid pairing code {code}")

    async def start(self) -> None:
        """Start Slack socket mode handler"""
        if not settings.slack_app_token:
            raise RuntimeError(
                "SLACK_APP_TOKEN is required to start the Slack socket mode app"
            )

        # Get bot user ID
        auth = await self.app.client.auth_test()
        self.bot_id = auth["user_id"]

        # Start socket mode handler
        self.handler = AsyncSocketModeHandler(
            self.app,
            settings.slack_app_token
        )
        await self.handler.start_async()

        logger.info(f"Slack adapter started (bot_id={self.bot_id})")

    async def stop(self) -> None:
        """Stop Slack handler"""
        if self.handler:
            await self.handler.close_async()
        logger.info("Slack adapter stopped")

    async def normalize_event(self, raw_event: dict) -> Optional[PlatformMessage]:
        """Convert Slack event to PlatformMessage"""
        # Skip system messages
        if raw_event.get("subtype"):
            return None

        # Skip bot's own messages
        if raw_event.get("user") == self.bot_id:
            return None

        text = raw_event.get("text", "")
        if not text:
            return None

        return PlatformMessage(
            text=text,
            user_id=raw_event["user"],  # Will be resolved to unified ID later
            platform_user_id=raw_event["user"],
            platform="slack",
            conversation_id=raw_event["channel"],
            message_id=raw_event["ts"],
            timestamp=datetime.fromtimestamp(float(raw_event["ts"])),
            reply_to_id=raw_event.get("thread_ts"),
            metadata={
                "channel_type": raw_event.get("channel_type"),
                "event_ts": raw_event.get("event_ts"),
            }
        )

    async def send_response(
        self,
        response: PlatformResponse,
        context: Dict[str, Any]
    ) -> bool:
        """Send response to Slack"""
        try:
            kwargs = {
                "channel": context["channel"],
                "text": response.text,
            }

            # Handle threading
            if response.should_thread and context.get("thread_ts"):
                kwargs["thread_ts"] = context["thread_ts"]
            elif response.reply_to_id:
                kwargs["thread_ts"] = response.reply_to_id

            # Handle rich formatting (Slack blocks)
            if response.formatting:
                kwargs["blocks"] = response.formatting.get("blocks")

            await self.app.client.chat_postMessage(**kwargs)
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}", exc_info=True)
            return False

    async def get_user_info(self, platform_user_id: str) -> Dict[str, Any]:
        """Get Slack user info"""
        try:
            result = await self.app.client.users_info(user=platform_user_id)
            user = result["user"]
            return {
                "id": user["id"],
                "name": user.get("real_name") or user.get("name"),
                "email": user.get("profile", {}).get("email"),
                "avatar": user.get("profile", {}).get("image_72"),
            }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return {"id": platform_user_id, "name": "unknown", "real_name": "unknown"}

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[PlatformMessage]:
        """Get Slack conversation history"""
        try:
            result = await self.app.client.conversations_history(
                channel=conversation_id,
                limit=limit
            )
            messages = []
            for msg in result.get("messages", []):
                normalized = await self.normalize_event(msg)
                if normalized:
                    messages.append(normalized)
            return messages
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    # ------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------

    def _is_bot_mentioned(self, text: str) -> bool:
        """Check if bot is mentioned in text"""
        return f"<@{self.bot_id}>" in text

    def _remove_bot_mention(self, text: str) -> str:
        """Remove bot mention from text"""
        return re.sub(f"<@{self.bot_id}>\\s*", "", text).strip()

    def _is_direct_message(self, channel_id: str) -> bool:
        """Check if channel is a DM"""
        return channel_id.startswith("D")

    def _normalize_model_name(self, raw_text: str) -> str:
        """Normalize model name from command"""
        model = raw_text.strip().strip("'\"")

        # Support syntax like: set model = gpt-4o-mini
        if model.startswith("="):
            model = model[1:].strip()

        return model

    async def _get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel info from Slack"""
        try:
            res = await self.app.client.conversations_info(channel=channel_id)
            return {"name": res["channel"]["name"]}
        except Exception:
            return {"name": "unknown"}

    # ------------------------------------------------
    # Message Processing
    # ------------------------------------------------

    async def _process_message(self, event: dict, say) -> None:
        """Process incoming Slack message"""

        logger.info("=== STEP 0: Message event received ===")

        # Skip subtypes (bot messages, edits, etc.)
        if event.get("subtype"):
            logger.info(f"Skipping message subtype: {event.get('subtype')}")
            return

        text = event.get("text")
        user = event.get("user")
        channel = event.get("channel")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts")

        logger.info(f"STEP 1: Raw event extracted | user={user}, channel={channel}, text={text[:50] if text else None}")

        if not text or not user:
            logger.info("STEP 1: Skipping - missing text or user")
            return

        if user == self.bot_id:
            logger.info("STEP 1: Skipping - message from bot itself")
            return

        logger.info(f"STEP 1: Valid message from {user} in {channel}")

        is_dm = self._is_direct_message(channel)

        # ------------------------------------------------
        # DM security policy
        # ------------------------------------------------

        if is_dm and settings.dm_policy != "open":
            if not is_user_approved(user):
                code = generate_pairing_code(user)
                logger.info(f"DM policy: user {user} not approved, sending pairing code")

                await say(
                    text=f"""
Before we chat, you must be approved.

Pairing code: `{code}`

Ask an admin to approve with:
/approve {code}
"""
                )
                return

        # ------------------------------------------------
        # Channel mention policy
        # ------------------------------------------------

        if not is_dm:
            # Check if bot was mentioned and remove the mention if so
            if self._is_bot_mentioned(text):
                clean_text = self._remove_bot_mention(text)
                logger.info(f"STEP 2: Bot mentioned in channel, proceeding")
            else:
                # Also process messages without mention (more flexible)
                clean_text = text
                logger.info(f"STEP 2: Processing channel message without explicit mention")
        else:
            clean_text = text
            logger.info(f"STEP 2: Processing direct message")

        logger.info(f"STEP 2: Cleaned text = '{clean_text}'")

        # ------------------------------------------------
        # Help Command
        # ------------------------------------------------

        if clean_text.lower() in ["help", "/help"]:
            logger.info("STEP 2: Help command detected")

            await say(
                text="""
Maantra Assistant

Commands:
• help
• summarize
• llm options
• llm show
• set provider [openai|openrouter|gemini|grok]
• set model [model-id]
• remind me
• my tasks
• cancel task [id]
• /reset
"""
            )
            return

        # ------------------------------------------------
        # LLM Provider Commands
        # ------------------------------------------------

        command_text = clean_text.strip()
        command_lower = command_text.lower()

        if command_lower in {"llm options", "provider options", "model options"}:
            providers = get_available_providers()
            providers_text = ", ".join(providers) if providers else "none configured"

            await say(
                text=(
                    "LLM selection options\n\n"
                    f"Configured providers: {providers_text}\n"
                    "Use:\n"
                    "• set provider openrouter\n"
                    "• set provider openai\n"
                    "• set provider gemini\n"
                    "• set provider grok\n"
                    "• set model your-model-id\n"
                    "• llm show"
                ),
                thread_ts=thread_ts or ts,
            )
            return

        if command_lower == "llm show":
            unified_user_id = get_or_create_unified_user("slack", user)
            session = get_or_create_session(unified_user_id, channel, thread_ts, platform="slack")
            metadata = get_session_metadata(session["id"])

            selected_provider = metadata.get("llm_provider", "default")
            selected_model = metadata.get("llm_model", "default")

            await say(
                text=(
                    "Current LLM settings\n\n"
                    f"Provider: {selected_provider}\n"
                    f"Model: {selected_model}"
                ),
                thread_ts=thread_ts or ts,
            )
            return

        if command_lower.startswith("set provider "):
            requested_provider = command_text[len("set provider "):].strip().lower()
            available = get_available_providers()

            if requested_provider not in {"openai", "openrouter", "gemini", "grok"}:
                await say(
                    text="Invalid provider. Use one of: openai, openrouter, gemini, grok",
                    thread_ts=thread_ts or ts,
                )
                return

            if requested_provider not in available:
                await say(
                    text=(
                        f"Provider '{requested_provider}' is not configured in environment. "
                        f"Configured providers: {', '.join(available) if available else 'none'}"
                    ),
                    thread_ts=thread_ts or ts,
                )
                return

            unified_user_id = get_or_create_unified_user("slack", user)
            session = get_or_create_session(unified_user_id, channel, thread_ts, platform="slack")
            update_session_metadata(session["id"], {"llm_provider": requested_provider})

            await say(
                text=f"Provider set to {requested_provider}",
                thread_ts=thread_ts or ts,
            )
            return

        if command_lower.startswith("set model "):
            requested_model = self._normalize_model_name(command_text[len("set model "):])

            if not requested_model:
                await say(
                    text="Model name cannot be empty. Example: set model gpt-4o-mini",
                    thread_ts=thread_ts or ts,
                )
                return

            unified_user_id = get_or_create_unified_user("slack", user)
            session = get_or_create_session(unified_user_id, channel, thread_ts, platform="slack")
            update_session_metadata(session["id"], {"llm_model": requested_model})

            await say(
                text=f"Model set to {requested_model}",
                thread_ts=thread_ts or ts,
            )
            return

        # ------------------------------------------------
        # Thread Summarization
        # ------------------------------------------------

        if "summarize" in clean_text.lower() or clean_text.lower() == "tldr":
            logger.info("STEP 2: Summarize command detected")

            if thread_ts:
                replies = await self.app.client.conversations_replies(
                    channel=channel,
                    ts=thread_ts,
                )

                msgs = replies.get("messages", [])

                context = AgentContext(
                    session_id=f"summary:{channel}:{thread_ts}",
                    user_id=user,
                    channel_id=channel,
                    thread_ts=thread_ts,
                )

                summary = await summarize_thread(msgs, context)

                logger.info(f"STEP 5: Sending thread summary to Slack")

                await say(
                    text=f"*Thread Summary*\n\n{summary}",
                    thread_ts=thread_ts,
                )
            else:
                logger.info("STEP 2: Summarize requested but not in thread")

                await say(
                    text="Use summarize inside a thread.",
                    thread_ts=ts,
                )

            return

        # ------------------------------------------------
        # Agent Processing
        # ------------------------------------------------

        logger.info("STEP 3: Beginning agent processing")

        try:
            logger.info(f"STEP 3a: Getting/creating session for user={user}, channel={channel}")

            unified_user_id = get_or_create_unified_user("slack", user, user_info.get("name"))
            session = get_or_create_session(
                unified_user_id,
                channel,
                thread_ts,
                platform="slack",
            )
            session_metadata = get_session_metadata(session["id"])

            logger.info(f"STEP 3b: Got session id={session['id']}")

            logger.info(f"STEP 3c: Fetching user info for {user}")

            user_info = await self.get_user_info(user)

            logger.info(f"STEP 3d: Got user_info: {user_info}")

            channel_info = {"name": "DM"} if is_dm else await self._get_channel_info(channel)

            logger.info(f"STEP 3e: Got channel_info: {channel_info}")

            context = AgentContext(
                session_id=session["id"],
                user_id=unified_user_id,
                channel_id=channel,
                thread_ts=thread_ts,
                user_name=user_info.get("real_name") or user_info.get("name"),
                channel_name=channel_info["name"],
                llm_provider=session_metadata.get("llm_provider"),
                llm_model=session_metadata.get("llm_model"),
            )

            logger.info(f"STEP 3f: Created context | session_id={context.session_id}, user_name={context.user_name}")

            logger.info(f"STEP 4: CALLING AGENT with message: '{clean_text}'")

            response = await self.agent.process_message(clean_text, context)

            logger.info(f"STEP 4: AGENT RETURNED | response.content={response.content[:100] if response.content else 'NONE'} | should_thread={response.should_thread}")

            logger.info(f"STEP 5: SENDING RESPONSE TO SLACK")

            await say(
                text=response.content,
                thread_ts=thread_ts or ts if response.should_thread else None,
            )

            logger.info("STEP 6: SUCCESSFULLY SENT TO SLACK [OK]")

        except Exception as e:
            logger.error(f"[ERROR] AGENT PROCESSING FAILED: {type(e).__name__}: {e}", exc_info=True)

            error_text = str(e).lower()

            if "invalid_api_key" in error_text or "incorrect api key" in error_text:
                user_error = (
                    "AI provider is not configured correctly (invalid OPENAI_API_KEY). "
                    "Please update environment variables and restart the bot."
                )
            elif "timeout" in error_text or "timed out" in error_text:
                user_error = (
                    "AI request timed out. Please try again in a few seconds."
                )
            else:
                user_error = "Sorry, something went wrong processing your message. Check logs for details."

            try:
                await say(
                    text=user_error,
                    thread_ts=thread_ts or ts,
                )
                logger.info("Sent error message to Slack")
            except Exception as say_error:
                logger.error(f"Failed to send error message to Slack: {say_error}", exc_info=True)

    async def _process_reaction(self, event: dict, say) -> None:
        """Process reaction events"""
        # TODO: Implement reaction workflows
        # This can be used for:
        # - Marking messages as important
        # - Quick actions (👍 = approve, ❌ = delete)
        # - Saving to knowledge base
        logger.info(f"Reaction event received: {event.get('reaction')} by {event.get('user')}")
        pass
