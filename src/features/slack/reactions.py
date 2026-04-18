"""
Slack reaction workflows.

- memo/page_facing_up/spiral_note_pad summarize the message thread
- bookmark stores the reacted message in the local message log
"""

from typing import Any, Awaitable, Callable, Dict, Optional

from src.memory.database import add_message
from src.utils.logger import get_logger

logger = get_logger("slack-reactions")

SummaryBuilder = Callable[[list, str, str, str], Awaitable[str]]


class SlackReactionWorkflow:
    """Handle Slack reaction shortcuts."""

    SUMMARY_REACTIONS = {"memo", "page_facing_up", "spiral_note_pad"}
    SAVE_REACTIONS = {"bookmark"}

    async def handle(
        self,
        *,
        event: Dict[str, Any],
        client: Any,
        bot_user_id: Optional[str] = None,
        summary_builder: Optional[SummaryBuilder] = None,
    ) -> bool:
        reaction = event.get("reaction")
        user_id = event.get("user")
        item = event.get("item") or {}

        if not reaction or item.get("type") != "message":
            return False

        if bot_user_id and user_id == bot_user_id:
            return False

        channel_id = item.get("channel")
        message_ts = item.get("ts")
        if not channel_id or not message_ts:
            return False

        if reaction in self.SUMMARY_REACTIONS:
            return await self._summarize_thread(
                client=client,
                channel_id=channel_id,
                message_ts=message_ts,
                user_id=user_id,
                summary_builder=summary_builder,
            )

        if reaction in self.SAVE_REACTIONS:
            return await self._save_message(
                client=client,
                channel_id=channel_id,
                message_ts=message_ts,
                user_id=user_id,
            )

        return False

    async def _summarize_thread(
        self,
        *,
        client: Any,
        channel_id: str,
        message_ts: str,
        user_id: str,
        summary_builder: Optional[SummaryBuilder],
    ) -> bool:
        if not summary_builder:
            logger.warning("Summary reaction ignored because no summary builder was provided")
            return False

        replies = await client.conversations_replies(channel=channel_id, ts=message_ts)
        messages = replies.get("messages", [])
        summary = await summary_builder(messages, channel_id, message_ts, user_id)

        await client.chat_postMessage(
            channel=channel_id,
            text=f"*Thread Summary*\n\n{summary}",
            thread_ts=message_ts,
        )
        return True

    async def _save_message(
        self,
        *,
        client: Any,
        channel_id: str,
        message_ts: str,
        user_id: str,
    ) -> bool:
        history = await client.conversations_history(
            channel=channel_id,
            latest=message_ts,
            inclusive=True,
            limit=1,
        )
        messages = history.get("messages", [])
        if not messages:
            return False

        message = messages[0]
        text = message.get("text") or ""
        if not text:
            return False

        add_message(
            session_id=f"saved:slack:{channel_id}",
            role="system",
            content=text,
            slack_ts=message_ts,
            metadata={
                "source": "reaction:bookmark",
                "saved_by": user_id,
                "channel_id": channel_id,
            },
        )

        await client.reactions_add(
            channel=channel_id,
            timestamp=message_ts,
            name="white_check_mark",
        )
        return True
