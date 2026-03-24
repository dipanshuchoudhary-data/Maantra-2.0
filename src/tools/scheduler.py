"""
Task Scheduler

Handles reminders and scheduled tasks for Slack users.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slack_sdk.web.async_client import AsyncWebClient

from src.config.settings import config
from src.memory.database import (
    cancel_task as db_cancel_task,
    create_scheduled_task,
    get_pending_tasks,
    get_user_tasks,
    update_task_status,
)
from src.utils.logger import get_logger

logger = get_logger("scheduler")

slack_client = AsyncWebClient(token=config.slack.bot_token)
scheduler = AsyncIOScheduler()
active_jobs: Dict[str, str] = {}


class TaskScheduler:

    def __init__(self):
        self.running = False

    def start(self):

        if self.running:
            logger.warning("Scheduler already running")
            return

        scheduler.start()
        scheduler.add_job(
            self.process_pending_tasks,
            "interval",
            seconds=60,
        )
        self.running = True
        logger.info("Task scheduler started")

    def stop(self):

        if not self.running:
            return

        scheduler.shutdown(wait=False)
        self.running = False
        logger.info("Task scheduler stopped")

    async def schedule_task(
        self,
        user_id: str,
        channel_id: str,
        description: str,
        scheduled_time: Optional[datetime] = None,
        cron_expression: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ):

        logger.info(f"Scheduling task for {user_id}: {description}")

        task_id = create_scheduled_task(
            user_id,
            channel_id,
            description,
            int(scheduled_time.timestamp()) if scheduled_time else None,
            cron_expression,
            thread_ts,
        )

        task = {
            "id": task_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "task_description": description,
            "cron_expression": cron_expression,
            "scheduled_time": int(scheduled_time.timestamp()) if scheduled_time else None,
        }

        if cron_expression:
            self.setup_cron_job(task)

        return task_id

    def setup_cron_job(self, task: Dict[str, object]):

        cron_expression = task.get("cron_expression")
        if not cron_expression:
            return

        job_id = f"task-{task['id']}"
        if job_id in active_jobs:
            return

        parts = str(cron_expression).split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        scheduler.add_job(
            self.execute_task,
            "cron",
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            args=[task],
            id=job_id,
        )

        active_jobs[job_id] = job_id
        logger.info(f"Cron job scheduled {job_id}")

    async def process_pending_tasks(self):

        tasks = get_pending_tasks()

        for task in tasks:
            if task.get("cron_expression"):
                continue
            await self.execute_task(task)

    async def execute_task(self, task: Dict[str, object]):

        task_id = int(task["id"])
        logger.info(f"Executing task {task_id}")

        try:
            update_task_status(task_id, "running")

            await slack_client.chat_postMessage(
                channel=str(task["channel_id"]),
                text=f"Reminder: {task['task_description']}",
                thread_ts=task.get("thread_ts"),
            )

            if task.get("cron_expression"):
                update_task_status(task_id, "pending")
            else:
                update_task_status(task_id, "completed")

        except Exception as e:
            logger.error(f"Task execution failed {task_id}: {e}")
            update_task_status(task_id, "failed")

    def get_user_tasks(self, user_id):
        return get_user_tasks(user_id)

    def cancel_task(self, task_id, user_id):

        job_id = f"task-{task_id}"
        if job_id in active_jobs:
            scheduler.remove_job(job_id)
            active_jobs.pop(job_id)

        return db_cancel_task(task_id, user_id)


task_scheduler = TaskScheduler()


def parse_relative_time(expression: str) -> Optional[datetime]:

    now = datetime.now()
    expr = expression.lower().strip()
    match = re.search(r"in (\d+) (minute|hour|day|week)s?", expr)

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "minute":
        return now + timedelta(minutes=amount)
    if unit == "hour":
        return now + timedelta(hours=amount)
    if unit == "day":
        return now + timedelta(days=amount)
    if unit == "week":
        return now + timedelta(weeks=amount)

    return None


def to_cron_expression(expression: str) -> Optional[str]:

    expr = expression.lower().strip()

    patterns = {
        "every minute": "* * * * *",
        "every hour": "0 * * * *",
        "every day": "0 9 * * *",
        "every morning": "0 9 * * *",
        "every evening": "0 18 * * *",
        "every monday": "0 9 * * 1",
        "every tuesday": "0 9 * * 2",
        "every wednesday": "0 9 * * 3",
        "every thursday": "0 9 * * 4",
        "every friday": "0 9 * * 5",
        "every saturday": "0 9 * * 6",
        "every sunday": "0 9 * * 0",
        "every weekday": "0 9 * * 1-5",
        "every weekend": "0 9 * * 0,6",
        "every week": "0 9 * * 1",
    }

    for pattern, cron in patterns.items():
        if pattern in expr:
            return cron

    return None
