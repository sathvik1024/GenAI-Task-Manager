"""
MongoDB models for User and Task collections.
Provides object-oriented interface for MongoDB documents.
"""

from datetime import datetime
from flask_bcrypt import Bcrypt
from bson import ObjectId
from database_mongo import MongoDBManager, get_next_sequence_value
import json

bcrypt = Bcrypt()

class User:
    """User model for MongoDB."""
    
    def __init__(self, username=None, email=None, password=None, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id')
        self.username = username
        self.email = email
        self.password_hash = kwargs.get('password_hash')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        
        if password:
            self.set_password(password)
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def save(self):
        """Save user to database."""
        user_data = {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            # Update existing user
            MongoDBManager.update_document('users', {'_id': ObjectId(self.id)}, user_data)
        else:
            # Create new user with auto-incrementing ID
            self.id = get_next_sequence_value('user_id')
            user_data['id'] = self.id
            result_id = MongoDBManager.insert_document('users', user_data)
            if not hasattr(self, 'id') or not self.id:
                self.id = self.id
        
        return self
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    @staticmethod
    def find_by_username(username):
        """Find user by username."""
        user_data = MongoDBManager.find_document('users', {'username': username})
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def find_by_email(email):
        """Find user by email."""
        user_data = MongoDBManager.find_document('users', {'email': email})
        if user_data:
            return User(**user_data)
        return None
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID."""
        
        query = {'$or': [{'id': int(user_id)}, {'_id': ObjectId(user_id) if ObjectId.is_valid(str(user_id)) else None}]}
        user_data = MongoDBManager.find_document('users', query)
        if user_data:
            return User(**user_data)
        return None

class Task:
    """Task model for MongoDB.Represents one task belonging to a user."""
    
    def __init__(self, title=None, description=None, deadline=None, priority='medium', 
                 category='general', status='pending', user_id=None, ai_generated=False, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id')
        self.title = title
        self.description = description
        self.deadline = deadline
        self.priority = priority
        self.category = category
        self.status = status
        self.user_id = user_id
        self.ai_generated = ai_generated
        self.subtasks = kwargs.get('subtasks', [])
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
    
    def save(self):
        """Save task to database."""
        task_data = {
            'title': self.title,
            'description': self.description,
            'deadline': self.deadline,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'user_id': self.user_id,
            'ai_generated': self.ai_generated,
            'subtasks': self.subtasks,
            'created_at': self.created_at,
            'updated_at': datetime.utcnow()
        }
        
        if self.id:
            # Update existing task
            query = {'$or': [{'id': int(self.id)}, {'_id': ObjectId(self.id) if ObjectId.is_valid(str(self.id)) else None}]}
            MongoDBManager.update_document('tasks', query, task_data)
        else:
            # Create new task with auto-incrementing ID
            self.id = get_next_sequence_value('task_id')
            task_data['id'] = self.id
            result_id = MongoDBManager.insert_document('tasks', task_data)
        
        return self
    
    def delete(self):
        """Delete task from database."""
        if self.id:
            query = {'$or': [{'id': int(self.id)}, {'_id': ObjectId(self.id) if ObjectId.is_valid(str(self.id)) else None}]}
            return MongoDBManager.delete_document('tasks', query)
        return False
    
    def set_subtasks(self, subtasks):
        """Set subtasks for the task."""
        self.subtasks = subtasks if isinstance(subtasks, list) else []
    
    def get_subtasks(self):
        """Get subtasks for the task."""
        return self.subtasks or []
    
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
    
    @staticmethod
    def find_by_id(task_id):
        """Find task by ID."""
        query = {'$or': [{'id': int(task_id)}, {'_id': ObjectId(task_id) if ObjectId.is_valid(str(task_id)) else None}]}
        task_data = MongoDBManager.find_document('tasks', query)
        if task_data:
            return Task(**task_data)
        return None
    
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
        
        # Sort by deadline (ascending, nulls last) then by created_at (descending)
        sort_criteria = [('deadline', 1), ('created_at', -1)]
        
        tasks_data = MongoDBManager.find_documents('tasks', query, sort_criteria)
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
