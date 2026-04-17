from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from runtime.api.app.models import AddCommentRequest, CreateProjectRequest, CreateSprintRequest, CreateWorkItemRequest, StoreMemoryRequest, UpdateMemoryRequest, UpdateWorkItemRequest


def register_management_tools(
    mcp: FastMCP,
    *,
    service_getter: Callable[[], Any],
    default_session_id: Callable[[str], str],
    default_user_id: Callable[[str], str],
) -> None:
    @mcp.tool(name="store_memory")
    def store_memory(
        scope: str,
        subject: str,
        content: str,
        category: str = "note",
        project_id: str = "",
        skill_id: str = "",
        tags: str = "",
        status: str = "",
        importance: int = 0,
        confidence: float = 0.0,
        source: str = "",
        owner: str = "",
        decision_scope: str = "",
        pinned: bool = False,
        supersedes_memory_id: str = "",
        expires_at: str = "",
        session_id: str = "",
        user_id: str = "",
    ) -> dict[str, object]:
        payload = StoreMemoryRequest(
            scope=scope,  # type: ignore[arg-type]
            subject=subject,
            content=content,
            category=category,
            project_id=project_id,
            skill_id=skill_id,
            tags=tags,
            status=status,
            importance=importance,
            confidence=confidence,
            source=source,
            owner=owner,
            decision_scope=decision_scope,
            pinned=pinned,
            supersedes_memory_id=supersedes_memory_id,
            expires_at=expires_at,
        )
        _sid = default_session_id(session_id)
        return service_getter().repository.store_memory(payload, user_id=default_user_id(user_id, _sid=_sid), session_id=_sid)

    @mcp.tool(name="query_memories")
    def query_memories(
        query: str = "",
        scope: str = "",
        project_id: str = "",
        category: str = "",
        triggers_only: bool = False,
        limit: int = 20,
        user_id: str = "",
    ) -> list[dict[str, object]]:
        if triggers_only:
            return service_getter().repository.list_memory_triggers(category=category, client_type="any", limit=limit)
        if query:
            return service_getter().repository.recall_memories(
                query=query,
                scope=scope,
                user_id=default_user_id(user_id),
                project_id=project_id,
                category=category,
                limit=limit,
            )
        return service_getter().repository.list_memories(
            scope=scope,
            user_id=default_user_id(user_id),
            project_id=project_id,
            category=category,
            limit=limit,
        )

    @mcp.tool(name="update_memory")
    def update_memory(
        memory_id: str,
        subject: str = "",
        content: str = "",
        category: str = "",
        tags: str = "",
        status: str = "",
        importance: int = 0,
        confidence: float = 0.0,
        source: str = "",
        owner: str = "",
        decision_scope: str = "",
        pinned: bool | None = None,
        supersedes_memory_id: str = "",
        expires_at: str = "",
        archive: bool = False,
        user_id: str = "",
    ) -> dict[str, object]:
        if archive:
            return service_getter().repository.archive_memory(memory_id, user_id=default_user_id(user_id))
        payload = UpdateMemoryRequest(
            subject=subject or None,
            content=content or None,
            category=category or None,
            tags=tags or None,
            status=status or None,
            importance=importance if importance > 0 else None,
            confidence=confidence if confidence > 0 else None,
            source=source or None,
            owner=owner or None,
            decision_scope=decision_scope or None,
            pinned=pinned,
            supersedes_memory_id=supersedes_memory_id or None,
            expires_at=expires_at or None,
        )
        return service_getter().repository.update_memory(memory_id, payload, user_id=default_user_id(user_id))

    @mcp.tool(name="get_dashboard")
    def get_dashboard(session_id: str = "", user_id: str = "", include_shared: bool = True) -> dict[str, Any]:
        resolved_session_id = default_session_id(session_id)
        resolved_user_id = default_user_id(user_id, _sid=resolved_session_id)
        service = service_getter()
        return {
            "health": service.health(),
            "user_id": resolved_user_id,
            "projects": service.repository.list_projects(resolved_user_id, include_shared=include_shared),
            "user_sessions": service.repository.list_user_sessions(user_id=resolved_user_id),
            "work_items": service.repository.list_work_items(user_id=resolved_user_id),
            "parking_lot": service.repository.list_parking_lot(resolved_session_id, user_id=resolved_user_id),
            "active_skill": service.repository.get_active_skill(resolved_session_id, user_id=resolved_user_id),
            "recent_events": service.repository.recent_events(resolved_user_id, session_id=resolved_session_id),
            "latest_alignment": service.repository.latest_alignment(resolved_user_id, session_id=resolved_session_id),
            "session_story": service.repository.build_session_story(resolved_session_id, resolved_user_id),
        }

    @mcp.tool(name="manage_project")
    def manage_project(
        action: str,
        user_id: str = "",
        include_shared: bool = True,
        name: str = "",
        summary: str = "",
        owner_name: str = "",
        visibility: str = "private",
        stage: str = "active",
    ) -> dict[str, object] | list[dict[str, object]]:
        _uid = default_user_id(user_id)
        if action == "list":
            return service_getter().repository.list_projects(_uid, include_shared=include_shared)  # type: ignore[return-value]
        if action == "create":
            payload = CreateProjectRequest(user_id=_uid, name=name, summary=summary, owner_name=owner_name, visibility=visibility, stage=stage)  # type: ignore[arg-type]
            return service_getter().repository.create_project(payload)
        raise ValueError(f"Unknown action: {action!r}. Valid: list, create")

    @mcp.tool(name="manage_work_item")
    def manage_work_item(
        action: str,
        project_id: str = "",
        user_id: str = "",
        work_item_id: str = "",
        title: str = "",
        summary: str = "",
        stage: str = "backlog",
        owner_skill_id: str = "",
        owner_display_name: str = "Unassigned",
        priority: str = "medium",
        entity_type: str = "work_item",
        body: str = "",
        skill_id: str = "",
    ) -> dict[str, object] | list[dict[str, object]]:
        _uid = default_user_id(user_id)
        svc = service_getter().repository
        if action == "list":
            return svc.list_work_items(project_id or None, user_id=_uid)  # type: ignore[return-value]
        if action == "create":
            payload = CreateWorkItemRequest(project_id=project_id, user_id=_uid, title=title, summary=summary, stage=stage, owner_skill_id=owner_skill_id, owner_display_name=owner_display_name, priority=priority)  # type: ignore[arg-type]
            return svc.create_work_item(payload)
        if action == "update":
            upd = UpdateWorkItemRequest(
                title=title or None,
                summary=summary or None,
                stage=stage or None,  # type: ignore[arg-type]
                owner_skill_id=owner_skill_id or None,
                owner_display_name=owner_display_name or None,
                priority=priority or None,
            )
            result = svc.update_work_item(work_item_id, upd)
            if not result:
                raise ValueError(f"Unknown work item: {work_item_id}")
            return result
        if action == "transitions":
            return svc.list_transitions(work_item_id)  # type: ignore[return-value]
        if action == "add_comment":
            return svc.add_comment(AddCommentRequest(entity_type=entity_type, entity_id=work_item_id, body=body), user_id=_uid, skill_id=skill_id)
        if action == "list_comments":
            return svc.list_comments(entity_type, work_item_id)  # type: ignore[return-value]
        raise ValueError(f"Unknown action: {action!r}. Valid: list, create, update, transitions, add_comment, list_comments")

    @mcp.tool(name="manage_sprint")
    def manage_sprint(
        action: str,
        project_id: str = "",
        user_id: str = "",
        sprint_id: str = "",
        work_item_id: str = "",
        name: str = "",
        status: str = "planning",
    ) -> dict[str, object] | list[dict[str, object]]:
        _uid = default_user_id(user_id)
        svc = service_getter().repository
        if action == "list":
            return svc.list_sprints(project_id=project_id, user_id=_uid)  # type: ignore[return-value]
        if action == "create":
            return svc.create_sprint(CreateSprintRequest(project_id=project_id, name=name, status=status), user_id=_uid)  # type: ignore[arg-type]
        if action == "update_status":
            return svc.update_sprint_status(sprint_id, status)
        if action == "add_item":
            return svc.add_to_sprint(sprint_id, work_item_id)
        if action == "remove_item":
            return svc.remove_from_sprint(sprint_id, work_item_id)
        raise ValueError(f"Unknown action: {action!r}. Valid: list, create, update_status, add_item, remove_item")