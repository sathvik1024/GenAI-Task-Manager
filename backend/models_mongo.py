"""
MongoDB models for User and Task collections.
Provides object-oriented interface for MongoDB documents.
"""

from datetime import datetime
from flask_bcrypt import Bcrypt
from bson import ObjectId
from database_mongo import MongoDBManager, get_next_sequence_value

bcrypt = Bcrypt()

# =====================================================
# 🧍‍♂️ USER MODEL
# =====================================================
class User:
    """User model for MongoDB."""

    def __init__(self, username=None, email=None, password=None, whatsapp_number=None, **kwargs):
        # Prefer our custom auto-incrementing `id` if present; otherwise fallback to Mongo `_id`
        self.id = kwargs.get('id') or kwargs.get('_id')
        self.username = username or kwargs.get('username')
        self.email = email or kwargs.get('email')
        self.password_hash = kwargs.get('password_hash')
        self.whatsapp_number = whatsapp_number or kwargs.get('whatsapp_number')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())

        if password:
            self.set_password(password)

    # ---- Password Handling ----
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Check if provided password matches hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    # ---- CRUD ----
    def save(self):
        """Save user to database."""
        user_data = {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'whatsapp_number': self.whatsapp_number,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }

        if self.id:
            # Update existing user; support both numeric id and _id ObjectId
            query = {'$or': []}
            try:
                query['$or'].append({'id': int(self.id)})
            except Exception:
                pass
            if ObjectId.is_valid(str(self.id)):
                query['$or'].append({'_id': ObjectId(str(self.id))})
            if not query['$or']:
                # Fallback to username if id parsing failed (rare)
                query = {'username': self.username}
            MongoDBManager.update_document('users', query, user_data)
        else:
            # Create new user with auto-increment ID
            self.id = get_next_sequence_value('user_id')
            user_data['id'] = self.id
            MongoDBManager.insert_document('users', user_data)

        return self

    def to_dict(self):
        """Convert user to dictionary (excluding password)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'whatsapp_number': self.whatsapp_number,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }

    # ---- Finders ----
    @staticmethod
    def find_by_username(username):
        """Find user by username."""
        user_data = MongoDBManager.find_document('users', {'username': username})
        return User(**user_data) if user_data else None

    @staticmethod
    def find_by_email(email):
        """Find user by email."""
        user_data = MongoDBManager.find_document('users', {'email': email})
        return User(**user_data) if user_data else None

    @staticmethod
    def find_by_whatsapp(whatsapp_number):
        """Find user by WhatsApp number."""
        user_data = MongoDBManager.find_document('users', {'whatsapp_number': whatsapp_number})
        return User(**user_data) if user_data else None

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID (auto or ObjectId)."""
        ors = [{'id': int(user_id)}] if str(user_id).isdigit() else []
        if ObjectId.is_valid(str(user_id)):
            ors.append({'_id': ObjectId(str(user_id))})
        query = {'$or': ors} if ors else {'id': -1}  # impossible fallback
        user_data = MongoDBManager.find_document('users', query)
        return User(**user_data) if user_data else None


# =====================================================
# ✅ TASK MODEL
# =====================================================
class Task:
    """Task model for MongoDB. Represents one task belonging to a user."""

    def __init__(self, title=None, description=None, deadline=None, priority='medium',
                 category='general', status='pending', user_id=None, ai_generated=False, **kwargs):
        # Prefer our custom int id if present; otherwise fallback to Mongo _id
        self.id = kwargs.get('id') or kwargs.get('_id')
        self.title = title or kwargs.get('title')
        self.description = description or kwargs.get('description')
        self.deadline = deadline or kwargs.get('deadline')  # may be datetime or ISO string depending on usage
        self.priority = priority or kwargs.get('priority', 'medium')
        self.category = category or kwargs.get('category', 'general')
        self.status = status or kwargs.get('status', 'pending')
        self.user_id = user_id if user_id is not None else kwargs.get('user_id')
        self.ai_generated = ai_generated if ai_generated is not None else kwargs.get('ai_generated', False)
        self.subtasks = kwargs.get('subtasks', [])
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())

    # ---- CRUD ----
    def save(self):
        """Save task to database."""
        task_data = {
            'title': self.title,
            'description': self.description,
            'deadline': self.deadline,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'user_id': int(self.user_id) if self.user_id is not None else None,
            'ai_generated': self.ai_generated,
            'subtasks': self.subtasks,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }

        if self.id:
            # Update existing task; support numeric id and _id
            query = {'$or': []}
            try:
                query['$or'].append({'id': int(self.id)})
            except Exception:
                pass
            if ObjectId.is_valid(str(self.id)):
                query['$or'].append({'_id': ObjectId(str(self.id))})
            if not query['$or']:
                # Fallback (should not happen if ids are consistent)
                query = {'title': self.title, 'user_id': task_data['user_id']}
            MongoDBManager.update_document('tasks', query, task_data)
        else:
            # Create new task with auto-incrementing ID
            self.id = get_next_sequence_value('task_id')
            task_data['id'] = self.id
            MongoDBManager.insert_document('tasks', task_data)

        return self

    def delete(self):
        """Delete task from database."""
        if not self.id:
            return False
        query = {'$or': []}
        try:
            query['$or'].append({'id': int(self.id)})
        except Exception:
            pass
        if ObjectId.is_valid(str(self.id)):
            query['$or'].append({'_id': ObjectId(str(self.id))})
        if not query['$or']:
            return False
        return MongoDBManager.delete_document('tasks', query)

    # ---- Subtasks ----
    def set_subtasks(self, subtasks):
        """Set subtasks for the task."""
        self.subtasks = subtasks if isinstance(subtasks, list) else []

    def get_subtasks(self):
        """Get subtasks for the task."""
        return self.subtasks or []

    # ---- Serialization ----
    def to_dict(self):
        """Convert task to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'deadline': self.deadline.isoformat() if isinstance(self.deadline, datetime) and self.deadline else self.deadline,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'subtasks': self.get_subtasks(),
            'ai_generated': self.ai_generated,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'user_id': self.user_id
        }

    # ---- Finders ----
    @staticmethod
    def find_by_id(task_id):
        """Find task by ID."""
        ors = [{'id': int(task_id)}] if str(task_id).isdigit() else []
        if ObjectId.is_valid(str(task_id)):
            ors.append({'_id': ObjectId(str(task_id))})
        query = {'$or': ors} if ors else {'id': -1}
        task_data = MongoDBManager.find_document('tasks', query)
        return Task(**task_data) if task_data else None

    @staticmethod
    def find_by_user_id(user_id, filters=None):
        """Find tasks by user ID with optional filters."""
        query = {'user_id': int(user_id)}

        if filters:
            if filters.get('status'):
                query['status'] = filters['status']
            if filters.get('priority'):
                query['priority'] = filters['priority']
            if filters.get('category'):
                query['category'] = filters['category']
            if filters.get('search'):
                search_term = filters['search']
                query['$or'] = [
                    {'title': {'$regex': search_term, '$options': 'i'}},
                    {'description': {'$regex': search_term, '$options': 'i'}}
                ]

        # Sort by deadline ascending (nulls last), then by created_at descending
        sort_criteria = [('deadline', 1), ('created_at', -1)]
        tasks_data = MongoDBManager.find_documents('tasks', query, sort_criteria)
        return [Task(**task_data) for task_data in tasks_data]

    @staticmethod
    def find_all(sort_criteria=None):
        """Find all tasks (helper for schedulers/maintenance jobs)."""
        sort_criteria = sort_criteria or [('deadline', 1), ('created_at', -1)]
        tasks_data = MongoDBManager.find_documents('tasks', {}, sort_criteria)
        return [Task(**task_data) for task_data in tasks_data]

    @staticmethod
    def get_user_stats(user_id):
        """Get task statistics for a user."""
        pipeline = [
            {'$match': {'user_id': int(user_id)}},
            {'$group': {
                '_id': '$status',
                'count': {'$sum': 1}
            }}
        ]

        stats_data = MongoDBManager.aggregate('tasks', pipeline)

        # Initialize stats
        stats = {
            'total_tasks': 0,
            'pending_tasks': 0,
            'in_progress_tasks': 0,
            'completed_tasks': 0,
            'completion_rate': 0.0
        }

        # Process aggregation results
        for stat in stats_data:
            status = stat['_id']
            count = stat['count']
            stats['total_tasks'] += count

            if status == 'pending':
                stats['pending_tasks'] = count
            elif status == 'in_progress':
                stats['in_progress_tasks'] = count
            elif status == 'completed':
                stats['completed_tasks'] = count

        # Calculate completion rate
        if stats['total_tasks'] > 0:
            stats['completion_rate'] = round(
                (stats['completed_tasks'] / stats['total_tasks']) * 100, 1
            )

        return stats
