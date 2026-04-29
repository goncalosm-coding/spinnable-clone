from langchain.tools import tool
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.core.config import settings

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a given address with a subject and body."""
    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to,
        subject=subject,
        plain_text_content=body
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
        return f"Email sent to {to}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"