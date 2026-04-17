from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import repository
from ..models import MemoryRecord, StoreMemoryRequest, UpdateMemoryRequest

router = APIRouter()


@router.get("/api/memory/triggers")
def list_memory_triggers(category: str = "", client_type: str = "", limit: int = 20) -> list[dict[str, object]]:
    return repository().list_memory_triggers(category=category, client_type=client_type, limit=limit)


@router.get("/api/memories", response_model=list[MemoryRecord])
def list_memories(
    query: str = "",
    scope: str = "",
    user_id: str = "",
    project_id: str = "",
    category: str = "",
    limit: int = 20,
) -> list[dict[str, object]]:
    normalized_scope = "" if scope == "all" else scope
    normalized_category = "" if category == "all" else category
    if query.strip():
        return repository().recall_memories(
            query=query,
            scope=normalized_scope,
            user_id=user_id,
            project_id=project_id,
            category=normalized_category,
            limit=limit,
        )
    return repository().list_memories(
        scope=normalized_scope,
        user_id=user_id,
        project_id=project_id,
        category=normalized_category,
        limit=limit,
    )


@router.post("/api/memories")
def create_memory(payload: StoreMemoryRequest, user_id: str = "", session_id: str = "") -> dict[str, object]:
    try:
        return repository().store_memory(payload, user_id=user_id, session_id=session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.patch("/api/memories/{memory_id}")
def update_memory(memory_id: str, payload: UpdateMemoryRequest, user_id: str = "") -> dict[str, object]:
    try:
        return repository().update_memory(memory_id, payload, user_id=user_id)
    except ValueError as error:
        message = str(error)
        status_code = 404 if "not found" in message.lower() else 403
        raise HTTPException(status_code=status_code, detail=message) from error


@router.delete("/api/memories/{memory_id}")
def archive_memory(memory_id: str, user_id: str = "") -> dict[str, object]:
    try:
        return repository().archive_memory(memory_id, user_id=user_id)
    except ValueError as error:
        message = str(error)
        status_code = 404 if "not found" in message.lower() else 403
        raise HTTPException(status_code=status_code, detail=message) from error