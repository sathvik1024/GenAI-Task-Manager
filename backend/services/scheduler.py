# services/scheduler.py
"""
Task reminder scheduler helper.
Handles automated reminders for upcoming task deadlines by delegating
actual scheduling and sending to services.reminder_service.

Why this design?
- We keep a SINGLE BackgroundScheduler in the app (started in reminder_service.start_scheduler(app)).
- This file only scans tasks and asks reminder_service to (re)schedule jobs.
- Prevents duplicate schedulers and undefined calls to EmailService.
"""

from datetime import datetime, timedelta
from flask import current_app

from models_mongo import Task, User

# Reuse the single scheduler and helper functions from reminder_service
from services.reminder_service import (
    schedule_task_reminder_from_model,  # schedules a reminder for a Task+User
    remove_task_reminder,               # removes a reminder job by task_id
)

class TaskScheduler:
    """
    Lightweight wrapper that:
      - scans for upcoming deadlines and (re)schedules reminders
      - exposes a simple status summary

    NOTE: This class does NOT create or start another BackgroundScheduler.
    The only scheduler is started in services.reminder_service.start_scheduler(app).
    """

    def __init__(self):
        # No local BackgroundScheduler here — rely on reminder_service’s scheduler
        pass

    # ------------------------------------------------------------------
    # 🔍 SCAN & (RE)SCHEDULE UPCOMING DEADLINES
    # ------------------------------------------------------------------
    def check_upcoming_deadlines(self):
        """
        Finds tasks due within the next 24 hours (not completed) and ensures
        a reminder is scheduled 30 minutes before their deadline.
        Safe to run periodically (e.g., hourly via a cron or manual trigger).
        """
        try:
            now = datetime.utcnow()
            next_24h = now + timedelta(hours=24)

            all_tasks = Task.find_all() if hasattr(Task, "find_all") else []
            upcoming = [
                t for t in all_tasks
                if t.deadline
                and isinstance(t.deadline, datetime)
                and now < t.deadline <= next_24h
                and t.status != "completed"
            ]

            print(f"[Scheduler] Found {len(upcoming)} tasks due within 24h.")

            for task in upcoming:
                user = User.find_by_id(task.user_id)
                if not user:
                    continue
                # (Re-)schedule using the shared scheduler in reminder_service
                schedule_task_reminder_from_model(current_app, task, user)

        except Exception as e:
            print(f"[Scheduler] Error while scanning deadlines: {e}")

    # ------------------------------------------------------------------
    # 🧹 REMOVE REMINDERS FOR A TASK
    # ------------------------------------------------------------------
    def remove_task_reminders(self, task_id):
        """Remove the scheduled reminder for this task (if any)."""
        try:
            remove_task_reminder(task_id)
            print(f"[Scheduler] Removed reminder for task {task_id}")
        except Exception:
            # Job may not exist; ignore
            pass

    # ------------------------------------------------------------------
    # 📊 STATUS SUMMARY
    # ------------------------------------------------------------------
    def get_scheduler_status(self):
        """
        Returns a lightweight status summary derived from tasks & deadlines.
        We don’t expose the internal scheduler instance here.
        """
        try:
            upcoming_count = 0
            now = datetime.utcnow()
            next_24h = now + timedelta(hours=24)
            all_tasks = Task.find_all() if hasattr(Task, "find_all") else []
            for t in all_tasks:
                if (
                    t.deadline and isinstance(t.deadline, datetime)
                    and now < t.deadline <= next_24h
                    and t.status != "completed"
                ):
                    upcoming_count += 1

            return {
                "running": True,                      # the real scheduler lives in reminder_service
                "jobs_count_hint": upcoming_count,    # hint based on tasks due soon
                "note": "Jobs are managed by services.reminder_service",
            }
        except Exception as e:
            return {
                "running": False,
                "jobs_count_hint": 0,
                "error": str(e),
            }

# Global instance (as expected by your app)
task_scheduler = TaskScheduler()
