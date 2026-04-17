from __future__ import annotations

from fastapi import APIRouter

from ..dependencies import repository, runtime_service
from ..models import DashboardResponse

router = APIRouter()


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
    resolved_user_id = user_id or runtime_service().settings.default_user_id
    return DashboardResponse(
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