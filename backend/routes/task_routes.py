"""
Task management routes for CRUD operations.
Handles creating, reading, updating, and deleting tasks.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models_mongo import Task, User
from datetime import datetime
from services.email_service import EmailService

# Create task management blueprint
task_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@task_bp.route('/', methods=['GET'])
@jwt_required()
def get_tasks():
    """
    Get all tasks for the authenticated user with optional filtering.
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int

        # Get filters from request
        filters = {}

        status = request.args.get('status')
        if status:
            filters['status'] = status

        priority = request.args.get('priority')
        if priority:
            filters['priority'] = priority
        
        category = request.args.get('category')
        if category:
            filters['category'] = category

        search = request.args.get('search')
        if search:
            filters['search'] = search

        # Get tasks using MongoDB model
        tasks = Task.find_by_user_id(user_id, filters)

        return jsonify({
            'tasks': [task.to_dict() for task in tasks],
            'count': len(tasks)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get tasks: {str(e)}'}), 500

@task_bp.route('/', methods=['POST'])
@jwt_required()
def create_task():
    """
    Create a new task for the authenticated user.
    """
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({'error': 'Title is required'}), 400

        deadline = None
        if data.get('deadline'):
            try:
                deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid deadline format'}), 400

        task = Task(
            title=data['title'].strip(),
            description=data.get('description', '').strip(),
            deadline=deadline,
            priority=data.get('priority', 'medium'),
            category=data.get('category', 'general'),
            status='pending',
            user_id=user_id,
            ai_generated=data.get('ai_generated', False)
        )

        if data.get('subtasks'):
            task.set_subtasks(data['subtasks'])

        task.save()

        from services.reminder_service import schedule_task_reminder, mail
        user = User.find_by_id(user_id)
        task_dict = task.to_dict()
        if user and user.email:
            task_dict['user_email'] = user.email
            schedule_task_reminder(task_dict, current_app)
            EmailService.send_task_created_notification(mail, user.email, task_dict)

        return jsonify({
            'message': 'Task created successfully',
            'task': task.to_dict()
        }), 201

    except Exception as e:
        return jsonify({'error': f'Failed to create task: {str(e)}'}), 500

@task_bp.route('/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """
    Get a specific task by ID (only if owned by authenticated user).
    """
    try:
        user_id = int(get_jwt_identity()) 
        task = Task.find_by_id(task_id)

        if not task or task.user_id != user_id:
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify({'task': task.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get task: {str(e)}'}), 500

@task_bp.route('/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """
    Update a specific task (only if owned by authenticated user).
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        task = Task.find_by_id(task_id)

        if not task or task.user_id != user_id:
            return jsonify({'error': 'Task not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update
        if 'title' in data:
            task.title = data['title'].strip()
        
        if 'description' in data:
            task.description = data['description'].strip()
        
        if 'deadline' in data:
            if data['deadline']:
                try:
                    task.deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'error': 'Invalid deadline format'}), 400
            else:
                task.deadline = None
        
        if 'priority' in data:
            task.priority = data['priority']
        
        if 'category' in data:
            task.category = data['category']
        
        if 'status' in data:
            task.status = data['status']
        
        if 'subtasks' in data:
            task.set_subtasks(data['subtasks'])
        
        task.updated_at = datetime.utcnow()

        # Save to MongoDB
        task.save()

        return jsonify({
            'message': 'Task updated successfully',
            'task': task.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to update task: {str(e)}'}), 500

@task_bp.route('/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """
    Delete a specific task (only if owned by authenticated user).
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        task = Task.find_by_id(task_id)

        if not task or task.user_id != user_id:
            return jsonify({'error': 'Task not found'}), 404

        # Delete from MongoDB
        task.delete()

        return jsonify({'message': 'Task deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to delete task: {str(e)}'}), 500

@task_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_task_stats():
    """
    Get task statistics for the authenticated user.
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int

        # user statistics using MongoDB model
        stats = Task.get_user_stats(user_id)

        # Get all user tasks for additional calculations
        all_tasks = Task.find_by_user_id(user_id)

        # Count tasks by priority
        urgent_tasks = len([t for t in all_tasks if t.priority == 'urgent'])
        high_tasks = len([t for t in all_tasks if t.priority == 'high'])

        # Count overdue tasks
        now = datetime.utcnow()
        overdue_tasks = 0
        for task in all_tasks:
            if (task.deadline and
                isinstance(task.deadline, datetime) and
                task.deadline < now and
                task.status != 'completed'):
                overdue_tasks += 1
        
        return jsonify({
            'total_tasks': stats['total_tasks'],
            'completed_tasks': stats['completed_tasks'],
            'pending_tasks': stats['pending_tasks'],
            'in_progress_tasks': stats['in_progress_tasks'],
            'urgent_tasks': urgent_tasks,
            'high_priority_tasks': high_tasks,
            'overdue_tasks': overdue_tasks,
            'completion_rate': stats['completion_rate']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500

@task_bp.route('/test-email', methods=['POST'])
@jwt_required()
def test_email():
    """
    Test email configuration by sending a test email.
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.find_by_id(user_id)  # Using MongoDB model

        if not user or not user.email:
            return jsonify({'error': 'User email not found'}), 400

        from services.reminder_service import mail
        success, message = EmailService.send_test_email(mail, user.email)

        if success:
            return jsonify({
                'message': 'Test email sent successfully',
                'email': user.email
            }), 200
        else:
            return jsonify({'error': message}), 500

    except Exception as e:
        return jsonify({'error': f'Failed to send test email: {str(e)}'}), 500