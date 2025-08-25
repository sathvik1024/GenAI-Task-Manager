"""
AI Service for OpenAI API integration.
Handles task parsing, prioritization, and summary generation.
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

def enhanced_fallback_parsing(user_input: str) -> Dict:
    """Enhanced fallback parsing when OpenAI is not available"""
    text = user_input.lower()

    # Extract title (remove common deadline and priority words)
    title = user_input
    for phrase in [' by ', ' deadline ', ' due ', ' priority', ' urgent', ' high priority', ' low priority', ' medium priority']:
        if phrase in title.lower():
            title = title[:title.lower().find(phrase)]
            break
    title = title.strip()

    # Extract priority
    priority = 'medium'  # default
    if any(word in text for word in ['urgent', 'asap', 'immediately']):
        priority = 'urgent'
    elif any(word in text for word in ['high priority', 'important', 'critical']):
        priority = 'high'
    elif any(word in text for word in ['low priority', 'when possible', 'eventually']):
        priority = 'low'

    # Extract category
    category = 'general'  # default
    categories = {
        'work': ['work', 'office', 'job', 'meeting', 'report', 'project', 'business'],
        'personal': ['personal', 'home', 'family', 'friend'],
        'health': ['doctor', 'appointment', 'medical', 'health', 'exercise', 'gym'],
        'education': ['study', 'homework', 'assignment', 'exam', 'school', 'university', 'college'],
        'shopping': ['buy', 'purchase', 'shop', 'store', 'groceries'],
        'finance': ['bank', 'money', 'payment', 'bill', 'budget', 'finance']
    }

    for cat, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            category = cat
            break

    # Extract deadline (basic patterns)
    deadline = None
    now = datetime.now()

    # Look for day patterns
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(days):
        if day in text:
            # Find next occurrence of this day
            days_ahead = (i - now.weekday()) % 7
            if days_ahead == 0:  # Today
                days_ahead = 7  # Next week
            target_date = now + timedelta(days=days_ahead)

            # Look for time
            time_match = re.search(r'(\d{1,2})\s*(am|pm)', text)
            if time_match:
                hour = int(time_match.group(1))
                if time_match.group(2) == 'pm' and hour != 12:
                    hour += 12
                elif time_match.group(2) == 'am' and hour == 12:
                    hour = 0
                deadline = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            else:
                deadline = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
            break

    return {
        'title': title,
        'description': user_input,
        'deadline': deadline.isoformat() if deadline else None,
        'priority': priority,
        'category': category,
        'subtasks': [],
        'ai_generated': False
    }

def get_openai_client():
    """Get OpenAI client, return None if API key not configured"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("❌ OpenAI API key not configured")
        return None

    print(f"🔑 OpenAI API key found: {api_key[:10]}...")

    try:
        import openai

        # Set the API key
        openai.api_key = api_key

        # Test with a simple API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )

        print("✅ OpenAI client working successfully!")
        return openai

    except Exception as e:
        print(f"❌ OpenAI client failed: {e}")
        return None

class AIService:
    """
    Service class for AI-powered task management features.
    """
    
    @staticmethod
    def parse_natural_language_task(user_input: str) -> Dict:
        """
        Parse natural language input into structured task data.

        Args:
            user_input: Natural language task description

        Returns:
            Dictionary with extracted task details
        """
        print(f"🤖 AI Parsing request: {user_input}")
        client = get_openai_client()
        if not client:
            print("⚠️ OpenAI client not available, using enhanced fallback parsing")
            # Enhanced fallback parsing when OpenAI is not available
            return enhanced_fallback_parsing(user_input)

        try:
            from datetime import datetime, timedelta
            import calendar

            # Get current date for relative date parsing
            now = datetime.now()
            current_year = now.year

            prompt = f"""
            Parse the following natural language task into structured data. Today is {now.strftime('%A, %B %d, %Y')}.

            Extract these fields:
            - title: A clear, concise task title (remove deadline and priority words)
            - description: Detailed description if provided, or expand on the title
            - deadline: Parse any date/time mentioned. Convert relative dates like "Monday", "next Tuesday", "by Friday 9 PM" to YYYY-MM-DD HH:MM:SS format. If only day is mentioned, assume current week. If time is mentioned, use it; otherwise use 23:59:59. Return null if no deadline.
            - priority: Extract from words like "high priority", "urgent", "important", "low priority". Map to: low, medium, high, or urgent. Default to medium if not specified.
            - category: Categorize based on context. Options: work, personal, health, education, shopping, college, family, finance, travel, etc.
            - subtasks: Generate 2-4 logical subtasks to complete this task

            Task input: "{user_input}"

            Examples:
            - "Submit report by Monday 9 PM high priority" → deadline: "2024-MM-DD 21:00:00", priority: "high"
            - "Doctor appointment next Tuesday at 2pm" → deadline: "2024-MM-DD 14:00:00", priority: "medium"
            - "Buy groceries urgent" → deadline: null, priority: "urgent"

            Respond with valid JSON only (no markdown, no explanations):
            """

            print("🤖 Sending request to OpenAI...")

            # Use legacy OpenAI client format
            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a task management assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            ai_response = response.choices[0].message.content
            print(f"🤖 OpenAI response: {ai_response}")

            result = json.loads(ai_response)

            # Validate and set defaults
            parsed_result = {
                'title': result.get('title', user_input[:50]),
                'description': result.get('description', user_input),
                'deadline': result.get('deadline'),
                'priority': result.get('priority', 'medium'),
                'category': result.get('category', 'general'),
                'subtasks': result.get('subtasks', []),
                'ai_generated': True
            }

            print(f"✅ AI parsing successful: {parsed_result}")
            return parsed_result

        except Exception as e:
            print(f"❌ AI parsing error: {e}")
            print("⚠️ OpenAI API failed, using enhanced fallback parsing")
            # Use enhanced fallback parsing when API call fails
            return enhanced_fallback_parsing(user_input)
    
    @staticmethod
    def prioritize_tasks(tasks: List[Dict]) -> List[Dict]:
        """
        Use AI to intelligently prioritize tasks based on deadlines and context.

        Args:
            tasks: List of task dictionaries

        Returns:
            Sorted list of tasks by priority
        """
        client = get_openai_client()
        if not client:
            # Fallback to simple priority sorting
            priority_order = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
            return sorted(tasks, key=lambda x: priority_order.get(x['priority'], 2), reverse=True)

        try:
            tasks_summary = []
            for task in tasks:
                tasks_summary.append({
                    'id': task['id'],
                    'title': task['title'],
                    'deadline': task['deadline'],
                    'priority': task['priority'],
                    'category': task['category']
                })
            
            prompt = f"""
            Analyze these tasks and return them sorted by urgency/importance.
            Consider deadlines, current priority levels, and task categories.
            
            Tasks: {json.dumps(tasks_summary)}
            
            Return a JSON array with task IDs in order of priority (most urgent first):
            ["task_id_1", "task_id_2", ...]
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a productivity expert. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.2
            )
            
            priority_order = json.loads(response.choices[0].message.content)
            
            # Reorder tasks based on AI recommendation
            task_dict = {task['id']: task for task in tasks}
            prioritized_tasks = []
            
            for task_id in priority_order:
                if task_id in task_dict:
                    prioritized_tasks.append(task_dict[task_id])
            
            # Add any remaining tasks
            for task in tasks:
                if task not in prioritized_tasks:
                    prioritized_tasks.append(task)
            
            return prioritized_tasks
            
        except Exception as e:
            print(f"AI prioritization error: {e}")
            # Fallback to simple priority sorting
            priority_order = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
            return sorted(tasks, key=lambda x: priority_order.get(x['priority'], 2), reverse=True)
    
    @staticmethod
    def generate_summary(tasks: List[Dict], period: str = 'daily') -> str:
        """
        Generate AI-powered task summary for daily or weekly periods.

        Args:
            tasks: List of task dictionaries
            period: 'daily' or 'weekly'

        Returns:
            Generated summary text
        """
        client = get_openai_client()
        if not client:
            # Fallback summary
            completed_count = len([t for t in tasks if t['status'] == 'completed'])
            pending_count = len([t for t in tasks if t['status'] in ['pending', 'in_progress']])
            period_text = "today" if period == 'daily' else "this week"

            return f"You've completed {completed_count} tasks {period_text}! " \
                   f"You have {pending_count} tasks remaining. Keep up the great work!"

        try:
            # Filter tasks based on period
            now = datetime.now()
            if period == 'daily':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
                period_text = "today"
            else:  # weekly
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7)
                period_text = "this week"
            
            # Categorize tasks
            completed_tasks = [t for t in tasks if t['status'] == 'completed']
            pending_tasks = [t for t in tasks if t['status'] in ['pending', 'in_progress']]
            overdue_tasks = [t for t in tasks if t['deadline'] and 
                           datetime.fromisoformat(t['deadline'].replace('Z', '+00:00')) < now and 
                           t['status'] != 'completed']
            
            prompt = f"""
            Generate a concise {period} productivity summary based on these tasks:
            
            Completed ({len(completed_tasks)}): {[t['title'] for t in completed_tasks[:5]]}
            Pending ({len(pending_tasks)}): {[t['title'] for t in pending_tasks[:5]]}
            Overdue ({len(overdue_tasks)}): {[t['title'] for t in overdue_tasks[:3]]}
            
            Create a motivating 2-3 sentence summary highlighting progress and next priorities for {period_text}.
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a productivity coach. Be encouraging and actionable."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"AI summary error: {e}")
            # Fallback summary
            completed_count = len([t for t in tasks if t['status'] == 'completed'])
            pending_count = len([t for t in tasks if t['status'] in ['pending', 'in_progress']])
            
            return f"You've completed {completed_count} tasks {period_text}! " \
                   f"You have {pending_count} tasks remaining. Keep up the great work!"
