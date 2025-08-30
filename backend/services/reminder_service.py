import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from database_mongo import MongoDBManager
from flask import current_app

mail = Mail()
scheduler = BackgroundScheduler()

def send_reminder_email(app, user_email, task_title, deadline):
    with app.app_context():
        msg = Message(
            subject="Task Reminder: " + task_title,
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user_email],
            body=f"Reminder: Your task '{task_title}' is due at {deadline}."
        )
        mail.send(msg)

def schedule_task_reminder(task, app=None):
    # Only schedule if deadline exists and is in the future
    if not task.get('deadline'):
        return
    deadline = datetime.fromisoformat(task['deadline'])
    reminder_time = deadline - timedelta(minutes=30)
    if reminder_time > datetime.now():
        scheduler.add_job(
            send_reminder_email,
            'date',
            run_date=reminder_time,
            args=[app, task['user_email'], task['title'], task['deadline']],
            id=f"reminder_{task['id']}"
        )

def start_scheduler(app):
    mail.init_app(app)
    scheduler.start()