from fastapi import Request
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from app.core.config import settings

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to: str, body: str):
    """Send a WhatsApp message via Twilio."""
    twilio_client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        to=f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
    )

def parse_incoming_whatsapp(form_data: dict) -> dict:
    """Extract relevant fields from Twilio's webhook payload."""
    return {
        "from": form_data.get("From", "").replace("whatsapp:", ""),
        "body": form_data.get("Body", ""),
        "message_sid": form_data.get("MessageSid", ""),
    }