#!/usr/bin/env python3
"""
Checks Slack formatting helpers and reaction routing.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.channels.slack.formatter import help_message  # noqa: E402
from src.features.slack.analytics import calculate_channel_stats  # noqa: E402
from src.features.slack.reactions import SlackReactionWorkflow  # noqa: E402
from src.features.slack.reminders import SlackReminderWorkflow, visible_task_count  # noqa: E402


class FakeScheduler:
    def get_user_tasks(self, user_id):
        return [
            {"id": 1, "task_description": "Ship update", "status": "pending"},
            {"id": 2, "task_description": "Old task", "status": "completed"},
        ]

    def cancel_task(self, task_id, user_id):
        return task_id == 1


async def main() -> int:
    payload = help_message()
    if not payload.get("text"):
        print("[FAILED] Help formatter missing fallback text")
        return 1

    blocks = payload.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        print("[FAILED] Help formatter missing Slack blocks")
        return 1

    workflow = SlackReactionWorkflow()
    handled = await workflow.handle(
        event={
            "reaction": "thumbsup",
            "user": "U_SLACK_CHECK",
            "item": {"type": "message", "channel": "C_SLACK_CHECK", "ts": "1.23"},
        },
        client=object(),
        bot_user_id="U_BOT",
    )
    if handled:
        print("[FAILED] Unrelated reaction should not be handled")
        return 1

    reminders = SlackReminderWorkflow(FakeScheduler())
    if not reminders.is_list_command("my tasks"):
        print("[FAILED] Task list command was not recognized")
        return 1

    if reminders.parse_cancel_command("cancel task #12") != 12:
        print("[FAILED] Cancel task command was not parsed")
        return 1

    if visible_task_count(FakeScheduler().get_user_tasks("U_SLACK_CHECK")) != 1:
        print("[FAILED] Pending task count is wrong")
        return 1

    stats = calculate_channel_stats(
        [
            {"user": "U1", "ts": "1"},
            {"user": "U1", "ts": "2", "thread_ts": "1"},
            {"user": "U2", "ts": "3"},
        ]
    )
    if stats["messages_scanned"] != 3 or stats["unique_users"] != 2:
        print("[FAILED] Channel stats calculation is wrong")
        return 1

    print("[SUCCESS] Slack feature checks passed")
    print(f"Help message blocks: {len(blocks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
