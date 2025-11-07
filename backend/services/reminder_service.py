"""
Reminder Service - Email + WhatsApp task deadline reminders
Enhanced reliability, duplicate-job protection, and stronger datetime handling
"""

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
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

try:
    from services.whatsapp_service import WhatsAppService
except Exception:
    WhatsAppService = None

mail = Mail()
_scheduler: Optional[BackgroundScheduler] = None


# ---------- Util: Logger ----------
def _log(message: str, level: str = "info"):
    app = current_app if current_app else None
    if app and hasattr(app, "logger"):
        log_fn = getattr(app.logger, level, app.logger.info)
        log_fn(message)
    else:
        print(message)


# ---------- Date Parsing ----------
def _parse_deadline(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        dt = date_parser.parse(str(value)) if date_parser else datetime.fromisoformat(str(value))
        if dt.tzinfo:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _format_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return "No deadline"
    return dt.strftime("%d-%m-%Y %I:%M %p")


def _job_id(task_id: Union[int, str]):
    return f"remind_task_{task_id}"


# ---------- Notification Senders ----------
def _send_email(to: str, subject: str, body: str):
    if not to:
        return
    with current_app.app_context():
        try:
            suppress = current_app.config.get("MAIL_SUPPRESS_SEND", False)
            msg = Message(subject=subject,
                          sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
                          recipients=[to],
                          body=body)
            if not suppress:
                mail.send(msg)
            _log(f"[ReminderEmail] {'(suppressed) ' if suppress else ''}Sent to {to}")
        except Exception as e:
            _log(f"[ReminderEmail] Failed: {e}", "error")


def _send_whatsapp(to: Optional[str], text: str):
    if not to or not WhatsAppService:
        _log("[ReminderWhatsApp] Skipped — no valid number or service missing", "warning")
        return
    try:
        sid = WhatsAppService().send_message(to, text)
        _log(f"[ReminderWhatsApp] Sent SID={sid} → {to}")
    except Exception as e:
        _log(f"[ReminderWhatsApp] Error: {e}", "error")


# ---------- Scheduled Job ----------
def _reminder_job(user_email, user_whatsapp, title, deadline_str):
    _send_email(user_email,
                subject=f"⏰ Task Reminder: {title}",
                body=f"Reminder: '{title}' is due at {deadline_str}.")
    _send_whatsapp(user_whatsapp,
                   f"⏰ *Task Reminder*\n\n*Title:* {title}\n*Due:* {deadline_str}")


# ---------- Scheduler Manager ----------
def _schedule_common(task_id, title, deadline_val, user_email, user_whatsapp):
    if not task_id:
        _log("[Scheduler] Missing task_id; cannot schedule", "warning")
        return

    dt = _parse_deadline(deadline_val)
    if not dt:
        _log(f"[Scheduler] Invalid deadline for task {task_id} — skipping", "warning")
        return

    reminder_time = dt - timedelta(minutes=30)
    if reminder_time <= datetime.now():
        _log(f"[Scheduler] Reminder already passed for task {task_id} — skipping", "warning")
        return

    job_id = _job_id(task_id)

    # ✅ Prevent duplicate reminders after task update
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        pass

    _scheduler.add_job(
        func=_reminder_job,
        trigger="date",
        run_date=reminder_time,
        args=[user_email, user_whatsapp, title, _format_dt(dt)],
        id=job_id,
        replace_existing=True,
    )

    _log(f"[Scheduler] Reminder set for task {task_id} at {reminder_time} (job={job_id})")


def schedule_task_reminder(app, task_dict: dict):
    with app.app_context():
        _schedule_common(
            task_id=task_dict.get("id"),
            title=task_dict.get("title", "Untitled Task"),
            deadline_val=task_dict.get("deadline"),
            user_email=task_dict.get("user_email"),
            user_whatsapp=task_dict.get("user_whatsapp"),
        )


def schedule_task_reminder_from_model(app, task_obj, user_obj):
    with app.app_context():
        _schedule_common(
            task_id=getattr(task_obj, "id"),
            title=getattr(task_obj, "title"),
            deadline_val=getattr(task_obj, "deadline"),
            user_email=getattr(user_obj, "email"),
            user_whatsapp=getattr(user_obj, "whatsapp_number"),
        )


def remove_task_reminder(task_id):
    if not _scheduler:
        return
    try:
        _scheduler.remove_job(_job_id(task_id))
        _log(f"[Scheduler] Removed job for task {task_id}")
    except Exception:
        pass


def start_scheduler(app):
    global _scheduler
    try:
        mail.init_app(app)
    except Exception as e:
        _log(f"[Scheduler] Mail init fail: {e}", "error")

    if _scheduler and _scheduler.running:
        _log("[Scheduler] Already running — skipping init")
        return

    _scheduler = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        executors={"default": ThreadPoolExecutor(10)},
        job_defaults={"coalesce": True, "max_instances": 2, "misfire_grace_time": 300},
        timezone=app.config.get("APSCHEDULER_TIMEZONE", "Asia/Kolkata"),
    )
    _scheduler.start()
    _log("[Scheduler] ✅ Started")

    atexit.register(lambda: _scheduler.shutdown(wait=False))
