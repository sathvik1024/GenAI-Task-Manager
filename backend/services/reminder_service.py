import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from dateutil import parser   # <-- handles ISO + human-readable date strings
from flask import current_app

# Global mail + scheduler
mail = Mail()
scheduler = BackgroundScheduler()

def send_reminder_email(app, user_email, task_title, deadline):
    """
    Send reminder email for an upcoming task.
    Runs inside Flask app context to access configs.
    """
    with app.app_context():
        try:
            msg = Message(
                subject="Task Reminder: " + task_title,
                sender=os.getenv("MAIL_DEFAULT_SENDER"),
                recipients=[user_email],
                body=f"Reminder: Your task '{task_title}' is due at {deadline}."
            )
            mail.send(msg)
            print(f"✅ Reminder email sent to {user_email} for task '{task_title}'")
        except Exception as e:
            print(f"❌ Failed to send reminder email: {e}")

def schedule_task_reminder(task, app=None):
    """
    Schedule a reminder 30 minutes before task deadline.
    Only runs if deadline is valid and in the future.
    """
    if not task.get('deadline'):
        print("⚠️ No deadline provided, skipping reminder scheduling.")
        return
    
    try:
        # Parse deadline safely (works for ISO and human-readable formats)
        deadline = parser.parse(task['deadline'])
    except Exception as e:
        print(f"❌ Deadline parsing failed: {e} | Value: {task['deadline']}")
        return

    reminder_time = deadline - timedelta(minutes=30)

    print(f"⏰ Scheduling reminder at {reminder_time}, now is {datetime.now()}")

    if reminder_time > datetime.now():
        try:
            scheduler.add_job(
                send_reminder_email,
                'date',
                run_date=reminder_time,
                args=[app, task['user_email'], task['title'], task['deadline']],
                id=f"reminder_{task.get('id', task.get('_id', ''))}",
                replace_existing=True
            )
            print("✅ Reminder job added:", scheduler.get_jobs())
        except Exception as e:
            print(f"❌ Failed to add reminder job: {e}")
    else:
        print("⚠️ Reminder time already passed, not scheduling.")

def send_task_creation_email(app, user_email, task_title, deadline):
    """
    Send an email when a task is created (confirmation).
    """
    with app.app_context():
        try:
            msg = Message(
                subject="New Task Created: " + task_title,
                sender=os.getenv("MAIL_DEFAULT_SENDER"),
                recipients=[user_email],
                body=f"You have created a new task '{task_title}' with deadline {deadline}."
            )
            mail.send(msg)
            print(f"✅ Task creation email sent to {user_email} for task '{task_title}'")
        except Exception as e:
            print(f"❌ Failed to send creation email: {e}")

def start_scheduler(app):
    """
    Initialize Flask-Mail and start the background scheduler.
    This must be called from app.py when the app starts.
    """
    try:
        mail.init_app(app)
        scheduler.start()
        print("✅ Reminder scheduler started successfully!")
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")
