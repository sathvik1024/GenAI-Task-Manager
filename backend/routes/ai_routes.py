"""
AI-powered routes for task parsing, prioritization, summary generation, and subtask suggestions.
Mounted at /api/ai from app.py
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from dateutil import parser as date_parser  # robust parsing

from models_mongo import Task, User
from services.ai_service import AIService
from services.email_service import EmailService
from services.whatsapp_service import WhatsAppService
from services.reminder_service import mail, schedule_task_reminder  # signature: (app, payload)

# Blueprint (no prefix here; app.py mounts it at /api/ai)
ai_bp = Blueprint("ai", __name__)


# ---------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------
_DEF_TIME_H = 23
_DEF_TIME_M = 59


def _strip_ordinals(text: str) -> str:
    """turn '30th' -> '30' etc."""
    return re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.I)


def _normalize_deadline_for_input(raw: Optional[str]) -> Optional[str]:
    """
    Convert human/ISO to 'YYYY-MM-DDTHH:MM' for <input type="datetime-local">.
    If only a date was present, default to 23:59.
    """
    if not raw:
        return None
    s = _strip_ordinals(str(raw).strip())
    time_mentioned = bool(re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", s, re.I))

    for dayfirst in (True, False):
        try:
            dt = date_parser.parse(s, dayfirst=dayfirst, fuzzy=True)
            if dt.tzinfo:
                dt = dt.astimezone(tz=None).replace(tzinfo=None)
            if not time_mentioned:
                dt = dt.replace(hour=_DEF_TIME_H, minute=_DEF_TIME_M, second=0, microsecond=0)
            return dt.strftime("%Y-%m-%dT%H:%M")
        except Exception:
            continue
    return None


def _parse_deadline_for_storage(raw: Optional[str]) -> Optional[datetime]:
    """
    Parse human/ISO to a naive local datetime for DB storage.
    Defaults to 23:59 when only a date is supplied.
    """
    if not raw:
        return None
    s = _strip_ordinals(str(raw).strip())
    time_mentioned = bool(re.search(r"\d{1,2}:\d{2}|\b(am|pm)\b", s, re.I))

    for dayfirst in (True, False):
        try:
            dt = date_parser.parse(s, dayfirst=dayfirst, fuzzy=True)
            if dt.tzinfo:
                dt = dt.astimezone(tz=None).replace(tzinfo=None)
            if not time_mentioned:
                dt = dt.replace(hour=_DEF_TIME_H, minute=_DEF_TIME_M, second=0, microsecond=0)
            return dt
        except Exception:
            continue
    return None


def _ascii_only(s: str) -> bool:
    """True if the string is ASCII (rough heuristic for 'English-friendly')."""
    try:
        s.encode("ascii")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@ai_bp.route("/parse-task", methods=["POST"])
@jwt_required()
def parse_natural_language_task():
    """
    Parse a natural language task using AIService and return fields ready for the form.
    - Ensures deadline is formatted for <input type="datetime-local">
    - Makes the title English-friendly when possible (uses title_en fallback)
    """
    try:
        _ = get_jwt_identity()
        data = request.get_json() or {}
        user_input = (data.get("input") or "").strip()
        if not user_input:
            return jsonify({"error": "Input text is required"}), 400

        parsed = AIService.parse_natural_language_task(user_input)

        # If the model returned a non-ASCII title, fall back to 'title_en' (AIService guarantees it)
        if not _ascii_only(parsed.get("title", "")):
            title_en = parsed.get("title_en") or parsed.get("title") or ""
            parsed["title"] = title_en[:60] if title_en else "Task"

        # Convert deadline to input-friendly value (or derive it from the text)
        parsed["deadline"] = _normalize_deadline_for_input(
            parsed.get("deadline") or user_input
        )

        return jsonify({"message": "Task parsed successfully", "parsed_task": parsed}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to parse task: {str(e)}"}), 500


@ai_bp.route("/create-from-text", methods=["POST"])
@jwt_required()
def create_task_from_text():
    """
    Parse natural language text and create a Task immediately.
    Also triggers email + WhatsApp (if configured) + schedules reminder.
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        user_input = (data.get("input") or "").strip()
        if not user_input:
            return jsonify({"error": "Input text is required"}), 400

        parsed = AIService.parse_natural_language_task(user_input)

        title = parsed.get("title") or parsed.get("title_en") or user_input[:60] or "Task"
        # English-friendly fallback
        if not _ascii_only(title):
            title = (parsed.get("title_en") or "Task")[:60]

        priority = (parsed.get("priority") or "medium").lower()
        category = parsed.get("category") or "general"
        description = parsed.get("description") or user_input
        deadline = _parse_deadline_for_storage(parsed.get("deadline") or user_input)

        task = Task(
            title=title,
            description=description,
            deadline=deadline,
            priority=priority,
            category=category,
            status="pending",
            user_id=user_id,
            ai_generated=bool(parsed.get("ai_generated")),
        )

        if parsed.get("subtasks"):
            task.set_subtasks(parsed["subtasks"])

        task.save()

        user = User.find_by_id(user_id)

        # Schedule reminder (30-min-before handled inside your reminder_service)
        try:
            reminder_payload = {
                "id": task.id,
                "title": task.title,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "user_email": user.email if user else None,
                "user_whatsapp": getattr(user, "whatsapp_number", None) if user else None,
            }
            schedule_task_reminder(current_app, reminder_payload)
        except Exception as sched_err:
            print(f"[AI Routes] Failed to schedule reminder: {sched_err}")

        # Email
        try:
            if user and user.email:
                EmailService.send_task_created_notification(mail, user.email, task.to_dict())
        except Exception as email_error:
            print(f"[AI Routes] Email failed: {email_error}")

        # WhatsApp (best-effort; your service returns SID or None)
        try:
            wa_number = getattr(user, "whatsapp_number", "") if user else ""
            if wa_number:
                wa = WhatsAppService()
                sid = wa.send_message(
                    wa_number,
                    (
                        "✅ *New Task Created!*\n\n"
                        f"*Title:* {task.title}\n"
                        f"*Category:* {str(task.category).capitalize()}\n"
                        f"*Priority:* {str(task.priority).capitalize()}\n"
                        f"*Deadline:* {task.deadline.strftime('%d-%m-%Y %I:%M %p') if task.deadline else 'No deadline'}\n\n"
                        "🧠 I'll remind you before the deadline!"
                    )
                )
                if sid:
                    print(f"[AI Routes] WhatsApp message sent. SID={sid}")
                else:
                    print("[AI Routes] WhatsApp send returned None (check Twilio logs/credentials).")
        except Exception as wa_error:
            print(f"[AI Routes] WhatsApp unexpected error: {wa_error}")

        return jsonify({
            "message": "Task created successfully from AI parsing",
            "task": task.to_dict(),
            "original_input": user_input
        }), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create task from text: {str(e)}"}), 500


@ai_bp.route("/prioritize-tasks", methods=["POST"])
@jwt_required()
def prioritize_user_tasks():
    """Use AI to intelligently prioritize user's tasks."""
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}

        if data.get("task_ids"):
            all_user_tasks = Task.find_by_user_id(user_id)
            target_ids = set(data["task_ids"])
            tasks = [t for t in all_user_tasks if t.id in target_ids and t.status != "completed"]
        else:
            tasks = [t for t in Task.find_by_user_id(user_id) if t.status != "completed"]

        if not tasks:
            return jsonify({"message": "No tasks to prioritize", "prioritized_tasks": []}), 200

        prioritized_tasks = AIService.prioritize_tasks([t.to_dict() for t in tasks])

        return jsonify({
            "message": "Tasks prioritized successfully",
            "prioritized_tasks": prioritized_tasks,
            "count": len(prioritized_tasks)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to prioritize tasks: {str(e)}"}), 500


@ai_bp.route("/generate-summary", methods=["GET"])
@jwt_required()
def generate_task_summary():
    """Generate AI-powered summary of user's tasks."""
    try:
        user_id = int(get_jwt_identity())
        period = request.args.get("period", "daily")
        if period not in ["daily", "weekly"]:
            return jsonify({"error": "Period must be daily or weekly"}), 400

        tasks = Task.find_by_user_id(user_id)
        summary = AIService.generate_summary([t.to_dict() for t in tasks], period)

        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == "completed"])
        pending_tasks = len([t for t in tasks if t.status in ["pending", "in_progress"]])

        return jsonify({
            "summary": summary,
            "period": period,
            "stats": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": pending_tasks
            },
            "generated_at": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500


@ai_bp.route("/suggest-subtasks", methods=["POST"])
@jwt_required()
def suggest_subtasks():
    """Generate AI suggestions for subtasks based on a task title/description."""
    try:
        data = request.get_json() or {}

        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Task title is required"}), 400

        description = (data.get("description") or "").strip()

        # Use the dedicated AIService method (has OpenAI + fallback)
        res = AIService.suggest_subtasks(title, description)

        return jsonify({
            "suggested_subtasks": res.get("suggested_subtasks", []),
            "suggested_category": res.get("suggested_category", "general"),
            "suggested_priority": res.get("suggested_priority", "medium")
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to suggest subtasks: {str(e)}"}), 500


@ai_bp.route("/health", methods=["GET"])
def ai_health_check():
    """Check if AI service is available and configured."""
    try:
        api_key_configured = bool(os.getenv("OPENAI_API_KEY"))
        return jsonify({
            "ai_service_available": True,
            "openai_api_configured": api_key_configured,
            "status": "healthy" if api_key_configured else "missing_api_key"
        }), 200
    except Exception as e:
        return jsonify({
            "ai_service_available": False,
            "error": str(e),
            "status": "unhealthy"
        }), 500
