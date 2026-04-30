from twilio.rest import Client
from app.core.config import settings

twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_whatsapp_message(to: str, body: str):
    # Normalize: strip everything, rebuild cleanly
    to = to.strip().replace(" ", "")
    to = to.replace("whatsapp:", "")
    to = to.lstrip("+")
    to = f"whatsapp:+{to}"
    print(f"DEBUG sending to: '{to}'")
    twilio_client.messages.create(
        body=body,
        from_=settings.TWILIO_WHATSAPP_NUMBER,
        to=to
    )

def parse_incoming_whatsapp(form_data: dict) -> dict:
    raw_from = form_data.get("From", "").replace("whatsapp:", "").strip().replace(" ", "")
    print(f"DEBUG parsed from: '{raw_from}'")
    return {
        "from": raw_from,
        "body": form_data.get("Body", ""),
        "message_sid": form_data.get("MessageSid", ""),
    }
