from __future__ import annotations

import asyncio
import base64
import binascii
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..databricks_auth import get_forwarded_token
from ..dependencies import repository, runtime_service
from ..models import DashboardResponse

router = APIRouter()


def _base64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _decode_jwt_claims(token: str) -> dict[str, object]:
    if not token or "." not in token:
        return {}
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    try:
        payload = _base64url_decode(parts[1]).decode("utf-8")
        data = json.loads(payload)
        return data if isinstance(data, dict) else {}
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
        return {}


def _dashboard_snapshot(session_id: str, user_id: str, include_shared: bool = True) -> dict[str, object]:
    resolved_user_id = user_id or runtime_service().settings.default_user_id
    response = DashboardResponse(
        user_id=resolved_user_id,
        projects=repository().list_projects(user_id=resolved_user_id, include_shared=include_shared),
        user_sessions=repository().list_user_sessions(user_id=resolved_user_id),
        work_items=repository().list_work_items(user_id=resolved_user_id),
        parking_lot=repository().list_parking_lot(session_id, user_id=resolved_user_id),
        active_skill=repository().get_active_skill(session_id, user_id=resolved_user_id),
        recent_events=repository().recent_events(resolved_user_id, session_id=session_id),
        latest_alignment=repository().latest_alignment(resolved_user_id, session_id=session_id),
        session_story=repository().build_session_story(session_id, resolved_user_id),
    )
    return response.model_dump()


@router.get("/api/health")
def health() -> dict[str, object]:
    return runtime_service().health()


@router.post("/api/runtime/compile")
def compile_runtime() -> dict[str, int]:
    return runtime_service().compiler.compile()


@router.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(
    session_id: str = "local-dev-session",
    user_id: str = "",
    include_shared: bool = True,
) -> DashboardResponse:
    payload = _dashboard_snapshot(session_id=session_id, user_id=user_id, include_shared=include_shared)
    return DashboardResponse.model_validate(payload)


@router.get("/api/dashboard/stream")
async def dashboard_stream(
    session_id: str = "local-dev-session",
    user_id: str = "",
    include_shared: bool = True,
) -> StreamingResponse:
    async def event_generator():
        while True:
            payload = _dashboard_snapshot(session_id=session_id, user_id=user_id, include_shared=include_shared)
            message = json.dumps(payload)
            yield f"event: dashboard\ndata: {message}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/auth/context")
def auth_context() -> dict[str, object]:
    token = get_forwarded_token()
    claims = _decode_jwt_claims(token)
    email = str(claims.get("email") or claims.get("upn") or claims.get("preferred_username") or "").strip()
    display_name = str(claims.get("name") or claims.get("given_name") or "").strip()
    subject = str(claims.get("sub") or "").strip()
    fallback_user = runtime_service().settings.default_user_id
    return {
        "authenticated": bool(token),
        "provider": "databricks-app" if token else "local",
        "email": email or fallback_user,
        "display_name": display_name or email or fallback_user,
        "subject": subject,
        "workspace_host": runtime_service().settings.databricks_host,
    }