from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from runtime.api.app.models import AlignmentRequest, ActivateSkillRequest, CreateSkillRequest, FeedbackRequest, ParkSkillRequest, ResumeSkillRequest, SkillEventRequest


def register_skill_tools(
    mcp: FastMCP,
    *,
    service_getter: Callable[[], Any],
    default_session_id: Callable[[str], str],
    default_user_id: Callable[[str], str],
    skill_detail: Callable[[str, int], dict[str, object]],
    session_contexts: dict[str, dict[str, str]],
) -> None:
    @mcp.tool(name="route_skill_request")
    def route_skill_request(
        prompt: str,
        complexity: str = "",
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        _sid = default_session_id(session_id)
        return service_getter().repository.route_request(
            prompt,
            complexity or None,
            session_id=_sid,
            user_id=default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            client_type=client_type,
        ).model_dump()

    @mcp.tool(name="load_skill_context")
    def load_skill_context(skill_id: str, gate_level: int = 1) -> dict[str, object]:
        return skill_detail(skill_id, gate_level)

    @mcp.tool(name="activate_skill")
    def activate_skill(
        skill_id: str,
        gate_level: int = 1,
        prompt: str = "",
        activation_reason: str = "",
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        _sid = default_session_id(session_id)
        payload = ActivateSkillRequest(
            session_id=_sid,
            user_id=default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            client_type=client_type,  # type: ignore[arg-type]
            gate_level=gate_level,
            prompt=prompt,
            activation_reason=activation_reason,
        )
        return service_getter().repository.activate_skill(skill_id, payload)

    @mcp.tool(name="manage_skill_session")
    def manage_skill_session(
        action: str,
        session_id: str = "",
        user_id: str = "",
        skill_id: str = "",
        gate_level: int = 1,
        note: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
        context_user_id: str = "",
        context_client_type: str = "",
        context_model: str = "",
    ) -> dict[str, object] | list[dict[str, object]]:
        _sid = default_session_id(session_id)
        _uid = default_user_id(user_id, _sid=_sid)
        svc = service_getter().repository

        if action == "get_active":
            result = svc.get_active_skill(_sid, user_id=_uid)
            if not result:
                raise ValueError("No active skill for this session")
            return result
        if action == "park":
            payload = ParkSkillRequest(
                session_id=_sid,
                user_id=_uid,
                project_id=project_id,
                client_type=client_type,  # type: ignore[arg-type]
                gate_level=gate_level,
                note=note,
            )
            return svc.park_skill(skill_id, payload)
        if action == "resume":
            payload = ResumeSkillRequest(session_id=_sid, user_id=_uid)
            resumed = svc.resume_skill(skill_id, payload)
            if not resumed:
                raise ValueError(f"No parked skill found for {skill_id}")
            return resumed
        if action == "list_parking":
            return svc.list_parking_lot(_sid, user_id=_uid)  # type: ignore[return-value]
        if action == "set_context":
            existing = session_contexts.get(_sid, {})
            if context_user_id:
                existing["user_id"] = context_user_id
            if context_client_type:
                existing["client_type"] = context_client_type
            if context_model:
                existing["model"] = context_model
            session_contexts[_sid] = existing
            return {"status": "context-set", "session_id": _sid, **existing}
        if action == "get_context":
            stored = session_contexts.get(_sid, {})
            return {"session_id": _sid, **stored}
        raise ValueError(f"Unknown action: {action!r}. Valid: get_active, park, resume, list_parking, set_context, get_context")

    @mcp.tool(name="create_skill")
    def create_skill(
        skill_id: str,
        display_name: str,
        description: str,
        purpose: str = "",
        use_when: str = "",
        do_not_use_when: str = "",
        personality: str = "",
        standards: str = "",
        handoffs: str = "",
    ) -> dict[str, object]:
        payload = CreateSkillRequest(
            skill_id=skill_id,
            display_name=display_name,
            description=description,
            purpose=purpose,
            use_when=use_when,
            do_not_use_when=do_not_use_when,
            personality=personality,
            standards=standards,
            handoffs=handoffs,
        )
        return service_getter().repository.upsert_skill(payload)

    @mcp.tool(name="record_skill_outcome")
    def record_skill_outcome(
        type: str,
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        skill_id: str = "",
        event_type: str = "",
        summary: str = "",
        activation_id: str = "",
        status: str = "info",
        payload_json: str = "{}",
        prompt: str = "",
        response_excerpt: str = "",
        gate_level: int | None = None,
        note: str = "",
        rating: str = "",
        work_item_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        _sid = default_session_id(session_id)
        _uid = default_user_id(user_id, _sid=_sid)

        if type == "event":
            try:
                payload_data = json.loads(payload_json or "{}")
            except json.JSONDecodeError as error:
                raise ValueError("payload_json must be valid JSON") from error
            evt = SkillEventRequest(
                session_id=_sid,
                user_id=_uid,
                project_id=project_id,
                activation_id=activation_id,
                skill_id=skill_id,
                event_type=event_type,
                status=status,
                summary=summary,
                payload=payload_data,
            )
            return service_getter().repository.record_skill_event(evt)
        if type == "alignment":
            aln = AlignmentRequest(
                session_id=_sid,
                user_id=_uid,
                project_id=project_id,
                skill_id=skill_id,
                prompt=prompt,
                response_excerpt=response_excerpt,
                gate_level=gate_level,
                note=note,
            )
            return service_getter().repository.score_response_alignment(aln)
        if type == "feedback":
            fb = FeedbackRequest(
                session_id=_sid,
                user_id=_uid,
                project_id=project_id,
                client_type=client_type,  # type: ignore[arg-type]
                skill_id=skill_id,
                rating=rating,  # type: ignore[arg-type]
                prompt=prompt,
                response_excerpt=response_excerpt,
                note=note,
                work_item_id=work_item_id,
            )
            return service_getter().repository.record_feedback(fb)
        raise ValueError(f"Unknown type: {type!r}. Valid: event, alignment, feedback")