from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import supabase

router = APIRouter(prefix="/integrations", tags=["integrations"])


class GoogleAuthorizeRequest(BaseModel):
    worker_id: str
    tenant_id: str
    user_id: str
    permissions: list[str]


class GoogleAuthorizeResponse(BaseModel):
    authorization_url: str


SCOPE_MAP = {
    "gmail_read": "https://www.googleapis.com/auth/gmail.readonly",
    "gmail_send": "https://www.googleapis.com/auth/gmail.send",
    "calendar_read": "https://www.googleapis.com/auth/calendar.readonly",
    "calendar_write": "https://www.googleapis.com/auth/calendar.events",
}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_state(payload: dict) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_json)
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}"


def _verify_state(state: str) -> dict:
    try:
        payload_b64, signature_b64 = state.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state format.") from exc

    expected_signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(_b64url_encode(expected_signature), signature_b64):
        raise HTTPException(status_code=400, detail="Invalid OAuth state signature.")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=400, detail="Invalid OAuth state payload.") from exc

    issued_at = payload.get("iat")
    if not isinstance(issued_at, int):
        raise HTTPException(status_code=400, detail="Invalid OAuth state timestamp.")
    if datetime.now(timezone.utc).timestamp() - issued_at > 900:
        raise HTTPException(status_code=400, detail="OAuth state expired. Try again.")

    return payload


def _resolve_permissions_from_scopes(scopes: list[str]) -> list[str]:
    permissions: list[str] = []
    scope_set = set(scopes)
    for permission, scope in SCOPE_MAP.items():
        if scope in scope_set:
            permissions.append(permission)
    return sorted(permissions)


@router.post("/google/authorize", response_model=GoogleAuthorizeResponse)
async def authorize_google(req: GoogleAuthorizeRequest):
    if (
        not settings.GOOGLE_CLIENT_ID
        or not settings.GOOGLE_CLIENT_SECRET
        or not settings.GOOGLE_REDIRECT_URI
    ):
        raise HTTPException(
            status_code=400,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI.",
        )

    unique_permissions = sorted(set(req.permissions))
    scopes = sorted({SCOPE_MAP[p] for p in unique_permissions if p in SCOPE_MAP})
    if not scopes:
        raise HTTPException(status_code=400, detail="No Google-scoped permissions requested.")

    state = _sign_state(
        {
            "tenant_id": req.tenant_id,
            "worker_id": req.worker_id,
            "user_id": req.user_id,
            "permissions": unique_permissions,
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
    )

    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "scope": " ".join(scopes),
            "state": state,
        }
    )

    return {
        "authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
    }


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth denied: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state.")

    state_payload = _verify_state(state)

    token_payload = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_response.status_code >= 400:
            raise HTTPException(status_code=400, detail="Failed exchanging OAuth code for token.")
        token_data = token_response.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google OAuth response missing access_token.")

        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        email = None
        if userinfo_response.status_code < 400:
            email = userinfo_response.json().get("email")

    scopes = str(token_data.get("scope", "")).split()
    granted_permissions = _resolve_permissions_from_scopes(scopes)
    expires_in = int(token_data.get("expires_in") or 3600)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
    existing = (
        supabase.table("oauth_connections")
        .select("refresh_token")
        .eq("tenant_id", state_payload["tenant_id"])
        .eq("user_id", state_payload["user_id"])
        .eq("provider", "google")
        .limit(1)
        .execute()
    )
    existing_refresh_token = (
        existing.data[0].get("refresh_token") if existing.data and existing.data[0] else None
    )

    upsert_payload = {
        "tenant_id": state_payload["tenant_id"],
        "user_id": state_payload["user_id"],
        "provider": "google",
        "connected_email": email,
        "scopes": scopes,
        "permissions": granted_permissions,
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token") or existing_refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    supabase.table("oauth_connections").upsert(
        upsert_payload,
        on_conflict="tenant_id,user_id,provider",
    ).execute()

    if settings.GOOGLE_POST_AUTH_REDIRECT:
        query = urlencode(
            {
                "oauth": "success",
                "provider": "google",
                "worker_id": state_payload["worker_id"],
            }
        )
        return RedirectResponse(f"{settings.GOOGLE_POST_AUTH_REDIRECT}?{query}")

    return HTMLResponse(
        "<html><body><h3>Google connected successfully.</h3><p>You can close this tab and return to chat.</p></body></html>"
    )


class GoogleStatusResponse(BaseModel):
    connected: bool
    granted_permissions: list[str]
    missing_permissions: list[str]
    connected_email: str | None = None


@router.get("/google/status", response_model=GoogleStatusResponse)
async def google_status(
    tenant_id: str,
    user_id: str,
    permissions: list[str] = Query(default=[]),
):
    result = (
        supabase.table("oauth_connections")
        .select("permissions, connected_email")
        .eq("tenant_id", tenant_id)
        .eq("user_id", user_id)
        .eq("provider", "google")
        .limit(1)
        .execute()
    )

    row = result.data[0] if result.data else None
    granted = set(row.get("permissions", []) if row else [])
    requested = sorted(set(permissions))
    missing = [permission for permission in requested if permission not in granted]

    return {
        "connected": len(missing) == 0 and len(requested) > 0,
        "granted_permissions": sorted(granted),
        "missing_permissions": missing,
        "connected_email": row.get("connected_email") if row else None,
    }
