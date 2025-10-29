"""
Email service for sending task notifications.
Handles email configuration and sending task-related emails.
"""

import os
from flask import current_app
from flask_mail import Mail, Message
from datetime import datetime
from typing import Dict, Optional, Tuple

try:
    # Optional: nicer date parsing if available
    from dateutil import parser as date_parser
except Exception:
    date_parser = None


class EmailService:
    """
    Service class for handling email notifications.
    """

    # Keep a reference if you want to access later via EmailService.mail
    mail: Optional[Mail] = None

    @staticmethod
    def init_mail(app) -> Mail:
        """Initialize Flask-Mail with the app and return the Mail instance."""
        app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
        app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
        app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
        app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
        app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
        app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

        # Dev-friendly flags
        app.config['MAIL_SUPPRESS_SEND'] = os.getenv('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
        app.config['MAIL_DEBUG'] = os.getenv('MAIL_DEBUG', 'False').lower() == 'true'

        mail = Mail(app)
        EmailService.mail = mail
        return mail

    @staticmethod
    def is_email_configured() -> bool:
        """Check if email is properly configured (ignores SUPPRESS_SEND)."""
        required_vars = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_DEFAULT_SENDER']
        return all(os.getenv(var) for var in required_vars)

    @staticmethod
    def send_task_created_notification(mail: Mail, user_email: str, task_data: Dict) -> bool:
        """
        Send email notification when a new task is created.

        Args:
            mail: Flask-Mail instance
            user_email: Email address to send notification to
            task_data: Dictionary containing task information
        """
        logger = getattr(current_app, "logger", None)
        if logger:
            logger.info(f"[EmailService] Attempting to send email to: {user_email}")
            logger.info(f"[EmailService] Configured: {EmailService.is_email_configured()}, "
                        f"SUPPRESS_SEND={current_app.config.get('MAIL_SUPPRESS_SEND')}")

        if current_app.config.get('MAIL_SUPPRESS_SEND', False):
            if logger:
                logger.warning("[EmailService] MAIL_SUPPRESS_SEND=True → skipping actual send.")
            return True  # Treat as “sent” for local dev

        if not EmailService.is_email_configured():
            if logger:
                logger.warning("[EmailService] Email not configured - skipping notification.")
            return False

        try:
            subject = f"New Task Created: {task_data.get('title', 'Untitled Task')}"

            # Build HTML
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">
                         New Task Created
                    </h2>

                    <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #1e40af;">{task_data.get('title', 'Untitled Task')}</h3>

                        <div style="margin: 15px 0;">
                            <strong>Description:</strong><br>
                            <p style="margin: 5px 0; padding: 10px; background-color: white; border-radius: 4px;">
                                {task_data.get('description', 'No description provided')}
                            </p>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                            <div>
                                <strong>Priority:</strong><br>
                                <span style="background-color: {EmailService._get_priority_color(task_data.get('priority', 'medium'))};
                                           color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                    {task_data.get('priority', 'medium').upper()}
                                </span>
                            </div>

                            <div>
                                <strong>Category:</strong><br>
                                <span style="background-color: #6b7280; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                    {task_data.get('category', 'general').upper()}
                                </span>
                            </div>
                        </div>

                        {f'''
                        <div style="margin: 15px 0;">
                            <strong>Deadline:</strong><br>
                            <span style="color: #dc2626; font-weight: bold;">
                                📅 {EmailService._format_deadline(task_data.get('deadline'))}
                            </span>
                        </div>
                        ''' if task_data.get('deadline') else ''}

                        {f'''
                        <div style="margin: 15px 0;">
                            <strong>Subtasks:</strong><br>
                            <ul style="margin: 5px 0; padding-left: 20px;">
                                {"".join([f"<li>{subtask}</li>" for subtask in task_data.get('subtasks', [])])}
                            </ul>
                        </div>
                        ''' if task_data.get('subtasks') else ''}

                        <div style="margin: 15px 0; padding: 10px; background-color: #dbeafe; border-radius: 4px;">
                            <small style="color: #1e40af;">
                                ✨ Created on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                                {' | 🤖 Generated with AI' if task_data.get('ai_generated') else ' | 📝 Created manually'}
                            </small>
                        </div>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <p style="color: #6b7280; font-size: 14px;">
                            This notification was sent from your GenAI Task Manager.<br>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text fallback
            deadline_text = ""
            if task_data.get('deadline'):
                deadline_text = f"Deadline: {EmailService._format_deadline(task_data.get('deadline'))}"

            subtasks_text = ""
            if task_data.get('subtasks'):
                subtasks_list = "\n".join([f"- {subtask}" for subtask in task_data.get('subtasks', [])])
                subtasks_text = f"Subtasks:\n{subtasks_list}"

            ai_text = ' | Generated with AI' if task_data.get('ai_generated') else ' | Created manually'

            text_body = f"""
New Task Created: {task_data.get('title', 'Untitled Task')}

Description: {task_data.get('description', 'No description provided')}
Priority: {task_data.get('priority', 'medium').upper()}
Category: {task_data.get('category', 'general').upper()}
{deadline_text}

{subtasks_text}

Created on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}{ai_text}

---
This notification was sent from your GenAI Task Manager.
            """.strip()

            msg = Message(
                subject=subject,
                recipients=[user_email],
                html=html_body,
                body=text_body
            )

            mail.send(msg)
            if logger:
                logger.info(f"[EmailService] Task creation email sent to {user_email}")
            return True

        except Exception as e:
            if logger:
                logger.error(f"[EmailService] Failed to send task creation email: {e}", exc_info=True)
            else:
                print(f"Failed to send task creation email: {e}")
            return False

    # -----------------------
    # Helpers
    # -----------------------

    @staticmethod
    def _get_priority_color(priority: str) -> str:
        """Get color for priority badge."""
        colors = {
            'urgent': '#dc2626',  # red
            'high':   '#ea580c',  # orange
            'medium': '#2563eb',  # blue
            'low':    '#16a34a',  # green
        }
        return colors.get((priority or '').lower(), '#6b7280')  # default gray

    @staticmethod
    def _format_deadline(deadline: Optional[object]) -> str:
        """
        Format deadline for display. Supports:
        - datetime
        - ISO strings
        - other strings (returned as-is)
        """
        if not deadline:
            return ''

        # Already a datetime
        if isinstance(deadline, datetime):
            return deadline.strftime('%B %d, %Y at %I:%M %p')

        # Probably a string
        s = str(deadline)
        # Handle common ISO format, including 'Z'
        try:
            if 'T' in s or s.endswith('Z'):
                try:
                    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
                except Exception:
                    # Fallback to dateutil if available
                    if date_parser is not None:
                        dt = date_parser.parse(s)
                    else:
                        return s
                return dt.strftime('%B %d, %Y at %I:%M %p')
            # Try flexible parsing (e.g., "22-08-2025 9 PM")
            if date_parser is not None:
                dt = date_parser.parse(s, dayfirst=True)
                return dt.strftime('%B %d, %Y at %I:%M %p')
            return s
        except Exception:
            return s

    @staticmethod
    def send_test_email(mail: Mail, user_email: str) -> Tuple[bool, str]:
        """Send a test email to verify configuration."""
        if current_app.config.get('MAIL_SUPPRESS_SEND', False):
            return True, "MAIL_SUPPRESS_SEND is True – test considered sent (no email dispatched)."

        if not EmailService.is_email_configured():
            return False, "Email not configured. Please set MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER."

        try:
            msg = Message(
                subject="GenAI Task Manager - Test Email",
                recipients=[user_email],
                body="This is a test email from your GenAI Task Manager. Email notifications are working correctly!"
            )
            mail.send(msg)
            return True, "Test email sent successfully"
        except Exception as e:
            return False, f"Failed to send test email: {e}"
