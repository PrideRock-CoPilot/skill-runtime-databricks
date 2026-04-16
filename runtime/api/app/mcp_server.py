from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

from runtime.api.app.models import (
    ActivateSkillRequest,
    AddCommentRequest,
    AlignmentRequest,
    CreateProjectRequest,
    CreateSkillRequest,
    CreateSprintRequest,
    CreateWorkItemRequest,
    FeedbackRequest,
    ParkSkillRequest,
    ResumeSkillRequest,
    SkillDetailResponse,
    SkillEventRequest,
    StoreMemoryRequest,
    UpdateMemoryRequest,
    UpdateWorkItemRequest,
)
from runtime.api.app.runtime_service import get_runtime_service


def _service():
    return get_runtime_service()


# Per-session identity context store ----------------------------------------
_session_contexts: dict[str, dict[str, str]] = {}


def _default_session_id(session_id: str = "") -> str:
    return session_id or _service().settings.default_session_id


def _default_user_id(user_id: str = "", *, _sid: str = "") -> str:
    if user_id:
        return user_id
    if _sid:
        stored = _session_contexts.get(_sid, {})
        if stored.get("user_id"):
            return stored["user_id"]
    return _service().settings.default_user_id


def _public_hosts() -> tuple[list[str], list[str]]:
    hosts = [
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
    ]
    origins = [
        "http://127.0.0.1:*",
        "http://localhost:*",
    ]
    for candidate in (_service().settings.databricks_host, _service().settings.databricks_app_url):
        if not candidate:
            continue
        parsed = urlparse(candidate)
        hostname = parsed.netloc or parsed.path
        if not hostname:
            continue
        if hostname not in hosts:
            hosts.append(hostname)
        if candidate not in origins:
            origins.append(candidate)
    return hosts, origins


def _transport_security() -> TransportSecuritySettings:
    strict_transport = os.getenv("SKILL_RUNTIME_MCP_STRICT_TRANSPORT", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not strict_transport:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=["*"],
            allowed_origins=["*"],
        )

    hosts, origins = _public_hosts()
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


@asynccontextmanager
async def mcp_lifespan(_: FastMCP):
    _service()
    yield


def _skill_detail(skill_id: str, gate_level: int) -> dict[str, object]:
    service = _service()
    skill = service.repository.get_skill(skill_id)
    if not skill:
        raise ValueError(f"Unknown skill: {skill_id}")
    bundles = service.repository.load_skill_bundles(skill_id, gate_level)
    response = SkillDetailResponse(
        skill=skill,
        requested_gate=gate_level,
        loaded_gates=sorted({bundle["gate_level"] for bundle in bundles}),
        bundles=bundles,
    )
    return response.model_dump()


def _register_tools(mcp: FastMCP) -> FastMCP:  # noqa: C901
    # ── 1 ──────────────────────────────────────────────────────────────────
    @mcp.tool(name="route_skill_request")
    def route_skill_request(
        prompt: str,
        complexity: str = "",
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        """Route a request to the best matching skill and return action directives.

        Also searches the registry — no separate search call needed.
        action values: "activate" | "auto-build" | "trivial-bypass"
        Follow `next_step` as a directive:
        - activate → call load_skill_context then activate_skill
        - auto-build → activate build_skill_id, call create_skill, then activate it
        - trivial-bypass → answer directly
        """
        _sid = _default_session_id(session_id)
        return _service().repository.route_request(
            prompt,
            complexity or None,
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            client_type=client_type,
        ).model_dump()

    # ── 2 ──────────────────────────────────────────────────────────────────
    @mcp.tool(name="load_skill_context")
    def load_skill_context(skill_id: str, gate_level: int = 1) -> dict[str, object]:
        """Load the gated skill bundles for one worker packet."""
        return _skill_detail(skill_id, gate_level)

    # ── 3 ──────────────────────────────────────────────────────────────────
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
        """Set the active worker contract for the current session.

        After activation, answer within the worker's identity, scope, and rules.
        Call record_skill_outcome(type="alignment") after substantial responses.
        """
        _sid = _default_session_id(session_id)
        payload = ActivateSkillRequest(
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            client_type=client_type,  # type: ignore[arg-type]
            gate_level=gate_level,
            prompt=prompt,
            activation_reason=activation_reason,
        )
        return _service().repository.activate_skill(skill_id, payload)

    # ── 4 ──────────────────────────────────────────────────────────────────
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
        """Session and parking-lot management for active skills.

        action:
        - "get_active"       — return the currently active worker
        - "park"             — park skill_id (with optional note)
        - "resume"           — resume a parked skill_id
        - "list_parking"     — list parked workers for this session
        - "set_context"      — store context_user_id/context_client_type/context_model on the session
        - "get_context"      — return stored session context
        """
        _sid = _default_session_id(session_id)
        _uid = _default_user_id(user_id, _sid=_sid)
        svc = _service().repository

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
            existing = _session_contexts.get(_sid, {})
            if context_user_id:
                existing["user_id"] = context_user_id
            if context_client_type:
                existing["client_type"] = context_client_type
            if context_model:
                existing["model"] = context_model
            _session_contexts[_sid] = existing
            return {"status": "context-set", "session_id": _sid, **existing}

        if action == "get_context":
            stored = _session_contexts.get(_sid, {})
            return {"session_id": _sid, **stored}

        raise ValueError(f"Unknown action: {action!r}. Valid: get_active, park, resume, list_parking, set_context, get_context")

    # ── 5 ──────────────────────────────────────────────────────────────────
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
        """Register or update a skill in the runtime registry.

        skill_id must be lowercase kebab-case (e.g. 'flowershop-owner').
        When route_skill_request returns action='auto-build', call this to
        create the missing skill, then activate it and answer the request.
        """
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
        return _service().repository.upsert_skill(payload)

    # ── 6 ──────────────────────────────────────────────────────────────────
    @mcp.tool(name="record_skill_outcome")
    def record_skill_outcome(
        type: str,
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        skill_id: str = "",
        # event fields
        event_type: str = "",
        summary: str = "",
        activation_id: str = "",
        status: str = "info",
        payload_json: str = "{}",
        # alignment fields
        prompt: str = "",
        response_excerpt: str = "",
        gate_level: int | None = None,
        note: str = "",
        # feedback fields
        rating: str = "",
        work_item_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        """Record a skill event, alignment score, or feedback — all in one tool.

        type:
        - "event"      — write a handoff, retry, or execution note
          (requires: event_type, summary; optional: status, payload_json)
        - "alignment"  — score whether the response follows the worker contract
          (requires: prompt, response_excerpt)
        - "feedback"   — capture end-user thumbs-up / thumbs-down
          (requires: skill_id, rating, prompt)
        """
        _sid = _default_session_id(session_id)
        _uid = _default_user_id(user_id, _sid=_sid)

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
            return _service().repository.record_skill_event(evt)

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
            return _service().repository.score_response_alignment(aln)

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
            return _service().repository.record_feedback(fb)

        raise ValueError(f"Unknown type: {type!r}. Valid: event, alignment, feedback")

    # ── 7 ──────────────────────────────────────────────────────────────────
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
        """Store a memory at enterprise, user, or project scope.

        scope: "enterprise" (all users) | "user" (private) | "project" (shared on project).
        category: requirement, decision, assumption, constraint, question,
          handoff, preference, lesson, convention, note.
        project_id required when scope="project".
        """
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
        _sid = _default_session_id(session_id)
        return _service().repository.store_memory(
            payload,
            user_id=_default_user_id(user_id, _sid=_sid),
            session_id=_sid,
        )

    # ── 8 ──────────────────────────────────────────────────────────────────
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
        """Search or browse memories. Also retrieves memory/guardrail triggers.

        - query="" with triggers_only=False → list memories (browse mode)
        - query="something" → ranked text search across subject/content/tags
        - triggers_only=True → return guardrail and recall triggers (category/client_type filter via category param)

        Replaces: recall_memories, list_memories, list_memory_triggers.
        """
        if triggers_only:
            return _service().repository.list_memory_triggers(
                category=category,
                client_type="any",
                limit=limit,
            )
        if query:
            return _service().repository.recall_memories(
                query=query,
                scope=scope,
                user_id=_default_user_id(user_id),
                project_id=project_id,
                category=category,
                limit=limit,
            )
        return _service().repository.list_memories(
            scope=scope,
            user_id=_default_user_id(user_id),
            project_id=project_id,
            category=category,
            limit=limit,
        )

    # ── 9 ──────────────────────────────────────────────────────────────────
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
        """Update or archive an existing memory.

        Pass only the fields you want to change.
        Set archive=True to soft-delete (excluded from recall; auditable).
        Only the author can update or archive a memory.
        """
        if archive:
            return _service().repository.archive_memory(memory_id, user_id=_default_user_id(user_id))
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
        return _service().repository.update_memory(memory_id, payload, user_id=_default_user_id(user_id))

    # ── 10 ─────────────────────────────────────────────────────────────────
    @mcp.tool(name="get_dashboard")
    def get_dashboard(session_id: str = "", user_id: str = "", include_shared: bool = True) -> dict[str, Any]:
        """Return the full runtime view: projects, board, active skill, events, alignment, session story.

        Also covers runtime health — check the 'health' key for storage / config status.
        """
        resolved_session_id = _default_session_id(session_id)
        resolved_user_id = _default_user_id(user_id, _sid=resolved_session_id)
        return {
            "health": _service().health(),
            "user_id": resolved_user_id,
            "projects": _service().repository.list_projects(resolved_user_id, include_shared=include_shared),
            "user_sessions": _service().repository.list_user_sessions(user_id=resolved_user_id),
            "work_items": _service().repository.list_work_items(user_id=resolved_user_id),
            "parking_lot": _service().repository.list_parking_lot(resolved_session_id, user_id=resolved_user_id),
            "active_skill": _service().repository.get_active_skill(resolved_session_id, user_id=resolved_user_id),
            "recent_events": _service().repository.recent_events(resolved_user_id, session_id=resolved_session_id),
            "latest_alignment": _service().repository.latest_alignment(resolved_user_id, session_id=resolved_session_id),
            "session_story": _service().repository.build_session_story(resolved_session_id, resolved_user_id),
        }

    # ── 11 ─────────────────────────────────────────────────────────────────
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
        """Create or list projects.

        action:
        - "list"    — list visible projects for the user
        - "create"  — create a new project (requires: name)
        """
        _uid = _default_user_id(user_id)
        if action == "list":
            return _service().repository.list_projects(_uid, include_shared=include_shared)  # type: ignore[return-value]
        if action == "create":
            payload = CreateProjectRequest(
                user_id=_uid,
                name=name,
                summary=summary,
                owner_name=owner_name,
                visibility=visibility,  # type: ignore[arg-type]
                stage=stage,
            )
            return _service().repository.create_project(payload)
        raise ValueError(f"Unknown action: {action!r}. Valid: list, create")

    # ── 12 ─────────────────────────────────────────────────────────────────
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
        # comment fields
        entity_type: str = "work_item",
        body: str = "",
        skill_id: str = "",
    ) -> dict[str, object] | list[dict[str, object]]:
        """Create, update, list work items; add or list comments; view stage history.

        action:
        - "list"          — list work items (filter by project_id or user_id)
        - "create"        — create a work item (requires: project_id, title)
        - "update"        — update a work item (requires: work_item_id)
        - "transitions"   — show stage-change history (requires: work_item_id)
        - "add_comment"   — add a comment (requires: entity_type, work_item_id, body)
        - "list_comments" — list comments (requires: entity_type, work_item_id)
        """
        _uid = _default_user_id(user_id)
        svc = _service().repository

        if action == "list":
            return svc.list_work_items(project_id or None, user_id=_uid)  # type: ignore[return-value]

        if action == "create":
            payload = CreateWorkItemRequest(
                project_id=project_id,
                user_id=_uid,
                title=title,
                summary=summary,
                stage=stage,  # type: ignore[arg-type]
                owner_skill_id=owner_skill_id,
                owner_display_name=owner_display_name,
                priority=priority,
            )
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
            comment_payload = AddCommentRequest(entity_type=entity_type, entity_id=work_item_id, body=body)
            return svc.add_comment(comment_payload, user_id=_uid, skill_id=skill_id)

        if action == "list_comments":
            return svc.list_comments(entity_type, work_item_id)  # type: ignore[return-value]

        raise ValueError(f"Unknown action: {action!r}. Valid: list, create, update, transitions, add_comment, list_comments")

    # ── 13 ─────────────────────────────────────────────────────────────────
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
        """Create, list, update, and manage sprint membership.

        action:
        - "list"          — list sprints (filter by project_id)
        - "create"        — create a sprint (requires: project_id, name)
        - "update_status" — update a sprint's status (requires: sprint_id, status)
        - "add_item"      — add a work item to a sprint (requires: sprint_id, work_item_id)
        - "remove_item"   — remove a work item from a sprint (requires: sprint_id, work_item_id)
        """
        _uid = _default_user_id(user_id)
        svc = _service().repository

        if action == "list":
            return svc.list_sprints(project_id=project_id, user_id=_uid)  # type: ignore[return-value]

        if action == "create":
            payload = CreateSprintRequest(project_id=project_id, name=name, status=status)  # type: ignore[arg-type]
            return svc.create_sprint(payload, user_id=_uid)

        if action == "update_status":
            return svc.update_sprint_status(sprint_id, status)

        if action == "add_item":
            return svc.add_to_sprint(sprint_id, work_item_id)

        if action == "remove_item":
            return svc.remove_from_sprint(sprint_id, work_item_id)

        raise ValueError(f"Unknown action: {action!r}. Valid: list, create, update_status, add_item, remove_item")

    # ── Resources ──────────────────────────────────────────────────────────
    @mcp.resource("skill://registry", mime_type="application/json", name="skill-registry")
    def skill_registry_resource() -> str:
        return json.dumps(_service().repository.list_skills(), indent=2)

    @mcp.resource("skill://activation-contract", mime_type="application/json", name="activation-contract")
    def activation_contract_resource() -> str:
        contract = {
            "required_flow": [
                "route_skill_request → returns action directive",
                "follow action: activate → load_skill_context + activate_skill",
                "follow action: auto-build → activate build_skill_id, create_skill, activate it",
                "follow action: trivial-bypass → answer directly",
                "answer within the active worker contract",
                "record_skill_outcome(type='event') for handoffs or retries",
                "record_skill_outcome(type='alignment') after substantial responses",
            ],
            "directive_fields": {
                "action": "activate | auto-build | trivial-bypass",
                "next_step": "explicit instruction — follow as a directive",
                "build_skill_id": "skill to activate when action is auto-build",
            },
            "goal": "The server decides what to do. The model follows the action and next_step directives.",
        }
        return json.dumps(contract, indent=2)

    @mcp.resource("skill://memory-triggers", mime_type="application/json", name="memory-triggers")
    def memory_triggers_resource() -> str:
        return json.dumps(_service().repository.list_memory_triggers(limit=50), indent=2)

    @mcp.resource("skill://chat-execution-contract", mime_type="application/json", name="chat-execution-contract")
    def chat_execution_contract_resource() -> str:
        contract = {
            "required_sections_for_non_trivial_turns": [
                "## Todo",
                "## Skill Activation",
                "## Security Warning (only when relevant)",
                "## Next Step or Result",
            ],
            "format_rules": [
                "Use Markdown headers instead of plain prose blobs.",
                "Announce newly activated skills by name and reason.",
                "Keep todo items visible and short.",
                "When a guarded write may hit policy, warn before attempting it.",
                "Do not suggest bypassing corporate security or transport controls.",
            ],
            "databricks_guardrail": "Before writing files, tables, or governed storage in Databricks-like environments, surface a security warning and stop if the platform denies the action.",
        }
        return json.dumps(contract, indent=2)

    @mcp.resource("skill://{skill_id}/gate/{gate_level}", mime_type="application/json", name="skill-gate")
    def skill_gate_resource(skill_id: str, gate_level: str) -> str:
        return json.dumps(_skill_detail(skill_id, int(gate_level)), indent=2)

    return mcp


def create_mcp_server(
    *,
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str = "/mcp",
    stateless_http: bool = False,
) -> FastMCP:
    instructions = (
        "This server is the centralized company skill runtime for Genie Code and internal IDEs. "
        "Before answering non-trivial requests, route the request, load the gate bundle, activate the skill, "
        "then keep events and alignment visible. Use the chat execution contract with Todo, Skill Activation, "
        "and Security Warning sections when relevant. Treat Markdown and identity folders as authoring sources of truth, "
        "and treat this MCP server as the runtime control plane."
    )
    server = FastMCP(
        name="Skill Runtime MCP",
        instructions=instructions,
        host=host or os.getenv("SKILL_RUNTIME_MCP_HOST", "127.0.0.1"),
        port=port or int(os.getenv("SKILL_RUNTIME_MCP_PORT", "8001")),
        streamable_http_path=streamable_http_path,
        json_response=True,
        stateless_http=stateless_http,
        log_level=os.getenv("SKILL_RUNTIME_MCP_LOG_LEVEL", "INFO"),
        transport_security=_transport_security(),
        lifespan=mcp_lifespan,
    )
    return _register_tools(server)


def main() -> None:
    transport = os.getenv("SKILL_RUNTIME_MCP_TRANSPORT", "stdio")
    server = create_mcp_server(
        streamable_http_path=os.getenv("SKILL_RUNTIME_MCP_HTTP_PATH", "/mcp"),
        stateless_http=os.getenv("SKILL_RUNTIME_MCP_STATELESS", "false").lower() in {"1", "true", "yes", "on"},
    )
    server.run(transport=transport)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
