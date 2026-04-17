from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
from dataclasses import dataclass, field

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..databricks_auth import get_forwarded_token
from ..dependencies import repository, runtime_service
from ..models import DashboardResponse

router = APIRouter()

_STREAM_POLL_SECONDS = 2.0
_STREAM_HEARTBEAT_SECONDS = 20.0


@dataclass
class _DashboardStreamState:
    subscribers: set[asyncio.Queue[str]] = field(default_factory=set)
    worker_task: asyncio.Task[None] | None = None
    last_hash: str = ""
    last_emit_at: float = 0.0


_stream_lock = asyncio.Lock()
_stream_states: dict[tuple[str, str, bool], _DashboardStreamState] = {}


def _resolved_user_id(user_id: str) -> str:
    return user_id or runtime_service().settings.default_user_id


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
    resolved_user_id = _resolved_user_id(user_id)
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


async def _broadcast_to_subscribers(key: tuple[str, str, bool], event: str) -> None:
    async with _stream_lock:
        state = _stream_states.get(key)
        if not state:
            return
        subscribers = list(state.subscribers)

    for queue in subscribers:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            continue


async def _run_dashboard_worker(key: tuple[str, str, bool]) -> None:
    session_id, user_id, include_shared = key
    while True:
        async with _stream_lock:
            state = _stream_states.get(key)
            if not state or not state.subscribers:
                _stream_states.pop(key, None)
                return
            last_hash = state.last_hash
            last_emit_at = state.last_emit_at

        payload = _dashboard_snapshot(session_id=session_id, user_id=user_id, include_shared=include_shared)
        message = json.dumps(payload, separators=(",", ":"))
        digest = hashlib.sha1(message.encode("utf-8")).hexdigest()
        now = asyncio.get_running_loop().time()

        event: str | None = None
        if digest != last_hash:
            event = f"event: dashboard\\ndata: {message}\\n\\n"
        elif now - last_emit_at >= _STREAM_HEARTBEAT_SECONDS:
            event = "event: heartbeat\\ndata: {}\\n\\n"

        if event is not None:
            await _broadcast_to_subscribers(key, event)
            async with _stream_lock:
                state = _stream_states.get(key)
                if state:
                    if digest != state.last_hash:
                        state.last_hash = digest
                    state.last_emit_at = now

        await asyncio.sleep(_STREAM_POLL_SECONDS)


async def _subscribe_dashboard_stream(key: tuple[str, str, bool]) -> asyncio.Queue[str]:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=4)
    async with _stream_lock:
        state = _stream_states.get(key)
        if state is None:
            state = _DashboardStreamState()
            _stream_states[key] = state
        state.subscribers.add(queue)
        if state.worker_task is None or state.worker_task.done():
            state.worker_task = asyncio.create_task(_run_dashboard_worker(key))
    return queue


async def _unsubscribe_dashboard_stream(key: tuple[str, str, bool], queue: asyncio.Queue[str]) -> None:
    async with _stream_lock:
        state = _stream_states.get(key)
        if not state:
            return
        state.subscribers.discard(queue)


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
    stream_key = (session_id, _resolved_user_id(user_id), include_shared)
    queue = await _subscribe_dashboard_stream(stream_key)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            await _unsubscribe_dashboard_stream(stream_key, queue)

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