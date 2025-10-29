"""
Task management routes for CRUD operations.
Handles creating, reading, updating, and deleting tasks.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from dateutil import parser as date_parser  # robust ISO parsing

from models_mongo import Task, User
from services.email_service import EmailService
from services.reminder_service import schedule_task_reminder, mail
from services.whatsapp_service import WhatsAppService  # ✅ Required for WhatsApp


task_bp = Blueprint("tasks", __name__)


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

        return jsonify({
            "tasks": [t.to_dict() for t in tasks],
            "count": len(tasks)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get tasks: {str(e)}"}), 500


@task_bp.route("/", methods=["POST"])
@jwt_required()
def create_task():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}

        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Title is required"}), 400

        # ✅ Safe deadline parsing
        deadline = None
        if data.get("deadline"):
            try:
                dt = date_parser.isoparse(str(data["deadline"]))
                if dt.tzinfo:
                    dt = dt.astimezone(tz=None).replace(tzinfo=None)
                deadline = dt
            except Exception:
                return jsonify({"error": "Invalid deadline format"}), 400

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

        # ✅ Attach user email for scheduler convenience
        if user and user.email:
            task_dict["user_email"] = user.email

        # ✅ 30-min reminder scheduling
        try:
            schedule_task_reminder(current_app, task_dict)
        except Exception as sched_err:
            print(f"[Scheduler] Failed to schedule: {sched_err}")

        # ✅ Send email
        try:
            if user and user.email:
                EmailService.send_task_created_notification(mail, user.email, task_dict)
        except Exception as email_err:
            print(f"[Email] Failed: {email_err}")

        # ✅ NEW: WhatsApp send when task is created
        try:
            wa_number = getattr(user, "whatsapp_number", "") if user else ""
            if wa_number and wa_number.startswith("+") and len(wa_number) >= 10:
                wa = WhatsAppService()
                wa.send_message(
                    wa_number,
                    (
                        "✅ *New Task Created!*\n\n"
                        f"*Title:* {task.title}\n"
                        f"*Category:* {task.category.capitalize()}\n"
                        f"*Priority:* {task.priority.capitalize()}\n"
                        f"*Deadline:* {task.deadline.strftime('%d-%m-%Y %I:%M %p') if task.deadline else 'No deadline'}\n\n"
                        "🧠 I'll remind you before the deadline!"
                    )
                )
            else:
                print("[WhatsApp] Skipped (user has no valid WhatsApp number)")
        except Exception as wa_err:
            print(f"[WhatsApp] Failed: {wa_err}")

        return jsonify({
            "message": "Task created successfully",
            "task": task.to_dict()
        }), 201

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

        for key in ["title", "description", "priority", "category", "status"]:
            if key in data:
                val = (data.get(key) or "").strip()
                setattr(task, key, val)

        if "deadline" in data:
            try:
                dt = date_parser.isoparse(str(data["deadline"]))
                if dt.tzinfo:
                    dt = dt.astimezone(tz=None).replace(tzinfo=None)
                task.deadline = dt
            except Exception:
                return jsonify({"error": "Invalid deadline format"}), 400

        if "subtasks" in data:
            task.set_subtasks(data["subtasks"])

        task.updated_at = datetime.utcnow()
        task.save()

        return jsonify({
            "message": "Task updated successfully",
            "task": task.to_dict()
        }), 200

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

        overdue = sum(
            1 for t in all_tasks
            if t.deadline and isinstance(t.deadline, datetime) and t.deadline < now and t.status != "completed"
        )

        urgent_tasks = sum(1 for t in all_tasks if t.priority == "urgent")
        high_tasks = sum(1 for t in all_tasks if t.priority == "high")

        return jsonify({
            **stats,
            "urgent_tasks": urgent_tasks,
            "high_priority_tasks": high_tasks,
            "overdue_tasks": overdue,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500
