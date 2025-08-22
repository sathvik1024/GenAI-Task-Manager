"""
Task reminder scheduler using APScheduler.
Handles automated reminders for upcoming task deadlines.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from models import Task, User
from database import db
import atexit

class TaskScheduler:
    """
    Background scheduler for task reminders and notifications.
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # Schedule reminder checks every hour
        self.scheduler.add_job(
            func=self.check_upcoming_deadlines,
            trigger=IntervalTrigger(hours=1),
            id='deadline_checker',
            name='Check upcoming task deadlines',
            replace_existing=True
        )
        
        # Ensure scheduler shuts down when app exits
        atexit.register(lambda: self.scheduler.shutdown())
    
    def check_upcoming_deadlines(self):
        """
        Check for tasks with deadlines in the next 24 hours.
        In a real app, this would send notifications/emails.
        """
        try:
            now = datetime.utcnow()
            tomorrow = now + timedelta(days=1)
            
            # Find tasks due within 24 hours
            upcoming_tasks = Task.query.filter(
                Task.deadline.between(now, tomorrow),
                Task.status != 'completed'
            ).all()
            
            for task in upcoming_tasks:
                self.send_reminder(task)
                
        except Exception as e:
            print(f"Scheduler error: {e}")
    
    def send_reminder(self, task):
        """
        Send reminder for a specific task.
        In production, this would send email/push notifications.
        """
        user = User.query.get(task.user_id)
        print(f"REMINDER: Task '{task.title}' is due soon for user {user.username}")
        
        # In a real application, you would:
        # - Send email notification
        # - Send push notification
        # - Log to notification system
        # - Update task with reminder_sent flag
    
    def add_custom_reminder(self, task_id, reminder_time):
        """
        Add a custom reminder for a specific task.
        
        Args:
            task_id: ID of the task
            reminder_time: datetime when to send reminder
        """
        try:
            self.scheduler.add_job(
                func=self.send_task_reminder,
                trigger='date',
                run_date=reminder_time,
                args=[task_id],
                id=f'task_reminder_{task_id}',
                replace_existing=True
            )
        except Exception as e:
            print(f"Error adding custom reminder: {e}")
    
    def send_task_reminder(self, task_id):
        """
        Send reminder for a specific task by ID.
        """
        try:
            task = Task.query.get(task_id)
            if task and task.status != 'completed':
                self.send_reminder(task)
        except Exception as e:
            print(f"Error sending task reminder: {e}")
    
    def remove_task_reminders(self, task_id):
        """
        Remove all reminders for a specific task.
        """
        try:
            self.scheduler.remove_job(f'task_reminder_{task_id}')
        except:
            pass  # Job might not exist
    
    def get_scheduler_status(self):
        """
        Get current scheduler status and job count.
        """
        return {
            'running': self.scheduler.running,
            'jobs_count': len(self.scheduler.get_jobs()),
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()
            ]
        }

# Global scheduler instance
task_scheduler = TaskScheduler()
