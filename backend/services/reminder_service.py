# services/reminder_service.py

import os
import atexit
from datetime import datetime, timedelta
from typing import Optional, Union

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from flask_mail import Mail, Message
from flask import current_app

try:
    # Flexible parsing for ISO and human-readable strings
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

# Optional WhatsApp integration (Twilio wrapper)
try:
    from services.whatsapp_service import WhatsAppService
except Exception:
    WhatsAppService = None  # OK if not configured

# ---------- Globals ----------
mail = Mail()
_scheduler: Optional[BackgroundScheduler] = None

# ---------- Utilities ----------
def _parse_deadline(value: Union[str, datetime, None]) -> Optional[datetime]:
    """Return a timezone-naive datetime in local server time, or None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value)
    if date_parser:
        try:
            return date_parser.parse(s)
        except Exception:
            return None
    try:
        if "T" in s or s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return None
    except Exception:
        return None


def _format_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return "No deadline"
    return dt.strftime("%d-%m-%Y %I:%M %p")


def _job_id_for_task(task_id: Union[int, str]) -> str:
    return f"reminder_task_{task_id}"


# ---------- Logging Helper ----------
def _log(app, message: str, level: str = "info"):
    """Safe logging utility that supports app.logger or print fallback."""
    if hasattr(app, "logger"):
        logger = app.logger
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    else:
        print(message)


# ---------- Email sender ----------
def _send_email(app, subject: str, recipient: str, body: str):
    """Send an email within the app context; tolerate dev SUPPRESS_SEND."""
    if not recipient:
        return
    with app.app_context():
        try:
            suppress = app.config.get("MAIL_SUPPRESS_SEND", False)
            msg = Message(
                subject=subject,
                sender=os.getenv("MAIL_DEFAULT_SENDER") or app.config.get("MAIL_DEFAULT_SENDER"),
                recipients=[recipient],
                body=body,
            )
            if not suppress:
                mail.send(msg)
            _log(app, f"[ReminderEmail] {'(suppressed) ' if suppress else ''}Sent to {recipient}: {subject}")
        except Exception as e:
            _log(app, f"[ReminderEmail] Failed: {e}", level="error")


# ---------- WhatsApp sender (optional) ----------
def _send_whatsapp(app, to_number: Optional[str], message: str):
    if not to_number or not WhatsAppService:
        return
    try:
        wa = WhatsAppService()
        wa.send_message(to_number, message)
        _log(app, f"[ReminderWhatsApp] Sent to {to_number}")
    except Exception as e:
        _log(app, f"[ReminderWhatsApp] Failed: {e}", level="error")


# ---------- Reminder job (called by scheduler) ----------
def _reminder_job(app, user_email: Optional[str], user_whatsapp: Optional[str], task_title: str, deadline_str: str):
    """A single reminder job that can notify over Email and WhatsApp."""
    _send_email(
        app,
        subject=f"⏰ Task Reminder: {task_title}",
        recipient=user_email or "",
        body=f"Reminder: Your task '{task_title}' is due at {deadline_str}.",
    )
    _send_whatsapp(
        app,
        user_whatsapp,
        f"⏰ *Task Reminder*\n\n*Title:* {task_title}\n*Due:* {deadline_str}"
    )


# ---------- Public API ----------
def schedule_task_reminder_from_model(app, task_obj, user_obj):
    """
    Schedule a reminder (email + WhatsApp) 30 minutes before the task deadline.
    Works directly with your Task/User models.
    """
    task_id = getattr(task_obj, "id", None)
    title = getattr(task_obj, "title", "Untitled Task")
    deadline_val = getattr(task_obj, "deadline", None)
    user_email = getattr(user_obj, "email", None)
    user_whatsapp = getattr(user_obj, "whatsapp_number", None)

    if not task_id:
        _log(app, "[Scheduler] Missing task_id; cannot schedule.", level="warning")
        return

    deadline_dt = _parse_deadline(deadline_val)
    if not deadline_dt:
        _log(app, f"[Scheduler] No/invalid deadline for task {task_id}; skipping.", level="warning")
        return
    reminder_time = deadline_dt - timedelta(minutes=30)
    if reminder_time <= datetime.now():
        _log(app, f"[Scheduler] Reminder time already passed for task {task_id}; skipping.", level="warning")
        return

    job_id = _job_id_for_task(task_id)

    try:
        _scheduler.add_job(
            func=_reminder_job,
            trigger="date",
            run_date=reminder_time,
            args=[app, user_email, user_whatsapp, title, _format_dt(deadline_dt)],
            id=job_id,
            replace_existing=True,
        )
        _log(app, f"[Scheduler] Reminder scheduled @ {reminder_time} for task {task_id} (job={job_id})")
    except Exception as e:
        _log(app, f"[Scheduler] Failed to add job for task {task_id}: {e}", level="error")


def schedule_task_reminder(app, task_dict: dict):
    """
    Backwards-compatible: schedule using a plain dict like:
    {
        'id': 12,
        'title': 'X',
        'deadline': '2025-08-22 21:00',
        'user_email': 'a@b.com',
        'user_whatsapp': '+91...'(optional)
    }
    """
    task_id = task_dict.get("id") or task_dict.get("_id")
    title = task_dict.get("title", "Untitled Task")
    deadline_val = task_dict.get("deadline")
    user_email = task_dict.get("user_email")
    user_whatsapp = task_dict.get("user_whatsapp")

    if not task_id:
        _log(app, "[Scheduler] Missing task_id; cannot schedule.", level="warning")
        return

    deadline_dt = _parse_deadline(deadline_val)
    if not deadline_dt:
        _log(app, f"[Scheduler] No/invalid deadline for task {task_id}; skipping.", level="warning")
        return

    reminder_time = deadline_dt - timedelta(minutes=30)
    if reminder_time <= datetime.now():
        _log(app, f"[Scheduler] Reminder time already passed for task {task_id}; skipping.", level="warning")
        return

    job_id = _job_id_for_task(task_id)

    try:
        _scheduler.add_job(
            func=_reminder_job,
            trigger="date",
            run_date=reminder_time,
            args=[app, user_email, user_whatsapp, title, _format_dt(deadline_dt)],
            id=job_id,
            replace_existing=True,
        )
        _log(app, f"[Scheduler] Reminder scheduled @ {reminder_time} for task {task_id} (job={job_id})")
    except Exception as e:
        _log(app, f"[Scheduler] Failed to add job for task {task_id}: {e}", level="error")


def remove_task_reminder(task_id: Union[int, str]):
    """Remove a scheduled reminder for a task (if any)."""
    if not _scheduler:
        return
    job_id = _job_id_for_task(task_id)
    try:
        _scheduler.remove_job(job_id)
        print(f"[Scheduler] Removed job {job_id}")
    except Exception:
        pass


def start_scheduler(app):
    """
    Initialize Flask-Mail and start the background scheduler.
    Safe to call multiple times; only the first call starts the scheduler.
    """
    global _scheduler

    try:
        mail.init_app(app)
    except Exception as e:
        _log(app, f"[Scheduler] Mail init failed: {e}", level="error")

    if _scheduler and _scheduler.running:
        _log(app, "[Scheduler] Already running; skip re-init.")
        return

    jobstores = {"default": MemoryJobStore()}
    executors = {"default": ThreadPoolExecutor(10)}
    job_defaults = {
        "coalesce": True,
        "max_instances": 2,
        "misfire_grace_time": 300,
    }

    timezone = app.config.get("APSCHEDULER_TIMEZONE", os.getenv("APSCHEDULER_TIMEZONE", "Asia/Kolkata"))

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=timezone,
    )
    _scheduler.start()
    _log(app, f"[Scheduler] Started with timezone={timezone}")

    atexit.register(lambda: _scheduler.shutdown(wait=False))
