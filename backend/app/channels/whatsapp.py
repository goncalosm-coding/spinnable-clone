from twilio.rest import Client
from app.core.config import settings

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to: str, body: str):
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:+{to}" if not to.startswith("+") else f"whatsapp:{to}"
    twilio_client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        to=to
    )

def parse_incoming_whatsapp(form_data: dict) -> dict:
    raw_from = form_data.get("From", "").replace("whatsapp:", "")
    return {
        "from": raw_from,  # keeps the + prefix e.g. +351924269207
        "body": form_data.get("Body", ""),
        "message_sid": form_data.get("MessageSid", ""),
    }