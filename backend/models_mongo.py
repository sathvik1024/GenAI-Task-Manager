"""
MongoDB models for User & Task (stable & full feature).
"""
from datetime import datetime
from flask_bcrypt import Bcrypt
from bson import ObjectId
from dateutil import parser as date_parser

from database_mongo import MongoDBManager, get_next_sequence_value

bcrypt = Bcrypt()

# =====================================================
# Helpers
# =====================================================
def _parse_dt(dt):
    if isinstance(dt, datetime):
        return dt
    try:
        return date_parser.isoparse(str(dt)).replace(tzinfo=None)
    except Exception:
        return None

def _id_query(value):
    ors = []
    try:
        ors.append({"id": int(value)})
    except Exception:
        pass
    if ObjectId.is_valid(str(value)):
        ors.append({"_id": ObjectId(str(value))})
    return {"$or": ors} if ors else {"id": -1}

# =====================================================
# USER MODEL
# =====================================================
class User:
    def __init__(self, username=None, email=None, password=None, whatsapp_number=None, **kwargs):
        self.id = kwargs.get("id") or kwargs.get("_id")
        self.username = username or kwargs.get("username")
        self.email = email or kwargs.get("email")
        self.password_hash = kwargs.get("password_hash")
        self.whatsapp_number = whatsapp_number or kwargs.get("whatsapp_number")
        self.created_at = _parse_dt(kwargs.get("created_at")) or datetime.utcnow()
        self.updated_at = _parse_dt(kwargs.get("updated_at")) or datetime.utcnow()

        if password:
            self.set_password(password)

    # --- Auth ---
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    # --- Persistence ---
    def save(self):
        user_data = {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "whatsapp_number": self.whatsapp_number,
            "created_at": self.created_at,
            "updated_at": datetime.utcnow(),
        }

        if self.id:
            MongoDBManager.update_document("users", _id_query(self.id), user_data)
        else:
            self.id = get_next_sequence_value("user_id")
            user_data["id"] = self.id
            MongoDBManager.insert_document("users", user_data)

        return self

    # --- Serialization ---
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "whatsapp_number": self.whatsapp_number,
            "created_at": self.created_at.isoformat(),
        }

    # --- Lookups ---
    @staticmethod
    def find_by_username(username):
        data = MongoDBManager.find_document("users", {"username": username})
        return User(**data) if data else None

    @staticmethod
    def find_by_email(email):
        data = MongoDBManager.find_document("users", {"email": email})
        return User(**data) if data else None

    @staticmethod
    def find_by_whatsapp(number):
        data = MongoDBManager.find_document("users", {"whatsapp_number": number})
        return User(**data) if data else None

    @staticmethod
    def find_by_id(uid):
        data = MongoDBManager.find_document("users", _id_query(uid))
        return User(**data) if data else None

# =====================================================
# TASK MODEL
# =====================================================
class Task:
    def __init__(self, title=None, description=None, deadline=None,
                 priority="medium", category="general", status="pending",
                 user_id=None, ai_generated=False, **kwargs):

        self.id = kwargs.get("id") or kwargs.get("_id")
        self.title = title or kwargs.get("title")
        self.description = description or kwargs.get("description")
        self.deadline = _parse_dt(deadline or kwargs.get("deadline"))
        self.priority = (priority or kwargs.get("priority", "medium")).lower()
        self.category = (category or kwargs.get("category", "general")).lower()
        self.status = (status or kwargs.get("status", "pending")).lower()
        self.user_id = int(user_id or kwargs.get("user_id"))
        self.ai_generated = ai_generated if ai_generated is not None else kwargs.get("ai_generated", False)
        self.subtasks = kwargs.get("subtasks", [])
        self.created_at = _parse_dt(kwargs.get("created_at")) or datetime.utcnow()
        self.updated_at = _parse_dt(kwargs.get("updated_at")) or datetime.utcnow()

    # --- Persistence ---
    def save(self):
        task_data = {
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline,
            "priority": self.priority,
            "category": self.category,
            "status": self.status,
            "subtasks": self.subtasks,
            "user_id": self.user_id,
            "ai_generated": self.ai_generated,
            "created_at": self.created_at,
            "updated_at": datetime.utcnow()
        }

        if self.id:
            MongoDBManager.update_document("tasks", _id_query(self.id), task_data)
        else:
            self.id = get_next_sequence_value("task_id")
            task_data["id"] = self.id
            MongoDBManager.insert_document("tasks", task_data)

        return self

    def delete(self):
        return MongoDBManager.delete_document("tasks", _id_query(self.id))

    def set_subtasks(self, subtasks):
        self.subtasks = [s.strip() for s in (subtasks or []) if isinstance(s, str) and s.strip()]

    # --- Serialization ---
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "priority": self.priority,
            "category": self.category,
            "status": self.status,
            "subtasks": self.subtasks,
            "ai_generated": self.ai_generated,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
        }

    # --- Lookups ---
    @staticmethod
    def find_by_id(task_id):
        data = MongoDBManager.find_document("tasks", _id_query(task_id))
        return Task(**data) if data else None

    @staticmethod
    def find_all(sort_criteria=None):
        sort_criteria = sort_criteria or [("deadline", 1), ("created_at", -1)]
        data = MongoDBManager.find_documents("tasks", {}, sort_criteria)
        return [Task(**doc) for doc in data]

    @staticmethod
    def find_by_user_id(uid, filters=None):
        q = {"user_id": int(uid)}

        if filters:
            if filters.get("status"):
                q["status"] = filters["status"]
            if filters.get("priority"):
                q["priority"] = filters["priority"]
            if filters.get("category"):
                q["category"] = filters["category"]
            if filters.get("search"):
                term = filters["search"]
                q["$or"] = [
                    {"title": {"$regex": term, "$options": "i"}},
                    {"description": {"$regex": term, "$options": "i"}}
                ]

        results = MongoDBManager.find_documents("tasks", q, [("deadline", 1), ("created_at", -1)])
        return [Task(**doc) for doc in results]

    @staticmethod
    def get_user_stats(uid):
        pipeline = [
            {"$match": {"user_id": int(uid)}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        raw = MongoDBManager.aggregate("tasks", pipeline)

        stats = {
            "total_tasks": 0,
            "pending_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "completion_rate": 0.0
        }

        for row in raw:
            status = row["_id"]
            cnt = row["count"]
            stats["total_tasks"] += cnt
            if status == "pending":
                stats["pending_tasks"] = cnt
            elif status == "in_progress":
                stats["in_progress_tasks"] = cnt
            elif status == "completed":
                stats["completed_tasks"] = cnt

        if stats["total_tasks"]:
            stats["completion_rate"] = round(stats["completed_tasks"] / stats["total_tasks"] * 100, 1)

        return stats
