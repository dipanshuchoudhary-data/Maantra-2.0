"""
Slack reminder command helpers.
"""

import re
from typing import Any, Dict, List, Optional

from src.channels.slack.formatter import task_cancel_message, task_list_message


class SlackReminderWorkflow:
    """Format and route task commands for Slack."""

    LIST_COMMANDS = {"my tasks", "tasks", "reminders", "my reminders"}

    def __init__(self, scheduler: Any):
        self.scheduler = scheduler

    def is_list_command(self, text: str) -> bool:
        return text.strip().lower() in self.LIST_COMMANDS

    def parse_cancel_command(self, text: str) -> Optional[int]:
        match = re.match(r"^(?:cancel|delete)\s+(?:task|reminder)\s+#?(\d+)$", text.strip().lower())
        if not match:
            return None
        return int(match.group(1))

    def list_tasks(self, user_id: str) -> Dict[str, Any]:
        tasks = self.scheduler.get_user_tasks(user_id)
        pending_tasks = [task for task in tasks if task.get("status") == "pending"]
        return task_list_message(pending_tasks)

    def cancel_task(self, task_id: int, user_id: str) -> Dict[str, Any]:
        cancelled = self.scheduler.cancel_task(task_id, user_id)
        return task_cancel_message(task_id, cancelled)


def visible_task_count(tasks: List[Dict[str, Any]]) -> int:
    return len([task for task in tasks if task.get("status") == "pending"])
