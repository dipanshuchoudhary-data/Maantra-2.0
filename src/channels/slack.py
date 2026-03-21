"""
Slack Channel Integration for Maantra

Handles:
- Slack events
- Slack messages
- Mentions
- Slash commands
- Thread summarization
"""

import asyncio
import re
import ssl
from typing import Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from src.config.settings import settings
from src.utils.logger import get_logger

from src.memory.database import (
    get_or_create_session,
    is_user_approved,
    generate_pairing_code,
    approve_pairing,
)

from src.agents.agent import Agent, AgentContext, summarize_thread
from src.tools.scheduler import task_scheduler

logger = get_logger("slack")

# ------------------------------------------------
# Slack App Initialization
# ------------------------------------------------

slack_app = AsyncApp(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
)

slack_app.client.ssl = ssl.create_default_context()

web_client = slack_app.client

agent = Agent()

bot_user_id: Optional[str] = None
socket_handler: Optional[AsyncSocketModeHandler] = None


# ------------------------------------------------
# Utility Helpers
# ------------------------------------------------


async def get_bot_user_id() -> str:
    global bot_user_id

    if bot_user_id:
        return bot_user_id

    auth = await web_client.auth_test()

    bot_user_id = auth["user_id"]

    return bot_user_id


def is_bot_mentioned(text: str, bot_id: str) -> bool:
    return f"<@{bot_id}>" in text


def remove_bot_mention(text: str, bot_id: str) -> str:
    return re.sub(f"<@{bot_id}>\\s*", "", text).strip()


def is_direct_message(channel_id: str) -> bool:
    return channel_id.startswith("D")


async def get_user_info(user_id: str):

    try:

        res = await web_client.users_info(user=user_id)

        user = res["user"]

        return {
            "name": user.get("name", "unknown"),
            "real_name": user.get("real_name", "unknown"),
        }

    except Exception:

        return {"name": "unknown", "real_name": "unknown"}


async def get_channel_info(channel_id: str):

    try:

        res = await web_client.conversations_info(channel=channel_id)

        return {"name": res["channel"]["name"]}

    except Exception:

        return {"name": "unknown"}


# ------------------------------------------------
# Message Handler
# ------------------------------------------------


@slack_app.event("message")
async def handle_message(event, say):

    logger.info("=== STEP 0: Message event received ===")

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

    bot_id = await get_bot_user_id()

    if user == bot_id:
        logger.info("STEP 1: Skipping - message from bot itself")
        return

    logger.info(f"STEP 1: Valid message from {user} in {channel}")

    is_dm = is_direct_message(channel)

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
        if is_bot_mentioned(text, bot_id):
            clean_text = remove_bot_mention(text, bot_id)
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
    # Help
    # ------------------------------------------------

    if clean_text.lower() in ["help", "/help"]:

        logger.info("STEP 2: Help command detected")

        await say(
            text="""
Maantra Assistant

Commands:
• help
• summarize
• remind me
• my tasks
• cancel task [id]
• /reset
"""
        )

        return

    # ------------------------------------------------
    # Thread Summarization
    # ------------------------------------------------

    if "summarize" in clean_text.lower() or clean_text.lower() == "tldr":

        logger.info("STEP 2: Summarize command detected")

        if thread_ts:

            replies = await web_client.conversations_replies(
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
    # Agent Processing (WITH COMPREHENSIVE DEBUG)
    # ------------------------------------------------

    logger.info("STEP 3: Beginning agent processing")

    try:

        logger.info(f"STEP 3a: Getting/creating session for user={user}, channel={channel}")

        session = get_or_create_session(user, channel, thread_ts)

        logger.info(f"STEP 3b: Got session id={session['id']}")

        logger.info(f"STEP 3c: Fetching user info for {user}")

        user_info = await get_user_info(user)

        logger.info(f"STEP 3d: Got user_info: {user_info}")

        channel_info = {"name": "DM"} if is_dm else await get_channel_info(channel)

        logger.info(f"STEP 3e: Got channel_info: {channel_info}")

        context = AgentContext(
            session_id=session["id"],
            user_id=user,
            channel_id=channel,
            thread_ts=thread_ts,
            user_name=user_info["real_name"],
            channel_name=channel_info["name"],
        )

        logger.info(f"STEP 3f: Created context | session_id={context.session_id}, user_name={context.user_name}")

        logger.info(f"STEP 4: CALLING AGENT with message: '{clean_text}'")

        response = await agent.process_message(clean_text, context)

        logger.info(f"STEP 4: AGENT RETURNED | response.content={response.content[:100] if response.content else 'NONE'} | should_thread={response.should_thread}")

        logger.info(f"STEP 5: SENDING RESPONSE TO SLACK")

        await say(
            text=response.content,
            thread_ts=thread_ts or ts if response.should_thread else None,
        )

        logger.info("STEP 6: SUCCESSFULLY SENT TO SLACK [OK]")

    except Exception as e:

        logger.error(f"[ERROR] AGENT PROCESSING FAILED at some step: {type(e).__name__}: {e}", exc_info=True)

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


# ------------------------------------------------
# Slash Commands
# ------------------------------------------------


@slack_app.command("/approve")
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


# ------------------------------------------------
# Startup / Shutdown
# ------------------------------------------------


async def start_slack_app():

    global socket_handler

    if not settings.slack_app_token:
        raise RuntimeError(
            "SLACK_APP_TOKEN is required to start the Slack socket mode app"
        )

    socket_handler = AsyncSocketModeHandler(
        slack_app,
        settings.slack_app_token
    )

    await socket_handler.start_async()

    bot_id = await get_bot_user_id()

    logger.info(f"Slack bot started. Bot ID: {bot_id}")


async def stop_slack_app():

    if socket_handler:
        await socket_handler.close_async()

    logger.info("Slack bot stopped")
