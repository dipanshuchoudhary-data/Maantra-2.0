"""
Slack reminder command helpers.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.channels.slack.formatter import (
    reminder_created_message,
    reminder_parse_error_message,
    task_cancel_message,
    task_list_message,
)
from src.tools.scheduler import parse_relative_time, to_cron_expression


@dataclass
class ReminderRequest:
    description: str
    scheduled_time: Optional[datetime] = None
    cron_expression: Optional[str] = None


class SlackReminderWorkflow:
    """Format and route task commands for Slack."""

    LIST_COMMANDS = {"my tasks", "tasks", "reminders", "my reminders"}
    REMIND_PREFIX = "remind me"

    def __init__(self, scheduler: Any):
        self.scheduler = scheduler

    def is_list_command(self, text: str) -> bool:
        return text.strip().lower() in self.LIST_COMMANDS

    def parse_cancel_command(self, text: str) -> Optional[int]:
        match = re.match(r"^(?:cancel|delete)\s+(?:task|reminder)\s+#?(\d+)$", text.strip().lower())
        if not match:
            return None
        return int(match.group(1))

    def is_create_command(self, text: str) -> bool:
        return text.strip().lower().startswith(self.REMIND_PREFIX)

    def parse_create_command(self, text: str) -> Optional[ReminderRequest]:
        raw = text.strip()
        lowered = raw.lower()
        if not lowered.startswith(self.REMIND_PREFIX):
            return None

        body = raw[len(self.REMIND_PREFIX):].strip()
        body = re.sub(r"^to\s+", "", body, flags=re.IGNORECASE).strip()
        if not body:
            return None

        relative_match = re.match(
            r"^(?P<desc>.+?)\s+in\s+(?P<num>\d+)\s+(?P<unit>minute|hour|day|week)s?$",
            body,
            flags=re.IGNORECASE,
        )
        if relative_match:
            description = relative_match.group("desc").strip(" .")
            schedule_text = f"in {relative_match.group('num')} {relative_match.group('unit')}"
            scheduled_time = parse_relative_time(schedule_text)
            if description and scheduled_time:
                return ReminderRequest(description=description, scheduled_time=scheduled_time)
            return None

        recurring_match = re.match(
            r"^(?P<desc>.+?)\s+(?P<schedule>every\s+.+)$",
            body,
            flags=re.IGNORECASE,
        )
        if recurring_match:
            description = recurring_match.group("desc").strip(" .")
            schedule_text = recurring_match.group("schedule").lower().strip()
            cron_expression = to_cron_expression(schedule_text)
            if description and cron_expression:
                return ReminderRequest(description=description, cron_expression=cron_expression)
            return None

        absolute_match = re.match(
            r"^(?P<desc>.+?)\s+(?:at|tomorrow)\s+(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)?)$",
            body,
            flags=re.IGNORECASE,
        )
        if absolute_match:
            description = absolute_match.group("desc").strip(" .")
            parsed_time = self._parse_absolute_time(body)
            if description and parsed_time:
                return ReminderRequest(description=description, scheduled_time=parsed_time)
            return None

        return None

    def _parse_absolute_time(self, expression: str) -> Optional[datetime]:
        expr = expression.lower().strip()
        now = datetime.now()
        is_tomorrow = " tomorrow " in f" {expr} "

        match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", expr)
        if not match:
            return None

        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        ampm = match.group(3)

        if minute > 59:
            return None

        if ampm:
            if hour < 1 or hour > 12:
                return None
            if ampm == "pm" and hour != 12:
                hour += 12
            if ampm == "am" and hour == 12:
                hour = 0
        else:
            if hour > 23:
                return None

        scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if is_tomorrow:
            scheduled = scheduled + timedelta(days=1)
        elif scheduled <= now:
            scheduled = scheduled + timedelta(days=1)

        return scheduled

    def list_tasks(self, user_id: str) -> Dict[str, Any]:
        tasks = self.scheduler.get_user_tasks(user_id)
        pending_tasks = [task for task in tasks if task.get("status") == "pending"]
        return task_list_message(pending_tasks)

    def cancel_task(self, task_id: int, user_id: str) -> Dict[str, Any]:
        cancelled = self.scheduler.cancel_task(task_id, user_id)
        return task_cancel_message(task_id, cancelled)

    async def create_task(
        self,
        *,
        user_id: str,
        channel_id: str,
        text: str,
        thread_ts: Optional[str],
    ) -> Dict[str, Any]:
        parsed = self.parse_create_command(text)
        if not parsed:
            return reminder_parse_error_message()

        task_id = await self.scheduler.schedule_task(
            user_id=user_id,
            channel_id=channel_id,
            description=parsed.description,
            scheduled_time=parsed.scheduled_time,
            cron_expression=parsed.cron_expression,
            thread_ts=thread_ts,
        )

        return reminder_created_message(
            task_id=task_id,
            description=parsed.description,
            scheduled_time=parsed.scheduled_time,
            cron_expression=parsed.cron_expression,
        )


def visible_task_count(tasks: List[Dict[str, Any]]) -> int:
    return len([task for task in tasks if task.get("status") == "pending"])
