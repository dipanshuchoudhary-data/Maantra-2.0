"""
Slack Actions Module

Provides helper utilities for interacting with the Slack API.
Handles users, channels, messages, history retrieval, and search.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.config.settings import config
from src.utils.logger import get_logger

logger = get_logger("slack-actions")

# Slack client
web_client = AsyncWebClient(token=config.slack.bot_token)


# =========================================================
# Data Models
# =========================================================

@dataclass
class SlackUser:
    id: str
    name: str
    real_name: str
    email: Optional[str] = None


@dataclass
class SlackChannel:
    id: str
    name: str
    is_private: bool
    is_member: bool


@dataclass
class SlackMessage:
    ts: str
    user: str
    user_name: str
    text: str
    thread_ts: Optional[str]
    timestamp: datetime


# =========================================================
# User Operations
# =========================================================

async def get_user_info(user_id: str) -> Optional[SlackUser]:

    try:
        result = await web_client.users_info(user=user_id)

        user = result["user"]

        return SlackUser(
            id=user["id"],
            name=user.get("name", "unknown"),
            real_name=user.get("real_name", user.get("name", "unknown")),
            email=user.get("profile", {}).get("email"),
        )

    except SlackApiError as e:
        logger.error(f"Failed to get user {user_id}: {e.response['error']}")
        return None


async def list_users() -> List[SlackUser]:

    try:

        result = await web_client.users_list()

        users = []

        for u in result["members"]:

            if u.get("deleted") or u.get("is_bot"):
                continue

            users.append(
                SlackUser(
                    id=u["id"],
                    name=u.get("name", "unknown"),
                    real_name=u.get("real_name", "unknown"),
                    email=u.get("profile", {}).get("email"),
                )
            )

        return users

    except SlackApiError as e:
        logger.error(f"Failed listing users: {e.response['error']}")
        return []


# =========================================================
# Channel Operations
# =========================================================

async def list_channels() -> List[SlackChannel]:

    try:

        result = await web_client.conversations_list(
            types="public_channel,private_channel",
            exclude_archived=True,
        )

        channels = []

        for c in result["channels"]:

            channels.append(
                SlackChannel(
                    id=c["id"],
                    name=c.get("name", "unknown"),
                    is_private=c.get("is_private", False),
                    is_member=c.get("is_member", False),
                )
            )

        return channels

    except SlackApiError as e:
        logger.error(f"Failed listing channels: {e.response['error']}")
        return []


async def find_channel(name: str) -> Optional[SlackChannel]:

    channels = await list_channels()

    name = name.replace("#", "").lower()

    for c in channels:
        if c.name.lower() == name:
            return c

    return None


# =========================================================
# Messaging
# =========================================================

async def send_channel_message(
    channel_id: str,
    text: str,
    thread_ts: Optional[str] = None,
):

    try:

        result = await web_client.chat_postMessage(
            channel=channel_id,
            text=text,
            thread_ts=thread_ts,
        )

        return {
            "success": True,
            "ts": result["ts"],
        }

    except SlackApiError as e:

        logger.error(f"Failed sending message: {e.response['error']}")

        return {
            "success": False,
            "error": e.response["error"],
        }


async def send_direct_message(user_id: str, text: str):

    try:

        dm = await web_client.conversations_open(users=user_id)

        channel_id = dm["channel"]["id"]

        return await send_channel_message(channel_id, text)

    except SlackApiError as e:

        logger.error(f"Failed DM: {e.response['error']}")

        return {
            "success": False,
            "error": e.response["error"],
        }


async def send_message(target: str, message: str):

    if target.startswith("#"):

        channel = await find_channel(target)

        if not channel:
            return {"success": False, "error": "Channel not found"}

        if not channel.is_member:
            return {
                "success": False,
                "error": f"Bot is not in #{channel.name}",
            }

        return await send_channel_message(channel.id, message)

    return await send_direct_message(target, message)


# =========================================================
# Conversation History
# =========================================================

async def get_channel_history(
    channel_id: str,
    limit: int = 50,
) -> List[SlackMessage]:

    try:

        result = await web_client.conversations_history(
            channel=channel_id,
            limit=limit,
        )

        messages: List[SlackMessage] = []

        for m in result["messages"]:

            if not m.get("text"):
                continue

            user_name = "unknown"

            if m.get("user"):
                user = await get_user_info(m["user"])
                if user:
                    user_name = user.real_name

            messages.append(
                SlackMessage(
                    ts=m["ts"],
                    user=m.get("user", "unknown"),
                    user_name=user_name,
                    text=m["text"],
                    thread_ts=m.get("thread_ts"),
                    timestamp=datetime.fromtimestamp(float(m["ts"])),
                )
            )

        return list(reversed(messages))

    except SlackApiError as e:

        logger.error(f"History failed: {e.response['error']}")

        return []


async def get_thread_replies(
    channel_id: str,
    thread_ts: str,
) -> List[SlackMessage]:

    try:

        result = await web_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
        )

        replies = []

        for m in result["messages"]:

            if not m.get("text"):
                continue

            user_name = "unknown"

            if m.get("user"):
                user = await get_user_info(m["user"])
                if user:
                    user_name = user.real_name

            replies.append(
                SlackMessage(
                    ts=m["ts"],
                    user=m.get("user", "unknown"),
                    user_name=user_name,
                    text=m["text"],
                    thread_ts=m.get("thread_ts"),
                    timestamp=datetime.fromtimestamp(float(m["ts"])),
                )
            )

        return replies

    except SlackApiError as e:

        logger.error(f"Thread fetch failed: {e.response['error']}")

        return []


# =========================================================
# Search
# =========================================================

async def search_messages(
    query: str,
    channel_id: Optional[str] = None,
    limit: int = 20,
) -> List[SlackMessage]:

    if channel_id:

        history = await get_channel_history(channel_id, 200)

        query = query.lower()

        return [
            m for m in history if query in m.text.lower()
        ][:limit]

    channels = await list_channels()

    results: List[SlackMessage] = []

    for channel in channels[:10]:

        if not channel.is_member:
            continue

        history = await get_channel_history(channel.id, 100)

        for msg in history:

            if query.lower() in msg.text.lower():

                results.append(msg)

                if len(results) >= limit:
                    return results

    return results


# =========================================================
# Formatting
# =========================================================

def format_messages_for_context(messages: List[SlackMessage]) -> str:

    formatted = []

    for m in messages:

        time = m.timestamp.strftime("%Y-%m-%d %H:%M")

        formatted.append(
            f"[{time}] {m.user_name}: {m.text}"
        )

    return "\n".join(formatted)