from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import repository
from ..models import SessionHistoryResponse, SessionRecord

router = APIRouter()


@router.get("/api/sessions", response_model=list[SessionRecord])
def list_sessions(user_id: str = "", project_id: str = "", limit: int = 40) -> list[dict[str, object]]:
    return repository().list_user_sessions(user_id=user_id, project_id=project_id, limit=limit)


@router.get("/api/sessions/{session_id}/history", response_model=SessionHistoryResponse)
def get_session_history(session_id: str, user_id: str = "", limit: int = 60) -> dict[str, object]:
    history = repository().get_session_history(session_id, user_id=user_id, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail="Session history not found")
    return history


@router.get("/api/sessions/{session_id}/parking-lot")
def list_parking_lot(session_id: str, user_id: str = "") -> list[dict[str, object]]:
    return repository().list_parking_lot(session_id, user_id=user_id)