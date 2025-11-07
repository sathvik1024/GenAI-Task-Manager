"""
Task management routes - CRUD + stats + reminders + notifications
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from dateutil import parser as date_parser
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from models_mongo import Task, User
from services.email_service import EmailService
from services.reminder_service import schedule_task_reminder, mail
from services.whatsapp_service import WhatsAppService

task_bp = Blueprint("tasks", __name__)


# -----------------------------
# Helpers
# -----------------------------
def _parse_deadline(value) -> Optional[datetime]:
    """Parse various deadline formats to a naive datetime (server local time)."""
    if not value:
        return None
    try:
        dt = date_parser.isoparse(str(value))
    except Exception:
        try:
            dt = date_parser.parse(str(value), dayfirst=True, fuzzy=True)
        except Exception:
            return None
    # make naive (scheduler uses naive, server-local)
    if dt.tzinfo:
        dt = dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


def _sort_deadline_first(task: Task):
    """Sort key: incomplete before completed, then nearest deadline first, then created_at desc."""
    # completed last
    is_completed = 1 if getattr(task, "status", "") == "completed" else 0

    # deadline (None goes to the end)
    d = getattr(task, "deadline", None)
    if isinstance(d, str):
        d = _parse_deadline(d)
    deadline_key = d or datetime.max

    # created_at (most recent first) -> negative timestamp
    ca = getattr(task, "created_at", None)
    if isinstance(ca, str):
        try:
            ca = date_parser.isoparse(ca)
        except Exception:
            ca = None
    created_key = -(ca.timestamp()) if isinstance(ca, datetime) else 0

    return (is_completed, deadline_key, created_key)


# -----------------------------
# Routes
# -----------------------------

# Support both "/tasks" and "/tasks/" to avoid 308 redirects
@task_bp.route("", methods=["GET"])
@task_bp.route("/", methods=["GET"])
@jwt_required()
def get_tasks():
    try:
        user_id = int(get_jwt_identity())
        filters = {
            k: request.args.get(k)
            for k in ("status", "priority", "category", "search")
            if request.args.get(k)
        }

        tasks = Task.find_by_user_id(user_id, filters)

        # Pending first, nearest deadline first
        tasks.sort(key=_sort_deadline_first)

        return jsonify(
            {
                "tasks": [t.to_dict() for t in tasks],
                "count": len(tasks),
            }
        ), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get tasks: {str(e)}"}), 500


@task_bp.route("", methods=["POST"])
@task_bp.route("/", methods=["POST"])
@jwt_required()
def create_task():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}

        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Title is required"}), 400

        deadline = _parse_deadline(data.get("deadline"))

        task = Task(
            title=title,
            description=(data.get("description") or "").strip(),
            deadline=deadline,
            priority=(data.get("priority") or "medium").lower(),
            category=(data.get("category") or "general").strip(),
            status="pending",
            user_id=user_id,
            ai_generated=bool(data.get("ai_generated", False)),
        )

        if data.get("subtasks"):
            task.set_subtasks(data["subtasks"])

        task.save()

        user = User.find_by_id(user_id)
        task_dict = task.to_dict()

        # Convenience for scheduler/notifiers
        if user:
            if getattr(user, "email", None):
                task_dict["user_email"] = user.email
            if getattr(user, "whatsapp_number", None):
                task_dict["user_whatsapp"] = user.whatsapp_number

        # Reminder 30-min before deadline
        try:
            schedule_task_reminder(current_app, task_dict)
        except Exception as sched_err:
            print(f"[Scheduler] Failed to schedule: {sched_err}")

        # Email notification (best-effort)
        try:
            if user and user.email:
                EmailService.send_task_created_notification(mail, user.email, task_dict)
        except Exception as email_err:
            print(f"[Email] Failed: {email_err}")

        # WhatsApp notification (best-effort)
        try:
            wa_number = getattr(user, "whatsapp_number", None) if user else None
            if wa_number and wa_number.startswith("+") and len(wa_number) >= 10:
                msg = (
                    "✅ *New Task Created!*\n\n"
                    f"*Title:* {task.title}\n"
                    f"*Category:* {str(task.category or 'general').capitalize()}\n"
                    f"*Priority:* {str(task.priority or 'medium').capitalize()}\n"
                    f"*Deadline:* "
                    f"{task.deadline.strftime('%d-%m-%Y %I:%M %p') if task.deadline else 'No deadline'}\n\n"
                    "🧠 I'll remind you before the deadline!"
                )
                WhatsAppService().send_message(wa_number, msg)
            else:
                print("[WhatsApp] Skipped (no valid number)")
        except Exception as wa_err:
            print(f"[WhatsApp] Failed: {wa_err}")

        return jsonify({"message": "Task created successfully", "task": task_dict}), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create task: {str(e)}"}), 500


@task_bp.route("/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id: int):
    try:
        user_id = int(get_jwt_identity())
        task = Task.find_by_id(task_id)

        if not task or task.user_id != user_id:
            return jsonify({"error": "Task not found"}), 404

        return jsonify({"task": task.to_dict()}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get task: {str(e)}"}), 500


@task_bp.route("/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id: int):
    try:
        user_id = int(get_jwt_identity())
        task = Task.find_by_id(task_id)
        if not task or task.user_id != user_id:
            return jsonify({"error": "Task not found"}), 404

        data = request.get_json() or {}

        # Track original deadline to decide on rescheduling
        original_deadline = task.deadline

        for key in ["title", "description", "priority", "category", "status"]:
            if key in data:
                setattr(task, key, (data.get(key) or "").strip())

        if "deadline" in data:
            parsed = _parse_deadline(data.get("deadline"))
            task.deadline = parsed

        if "subtasks" in data:
            task.set_subtasks(data["subtasks"])

        task.updated_at = datetime.utcnow()
        task.save()

        # If deadline changed, try scheduling again
        if (original_deadline or task.deadline) and original_deadline != task.deadline:
            try:
                user = User.find_by_id(user_id)
                task_dict = task.to_dict()
                if user and user.email:
                    task_dict["user_email"] = user.email
                if user and getattr(user, "whatsapp_number", None):
                    task_dict["user_whatsapp"] = user.whatsapp_number
                schedule_task_reminder(current_app, task_dict)
            except Exception as sched_err:
                print(f"[Scheduler] Reschedule failed: {sched_err}")

        return jsonify({"message": "Task updated successfully", "task": task.to_dict()}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to update task: {str(e)}"}), 500


@task_bp.route("/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id: int):
    try:
        user_id = int(get_jwt_identity())
        task = Task.find_by_id(task_id)
        if not task or task.user_id != user_id:
            return jsonify({"error": "Task not found"}), 404

        task.delete()
        return jsonify({"message": "Task deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete task: {str(e)}"}), 500


@task_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_task_stats():
    try:
        user_id = int(get_jwt_identity())
        all_tasks = Task.find_by_user_id(user_id)
        stats = Task.get_user_stats(user_id)
        now = datetime.utcnow()

        # Overdue counts (exclude completed)
        overdue = 0
        for t in all_tasks:
            d = getattr(t, "deadline", None)
            if isinstance(d, str):
                d = _parse_deadline(d)
            if d and isinstance(d, datetime) and d < now and getattr(t, "status", "") != "completed":
                overdue += 1

        urgent = sum(1 for t in all_tasks if getattr(t, "priority", "") == "urgent")
        high = sum(1 for t in all_tasks if getattr(t, "priority", "") == "high")

        return jsonify(
            {
                **stats,
                "urgent_tasks": urgent,
                "high_priority_tasks": high,
                "overdue_tasks": overdue,
            }
        ), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500
