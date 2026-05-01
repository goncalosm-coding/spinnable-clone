from contextvars import ContextVar
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import httpx
from langchain.tools import tool

from app.core.config import settings
from app.core.database import supabase


AGENT_CONTEXT: ContextVar[dict[str, str] | None] = ContextVar("agent_context", default=None)


def _refresh_google_access_token(refresh_token: str) -> dict:
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20.0,
    )
    response.raise_for_status()
    return response.json()


def _get_connection():
    context = AGENT_CONTEXT.get()
    if not context:
        return None, "Missing agent runtime context."

    result = (
        supabase.table("oauth_connections")
        .select("access_token, refresh_token, expires_at")
        .eq("tenant_id", context["tenant_id"])
        .eq("user_id", context["user_id"])
        .eq("provider", "google")
        .limit(1)
        .execute()
    )
    if not result.data:
        return None, "No Google account connected for this user yet."

    connection = result.data[0]
    expires_at = connection.get("expires_at")
    refresh_token = connection.get("refresh_token")

    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_dt <= datetime.now(timezone.utc) and refresh_token:
                refreshed = _refresh_google_access_token(refresh_token)
                connection["access_token"] = refreshed.get("access_token")
                new_expires = datetime.now(timezone.utc).timestamp() + int(
                    refreshed.get("expires_in", 3600)
                )
                expires_iso = datetime.fromtimestamp(new_expires, tz=timezone.utc).isoformat()
                connection["expires_at"] = expires_iso
                supabase.table("oauth_connections").update(
                    {
                        "access_token": connection["access_token"],
                        "expires_at": expires_iso,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                ).eq("tenant_id", context["tenant_id"]).eq("user_id", context["user_id"]).eq(
                    "provider", "google"
                ).execute()
        except Exception:
            # If parsing/refresh fails we still try using the current token.
            pass

    return connection, None


@tool
def read_latest_email() -> str:
    """Read the latest email in the user's Gmail inbox."""
    connection, error = _get_connection()
    if error:
        return error

    access_token = connection.get("access_token") if connection else None
    if not access_token:
        return "Google is connected but access token is unavailable. Please reconnect Google."

    headers = {"Authorization": f"Bearer {access_token}"}
    list_resp = httpx.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults=1&labelIds=INBOX",
        headers=headers,
        timeout=20.0,
    )
    if list_resp.status_code >= 400:
        return f"Failed to read inbox list: {list_resp.text}"

    messages = list_resp.json().get("messages", [])
    if not messages:
        return "No emails found in inbox."

    message_id = messages[0]["id"]
    detail_resp = httpx.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}?format=metadata",
        headers=headers,
        timeout=20.0,
    )
    if detail_resp.status_code >= 400:
        return f"Failed to read latest email: {detail_resp.text}"

    payload = detail_resp.json().get("payload", {})
    headers_list = payload.get("headers", [])
    header_map = {h.get("name", "").lower(): h.get("value", "") for h in headers_list}

    sender = header_map.get("from", "Unknown sender")
    subject = header_map.get("subject", "(No subject)")
    date_str = header_map.get("date", "")
    received = date_str
    if date_str:
        try:
            received = parsedate_to_datetime(date_str).isoformat()
        except Exception:
            received = date_str
    snippet = detail_resp.json().get("snippet", "")

    return (
        "Latest inbox email:\n"
        f"- From: {sender}\n"
        f"- Subject: {subject}\n"
        f"- Received: {received}\n"
        f"- Snippet: {snippet}"
    )
