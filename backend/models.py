"""
Database models for Users and Tasks.
Defines the structure and relationships for the GenAI Task Manager.
"""

from database import db
from datetime import datetime
from flask_bcrypt import Bcrypt
import json

bcrypt = Bcrypt()

class User(db.Model):
    """
    User model for authentication and task ownership.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with tasks
    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if provided password matches hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary (excluding password)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

class Task(db.Model):
    """
    Task model with AI-enhanced fields for structured task management.
    """
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    category = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    subtasks = db.Column(db.Text)  # JSON string of subtasks
    ai_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key to user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def set_subtasks(self, subtasks_list):
        """Convert list of subtasks to JSON string."""
        self.subtasks = json.dumps(subtasks_list) if subtasks_list else None
    
    def get_subtasks(self):
        """Convert JSON string back to list of subtasks."""
        return json.loads(self.subtasks) if self.subtasks else []
    
    def to_dict(self):
        """Convert task to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'priority': self.priority,
            'category': self.category,
            'status': self.status,
            'subtasks': self.get_subtasks(),
            'ai_generated': self.ai_generated,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id
        }
