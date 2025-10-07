"""
AI-powered routes for task parsing, prioritization, and summary generation.
Integrates OpenAI API for intelligent task management features.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models_mongo import Task, User
from services.ai_service import AIService
from services.email_service import EmailService
from datetime import datetime
from services.reminder_service import mail

# Create AI routes blueprint
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

@ai_bp.route('/parse-task', methods=['POST'])
@jwt_required()
def parse_natural_language_task():
    """
    Parse natural language input into structured task data using AI.
    
    {
        "input": "string - natural language task description"
    }
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        data = request.get_json()
        
        if not data or 'input' not in data:
            return jsonify({'error': 'Input text is required'}), 400
        
        user_input = data['input'].strip()
        if not user_input:
            return jsonify({'error': 'Input cannot be empty'}), 400
        
        # Use AI service to parse the task
        parsed_task = AIService.parse_natural_language_task(user_input)
        
        return jsonify({
            'message': 'Task parsed successfully',
            'parsed_task': parsed_task
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to parse task: {str(e)}'}), 500

@ai_bp.route('/create-from-text', methods=['POST'])
@jwt_required()
def create_task_from_text():
    """
    Parse natural language input and directly create a task.
    
    Expected JSON:
    {
        "input": "string - natural language task description"
    }
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        data = request.get_json()

        if not data or 'input' not in data:
            return jsonify({'error': 'Input text is required'}), 400
        
        user_input = data['input'].strip()
        if not user_input:
            return jsonify({'error': 'Input cannot be empty'}), 400
        
        # Parse task using AI
        parsed_data = AIService.parse_natural_language_task(user_input)
        
        # Parse deadline if provided
        deadline = None
        if parsed_data.get('deadline'):
            try:
                deadline = datetime.fromisoformat(parsed_data['deadline'])
            except (ValueError, TypeError):
                deadline = None
        
        # Create new task
        task = Task(
            title=parsed_data['title'],
            description=parsed_data['description'],
            deadline=deadline,
            priority=parsed_data['priority'],
            category=parsed_data['category'],
            status='pending',
            user_id=user_id,
            ai_generated=parsed_data['ai_generated']
        )
        
        # Set subtasks if provided
        if parsed_data.get('subtasks'):
            task.set_subtasks(parsed_data['subtasks'])
        
        task.save() #to mongodb

        # Send email notification
        try:
            user = User.find_by_id(user_id)
            if user and user.email:

                EmailService.send_task_created_notification(
                    mail,
                    user.email,
                    task.to_dict()
                )
        except Exception as email_error:
            print(f"Failed to send email notification: {email_error}")

        return jsonify({
            'message': 'Task created successfully from AI parsing',
            'task': task.to_dict(),
            'original_input': user_input
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to create task from text: {str(e)}'}), 500

@ai_bp.route('/prioritize-tasks', methods=['POST'])
@jwt_required()
def prioritize_user_tasks():
    """
    Use AI to intelligently prioritize user's tasks.

    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        data = request.get_json() or {}
        
        # Get tasks to prioritize
        if 'task_ids' in data and data['task_ids']:
            # Get specific tasks by IDs
            all_user_tasks = Task.find_by_user_id(user_id)
            tasks = [task for task in all_user_tasks
                    if task.id in data['task_ids'] and task.status != 'completed']
        else:
            # Get all non-completed tasks
            all_user_tasks = Task.find_by_user_id(user_id)
            tasks = [task for task in all_user_tasks if task.status != 'completed']
        
        if not tasks:
            return jsonify({'message': 'No tasks to prioritize'}), 200
        
        # Convert to dictionaries for AI processing
        task_dicts = [task.to_dict() for task in tasks]
        
        # Use AI to prioritize
        prioritized_tasks = AIService.prioritize_tasks(task_dicts)
        
        return jsonify({
            'message': 'Tasks prioritized successfully',
            'prioritized_tasks': prioritized_tasks,
            'count': len(prioritized_tasks)
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to prioritize tasks: {str(e)}'}), 500

@ai_bp.route('/generate-summary', methods=['GET'])
@jwt_required()
def generate_task_summary():
    """
    Generate AI-powered summary of user's tasks.
    
    Query parameters:
    - period: 'daily' or 'weekly' (default: daily)
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int
        period = request.args.get('period', 'daily')
        
        if period not in ['daily', 'weekly']:
            return jsonify({'error': 'Period must be daily or weekly'}), 400
        
        # Get user's tasks
        tasks = Task.find_by_user_id(user_id)
        task_dicts = [task.to_dict() for task in tasks]
        
        # Generate summary using AI
        summary = AIService.generate_summary(task_dicts, period)
        
        # stats like total, completed and pendinggg
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'completed'])
        pending_tasks = len([t for t in tasks if t.status in ['pending', 'in_progress']])
        
        return jsonify({
            'summary': summary,
            'period': period,
            'stats': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'pending_tasks': pending_tasks
            },
            'generated_at': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500

@ai_bp.route('/suggest-subtasks', methods=['POST'])
@jwt_required()
def suggest_subtasks():
    """
    Generate AI suggestions for subtasks based on a task title/description.

    """
    try:
        data = request.get_json()
        
        if not data or 'title' not in data:
            return jsonify({'error': 'Task title is required'}), 400
        
        title = data['title'].strip()
        description = data.get('description', '').strip()
        
        # Create a temporary task input for AI parsing
        task_input = f"{title}. {description}".strip()
        
        # Use AI to parse and get subtasks
        parsed_data = AIService.parse_natural_language_task(task_input)
        
        return jsonify({
            'suggested_subtasks': parsed_data.get('subtasks', []),
            'suggested_category': parsed_data.get('category', 'general'),
            'suggested_priority': parsed_data.get('priority', 'medium')
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to suggest subtasks: {str(e)}'}), 500

@ai_bp.route('/health', methods=['GET'])
def ai_health_check():
    """
    Check if AI service is available and configured.
    """
    try:
        import os
        api_key_configured = bool(os.getenv('OPENAI_API_KEY'))
        
        return jsonify({
            'ai_service_available': True,
            'openai_api_configured': api_key_configured,
            'status': 'healthy' if api_key_configured else 'missing_api_key'
        }), 200
        
    except Exception as e:
        return jsonify({
            'ai_service_available': False,
            'error': str(e),
            'status': 'unhealthy'
        }), 500
