"""
AI Service for OpenAI API integration.
Handles task parsing, prioritization, and summary generation.
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .translation_service import translation_service
from dateutil import parser as date_parser  # For deadline normalization

def normalize_deadline(deadline_str: Optional[str]) -> Optional[str]:
    """Convert various deadline formats into ISO 8601 string."""
    if not deadline_str:
        return None
    try:
        dt = date_parser.parse(deadline_str, dayfirst=True)
        return dt.isoformat()
    except Exception:
        return None

def enhanced_fallback_parsing(user_input: str) -> Dict:
    """Enhanced fallback parsing when OpenAI is not available"""
    text = user_input.lower()

    # Extract title (remove common deadline and priority words)
    title = user_input
    for phrase in [
        ' by ', ' deadline ', ' due ', ' priority',
        ' urgent', ' high priority', ' low priority', ' medium priority'
    ]:
        if phrase in title.lower():
            title = title[:title.lower().find(phrase)]
            break
    title = title.strip()

    # Extract priority
    priority = 'medium'
    if any(word in text for word in ['urgent', 'asap', 'immediately']):
        priority = 'urgent'
    elif any(word in text for word in ['high priority', 'important', 'critical']):
        priority = 'high'
    elif any(word in text for word in ['low priority', 'when possible', 'eventually']):
        priority = 'low'

    # Extract category
    category = 'general'
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

    deadline = None
    # Try to extract explicit date/time first (e.g., "22-08-2025 9 PM")
    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*(\d{1,2}\s*(am|pm)|\d{1,2}:\d{2})?', text)
    if date_match:
        date_str = date_match.group(0)
        deadline = normalize_deadline(date_str)
    else:
        # Look for day-of-week patterns
        now = datetime.now()
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(days):
            if day in text:
                days_ahead = (i - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = now + timedelta(days=days_ahead)
                time_match = re.search(r'(\d{1,2})\s*(am|pm)', text)
                if time_match:
                    hour = int(time_match.group(1))
                    if time_match.group(2) == 'pm' and hour != 12:
                        hour += 12
                    elif time_match.group(2) == 'am' and hour == 12:
                        hour = 0
                    deadline_dt = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                else:
                    deadline_dt = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
                deadline = normalize_deadline(deadline_dt.isoformat())
                break

    return {
        'title': title,
        'description': user_input,
        'deadline': deadline,
        'priority': priority,
        'category': category,
        'subtasks': [],
        'ai_generated': False
    }

def get_openai_client():
    """Get OpenAI client, return None if API key not configured"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("OpenAI API key not configured")
        return None

    try:
        import openai
        openai.api_key = api_key
        # Test API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return openai
    except Exception as e:
        print(f"OpenAI client failed: {e}")
        return None

class AIService:
    """
    Service class for AI-powered task management features.
    """

    @staticmethod
    def parse_natural_language_task(user_input: str) -> Dict:
        """Parse natural language input into structured task data with multilingual support."""
        translation_result = translation_service.translate_to_english(user_input)
        original_text = translation_result['original_text']
        english_text = translation_result['translated_text']
        source_lang = translation_result['source_language']

        multilingual_features = translation_service.extract_multilingual_features(original_text, source_lang)

        client = get_openai_client()
        if not client:
            fallback_result = enhanced_fallback_parsing(english_text)
            fallback_result.update({
                'priority': multilingual_features['priority'],
                'category': multilingual_features['category'],
                'original_language': source_lang,
                'original_text': original_text,
                'description': original_text
            })
            return fallback_result

        try:
            now = datetime.now()
            prompt = f"""
            Parse the following natural language task into structured data. Today is {now.strftime('%A, %B %d, %Y')}.
            Task input (translated to English): "{english_text}"
            Original input: "{original_text}"

            Extract these fields strictly in JSON:
            - title
            - description
            - deadline (extract any date/time mentioned, format as YYYY-MM-DD HH:MM:SS, or null if not present)
            - priority (low, medium, high, urgent)
            - category
            - subtasks (2-4 items)
            """

            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a task management assistant. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            ai_response = response.choices[0].message.content
            result = json.loads(ai_response)

            parsed_result = {
                'title': result.get('title', english_text[:50]),
                'description': original_text,
                'deadline': normalize_deadline(result.get('deadline')),
                'priority': result.get('priority') or multilingual_features['priority'],
                'category': result.get('category') or multilingual_features['category'],
                'subtasks': result.get('subtasks', []),
                'ai_generated': True,
                'original_language': source_lang,
                'original_text': original_text,
                'translated_text': english_text if translation_result['translation_needed'] else None
            }
            return parsed_result

        except Exception as e:
            fallback_result = enhanced_fallback_parsing(english_text)
            fallback_result.update({
                'priority': multilingual_features['priority'],
                'category': multilingual_features['category'],
                'original_language': source_lang,
                'original_text': original_text,
                'description': original_text,
                'translated_text': english_text if translation_result['translation_needed'] else None
            })
            return fallback_result

    @staticmethod
    def prioritize_tasks(tasks: List[Dict]) -> List[Dict]:
        """Use AI to intelligently prioritize tasks."""
        client = get_openai_client()
        if not client:
            priority_order = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
            return sorted(tasks, key=lambda x: priority_order.get(x['priority'], 2), reverse=True)

        try:
            tasks_summary = [
                {
                    'id': task['id'],
                    'title': task['title'],
                    'deadline': task['deadline'],
                    'priority': task['priority'],
                    'category': task['category']
                }
                for task in tasks
            ]

            prompt = f"""
            Sort these tasks by urgency/importance considering deadlines and priorities.
            Tasks: {json.dumps(tasks_summary)}
            Return a JSON array of task IDs in order.
            """

            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a productivity expert. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.2
            )

            priority_order = json.loads(response.choices[0].message.content)
            task_dict = {task['id']: task for task in tasks}
            prioritized_tasks = [task_dict[tid] for tid in priority_order if tid in task_dict]

            for task in tasks:
                if task not in prioritized_tasks:
                    prioritized_tasks.append(task)

            return prioritized_tasks

        except Exception as e:
            priority_order = {'urgent': 4, 'high': 3, 'medium': 2, 'low': 1}
            return sorted(tasks, key=lambda x: priority_order.get(x['priority'], 2), reverse=True)

    @staticmethod
    def generate_summary(tasks: List[Dict], period: str = 'daily') -> str:
        """Generate AI-powered task summary for daily or weekly periods."""
        client = get_openai_client()
        if not client:
            completed_count = len([t for t in tasks if t['status'] == 'completed'])
            pending_count = len([t for t in tasks if t['status'] in ['pending', 'in_progress']])
            period_text = "today" if period == 'daily' else "this week"
            return f"You've completed {completed_count} tasks {period_text}! You have {pending_count} remaining."

        try:
            now = datetime.now()
            if period == 'daily':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
                period_text = "today"
            else:
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=7)
                period_text = "this week"

            completed_tasks = [t for t in tasks if t['status'] == 'completed']
            pending_tasks = [t for t in tasks if t['status'] in ['pending', 'in_progress']]
            overdue_tasks = [t for t in tasks if t['deadline'] and
                             datetime.fromisoformat(t['deadline'].replace('Z', '+00:00')) < now and
                             t['status'] != 'completed']

            prompt = f"""
            Generate a concise {period} productivity summary.
            Completed: {[t['title'] for t in completed_tasks[:5]]}
            Pending: {[t['title'] for t in pending_tasks[:5]]}
            Overdue: {[t['title'] for t in overdue_tasks[:3]]}
            """

            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a productivity coach. Be encouraging."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            completed_count = len([t for t in tasks if t['status'] == 'completed'])
            pending_count = len([t for t in tasks if t['status'] in ['pending', 'in_progress']])
            return f"You've completed {completed_count} tasks {period_text}! You have {pending_count} remaining."