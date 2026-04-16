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


def _register_tools(mcp: FastMCP) -> FastMCP:
    @mcp.tool(name="runtime_health")
    def runtime_health() -> dict[str, object]:
        """Return runtime configuration and storage locations."""
        return _service().health()

    @mcp.tool(name="set_session_context")
    def set_session_context(
        session_id: str,
        user_id: str = "",
        client_type: str = "",
        model: str = "",
    ) -> dict[str, object]:
        """Set identity context for a session.

        Call once at the start of a conversation. Subsequent tool calls that
        include the same session_id automatically inherit user_id, client_type,
        and model — no need to repeat them on every call.

        - session_id: your conversation/thread identifier (required)
        - user_id: who you are
        - client_type: your tool/client (e.g. "genie-code", "copilot", "cursor")
        - model: the LLM model (e.g. "claude-opus-4", "gpt-4o")
        """
        existing = _session_contexts.get(session_id, {})
        if user_id:
            existing["user_id"] = user_id
        if client_type:
            existing["client_type"] = client_type
        if model:
            existing["model"] = model
        _session_contexts[session_id] = existing
        return {"status": "context-set", "session_id": session_id, **existing}

    @mcp.tool(name="get_session_context")
    def get_session_context(session_id: str) -> dict[str, object]:
        """Return the identity context stored for a session."""
        stored = _session_contexts.get(session_id, {})
        return {"session_id": session_id, **stored}

    @mcp.tool(name="search_skills")
    def search_skills(query: str = "") -> list[dict[str, object]]:
        """Search the centralized skill registry by name, description, or use case."""
        return _service().repository.list_skills(query)

    @mcp.tool(name="route_skill_request")
    def route_skill_request(
        prompt: str,
        complexity: str = "",
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        """Route a request to the best matching skill. Returns action directives.

        The response includes:
        - matches: ranked skill candidates with scores
        - complexity: detected task complexity
        - recommended_gate: gate level for the matched skill
        - action: one of "activate", "auto-build", or "trivial-bypass"
        - next_step: explicit instruction for what to do next — follow it as a directive
        - build_skill_id: when action is "auto-build", the skill to activate for building

        Complexity is optional. Canonical values are simple, standard, deep, and
        expert. Common aliases such as low, medium, and high are also accepted.

        Follow the `action` and `next_step` fields:
        - "activate" → call load_skill_context then activate_skill for the recommended skill
        - "auto-build" → activate the build_skill_id to create the missing skill, then activate it
        - "trivial-bypass" → answer directly without activation
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

    @mcp.tool(name="load_skill_context")
    def load_skill_context(skill_id: str, gate_level: int = 1) -> dict[str, object]:
        """Load the gated skill bundles for one worker packet."""
        return _skill_detail(skill_id, gate_level)

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
        """Register a new skill in the runtime registry.

        Use this tool to create skills that the router can discover. The skill
        is immediately available for routing, activation, and context loading.
        The skill_id must be lowercase kebab-case (e.g. 'flowershop-owner').

        When the route response action is 'auto-build', call this tool to
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

    @mcp.tool(name="plan_project_skills")
    def plan_project_skills(prompt: str) -> dict[str, object]:
        """Plan the full set of stakeholder skills needed for a project.

        Given a project description, returns skills grouped by phase
        (discovery → requirements → design → build → review). Each suggestion
        includes a domain-prefixed skill_id, role, phase, and purpose.

        The response tells you which skills already exist and which to create.
        Follow the next_step directive: create discovery-phase skills first
        using create_skill, then activate the domain-owner to start gathering
        requirements. Create later-phase skills as the project progresses.
        """
        return _service().repository.plan_project_skills(prompt)

    # ------------------------------------------------------------------
    # Knowledge memory tools
    # ------------------------------------------------------------------

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

        Scopes:
        - "enterprise": visible to ALL users across ALL projects. Use for
          company-wide conventions, global decisions, org-level lessons learned.
        - "user": private to this user, persists across sessions and projects.
          Use for personal preferences, learned patterns, working notes.
        - "project": visible to all users who share the project. Use for
          requirements, design decisions, phase outcomes, stakeholder notes.

        Categories: requirement, decision, assumption, constraint, question,
        handoff, preference, lesson, convention, note.
        Tags: comma-separated for search (e.g. "ux,mobile,accessibility").
        Status: open, provisional, confirmed, superseded, rejected.
        Importance: 1-5, or 0 to auto-derive from category.
        Confidence: 0.0-1.0, or 0 to auto-derive from status.
        Source: user, worker, system, inferred, imported.
        Owner: end-user, worker, shared, system.
        decision_scope: business, design, technical, delivery, policy, or other.
        Pinned memories rank higher during recall and browsing.
        supersedes_memory_id marks an older memory as replaced.
        project_id is required when scope is "project".
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

    @mcp.tool(name="recall_memories")
    def recall_memories(
        query: str,
        scope: str = "",
        project_id: str = "",
        category: str = "",
        limit: int = 10,
        user_id: str = "",
    ) -> list[dict[str, object]]:
        """Search memories by text relevance across accessible scopes.

        Finds memories where the query matches subject, content, or tags.
        Results are ranked by text match, importance, confidence, status,
        pinning, recency, and prior access. Without a scope filter, searches
        enterprise + user + accessible project memories.

        Use this to recall requirements, decisions, preferences, or any
        previously stored knowledge before starting work.
        """
        return _service().repository.recall_memories(
            query=query,
            scope=scope,
            user_id=_default_user_id(user_id),
            project_id=project_id,
            category=category,
            limit=limit,
        )

    @mcp.tool(name="list_memories")
    def list_memories(
        scope: str = "",
        project_id: str = "",
        category: str = "",
        limit: int = 20,
        user_id: str = "",
    ) -> list[dict[str, object]]:
        """List memories by scope, project, or category.

        Unlike recall_memories, this does not require a search query.
        Use it to browse what memories exist for a project, user, or enterprise.
        Results are sorted by pinning, importance, freshness, and prior access.
        """
        return _service().repository.list_memories(
            scope=scope,
            user_id=_default_user_id(user_id),
            project_id=project_id,
            category=category,
            limit=limit,
        )

    @mcp.tool(name="list_memory_triggers")
    def list_memory_triggers(category: str = "", client_type: str = "", limit: int = 20) -> list[dict[str, object]]:
        """List the runtime's memory and guardrail triggers.

        These triggers describe when the agent should recall memory, store
        memory, supersede outdated memory, or warn about guarded writes.
        """
        resolved_client_type = client_type or "any"
        return _service().repository.list_memory_triggers(
            category=category,
            client_type=resolved_client_type,
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
        user_id: str = "",
    ) -> dict[str, object]:
        """Update an existing memory and its ranking metadata.

        Only the author of the memory can update it.
        Pass only the fields you want to change.
        """
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
        return _service().repository.update_memory(
            memory_id,
            payload,
            user_id=_default_user_id(user_id),
        )

    @mcp.tool(name="archive_memory")
    def archive_memory(
        memory_id: str,
        user_id: str = "",
    ) -> dict[str, object]:
        """Soft-delete a memory. Only the author can archive it.

        Archived memories are excluded from recall and list results
        but remain in storage for audit purposes.
        """
        return _service().repository.archive_memory(
            memory_id,
            user_id=_default_user_id(user_id),
        )

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
        """Set the active worker contract for the current user session.

        After activation, answer within the worker's identity, scope, and rules.
        Call score_response_alignment after producing a substantial response.
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

    @mcp.tool(name="get_active_skill")
    def get_active_skill(session_id: str = "", user_id: str = "") -> dict[str, object]:
        """Return the currently active worker for this user session."""
        _sid = _default_session_id(session_id)
        active_skill = _service().repository.get_active_skill(
            _sid,
            user_id=_default_user_id(user_id, _sid=_sid),
        )
        if not active_skill:
            raise ValueError("No active skill for this session")
        return active_skill

    @mcp.tool(name="list_parking_lot")
    def list_parking_lot(session_id: str = "", user_id: str = "") -> list[dict[str, object]]:
        """List parked workers that can be resumed for this session."""
        _sid = _default_session_id(session_id)
        return _service().repository.list_parking_lot(
            _sid,
            user_id=_default_user_id(user_id, _sid=_sid),
        )

    @mcp.tool(name="park_skill")
    def park_skill(
        skill_id: str,
        gate_level: int = 1,
        note: str = "",
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        """Park a worker so it can be resumed without rediscovery."""
        _sid = _default_session_id(session_id)
        payload = ParkSkillRequest(
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            client_type=client_type,  # type: ignore[arg-type]
            gate_level=gate_level,
            note=note,
        )
        return _service().repository.park_skill(skill_id, payload)

    @mcp.tool(name="resume_skill")
    def resume_skill(skill_id: str, session_id: str = "", user_id: str = "") -> dict[str, object]:
        """Resume a parked worker for this user session."""
        _sid = _default_session_id(session_id)
        payload = ResumeSkillRequest(
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
        )
        resumed = _service().repository.resume_skill(skill_id, payload)
        if not resumed:
            raise ValueError(f"No parked skill found for {skill_id}")
        return resumed

    @mcp.tool(name="record_skill_event")
    def record_skill_event(
        event_type: str,
        summary: str,
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        skill_id: str = "",
        activation_id: str = "",
        status: str = "info",
        payload_json: str = "{}",
    ) -> dict[str, object]:
        """Write a visible skill event such as a handoff, retry, or execution note."""
        try:
            payload_data = json.loads(payload_json or "{}")
        except json.JSONDecodeError as error:
            raise ValueError("payload_json must be valid JSON") from error
        _sid = _default_session_id(session_id)
        payload = SkillEventRequest(
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            activation_id=activation_id,
            skill_id=skill_id,
            event_type=event_type,
            status=status,
            summary=summary,
            payload=payload_data,
        )
        return _service().repository.record_skill_event(payload)

    @mcp.tool(name="score_response_alignment")
    def score_response_alignment(
        prompt: str,
        response_excerpt: str,
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        skill_id: str = "",
        gate_level: int | None = None,
        note: str = "",
    ) -> dict[str, object]:
        """Score whether the response follows the active worker contract.

        Call this after every substantial response. The score and detail are
        returned inline so the user can see alignment quality.
        """
        _sid = _default_session_id(session_id)
        payload = AlignmentRequest(
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            skill_id=skill_id,
            prompt=prompt,
            response_excerpt=response_excerpt,
            gate_level=gate_level,
            note=note,
        )
        return _service().repository.score_response_alignment(payload)

    @mcp.tool(name="record_skill_feedback")
    def record_skill_feedback(
        skill_id: str,
        rating: str,
        prompt: str,
        response_excerpt: str = "",
        note: str = "",
        work_item_id: str = "",
        session_id: str = "",
        user_id: str = "",
        project_id: str = "",
        client_type: str = "genie-code",
    ) -> dict[str, object]:
        """Record end-user feedback tied to a skill attempt."""
        _sid = _default_session_id(session_id)
        payload = FeedbackRequest(
            session_id=_sid,
            user_id=_default_user_id(user_id, _sid=_sid),
            project_id=project_id,
            client_type=client_type,  # type: ignore[arg-type]
            skill_id=skill_id,
            rating=rating,  # type: ignore[arg-type]
            prompt=prompt,
            response_excerpt=response_excerpt,
            note=note,
            work_item_id=work_item_id,
        )
        return _service().repository.record_feedback(payload)

    @mcp.tool(name="list_projects")
    def list_projects(user_id: str = "", include_shared: bool = True) -> list[dict[str, object]]:
        """List the visible company and personal projects for a user."""
        return _service().repository.list_projects(_default_user_id(user_id), include_shared=include_shared)

    @mcp.tool(name="create_project")
    def create_project(
        user_id: str,
        name: str,
        summary: str = "",
        owner_name: str = "",
        visibility: str = "private",
        stage: str = "active",
    ) -> dict[str, object]:
        """Create a private or shared project board lane."""
        payload = CreateProjectRequest(
            user_id=_default_user_id(user_id),
            name=name,
            summary=summary,
            owner_name=owner_name,
            visibility=visibility,  # type: ignore[arg-type]
            stage=stage,
        )
        return _service().repository.create_project(payload)

    @mcp.tool(name="list_work_items")
    def list_work_items(project_id: str = "", user_id: str = "") -> list[dict[str, object]]:
        """List work items for the visible projects or one project."""
        return _service().repository.list_work_items(project_id or None, user_id=_default_user_id(user_id))

    @mcp.tool(name="create_work_item")
    def create_work_item(
        project_id: str,
        title: str,
        summary: str = "",
        stage: str = "backlog",
        owner_skill_id: str = "",
        owner_display_name: str = "Unassigned",
        priority: str = "medium",
        user_id: str = "",
    ) -> dict[str, object]:
        """Create a tracked work item on a project board."""
        payload = CreateWorkItemRequest(
            project_id=project_id,
            user_id=_default_user_id(user_id),
            title=title,
            summary=summary,
            stage=stage,  # type: ignore[arg-type]
            owner_skill_id=owner_skill_id,
            owner_display_name=owner_display_name,
            priority=priority,
        )
        return _service().repository.create_work_item(payload)

    @mcp.tool(name="update_work_item")
    def update_work_item(
        work_item_id: str,
        title: str | None = None,
        summary: str | None = None,
        stage: str | None = None,
        owner_skill_id: str | None = None,
        owner_display_name: str | None = None,
        priority: str | None = None,
    ) -> dict[str, object]:
        """Update stage, ownership, or text for an existing work item."""
        payload = UpdateWorkItemRequest(
            title=title,
            summary=summary,
            stage=stage,  # type: ignore[arg-type]
            owner_skill_id=owner_skill_id,
            owner_display_name=owner_display_name,
            priority=priority,
        )
        updated = _service().repository.update_work_item(work_item_id, payload)
        if not updated:
            raise ValueError(f"Unknown work item: {work_item_id}")
        return updated

    # ------------------------------------------------------------------
    # Sprint management
    # ------------------------------------------------------------------

    @mcp.tool(name="create_sprint")
    def create_sprint(
        project_id: str,
        name: str,
        status: str = "planning",
        user_id: str = "",
    ) -> dict[str, object]:
        """Create a sprint to organize work items into time-boxed iterations.

        Use sprints to plan and track multi-step work. Assign work items to
        a sprint using add_to_sprint. Status can be 'planning', 'active',
        or 'completed'.
        """
        payload = CreateSprintRequest(
            project_id=project_id,
            name=name,
            status=status,  # type: ignore[arg-type]
        )
        return _service().repository.create_sprint(payload, user_id=_default_user_id(user_id))

    @mcp.tool(name="list_sprints")
    def list_sprints(project_id: str = "", user_id: str = "") -> list[dict[str, object]]:
        """List sprints for a project, most recent first."""
        return _service().repository.list_sprints(project_id=project_id, user_id=_default_user_id(user_id))

    @mcp.tool(name="update_sprint_status")
    def update_sprint_status(sprint_id: str, status: str) -> dict[str, object]:
        """Update a sprint's status (planning → active → completed)."""
        return _service().repository.update_sprint_status(sprint_id, status)

    @mcp.tool(name="add_to_sprint")
    def add_to_sprint(sprint_id: str, work_item_id: str) -> dict[str, object]:
        """Assign a work item to a sprint for tracking."""
        return _service().repository.add_to_sprint(sprint_id, work_item_id)

    @mcp.tool(name="remove_from_sprint")
    def remove_from_sprint(sprint_id: str, work_item_id: str) -> dict[str, object]:
        """Remove a work item from a sprint."""
        return _service().repository.remove_from_sprint(sprint_id, work_item_id)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    @mcp.tool(name="add_comment")
    def add_comment(
        entity_type: str,
        entity_id: str,
        body: str,
        skill_id: str = "",
        user_id: str = "",
    ) -> dict[str, object]:
        """Add a comment to a work item, project, or sprint.

        entity_type: 'work_item', 'project', or 'sprint'.
        entity_id: the ID of the entity to comment on.
        Use this to record progress notes, blockers, decisions, or any
        context that should be visible on the board for the end user.
        """
        payload = AddCommentRequest(
            entity_type=entity_type,
            entity_id=entity_id,
            body=body,
        )
        return _service().repository.add_comment(
            payload,
            user_id=_default_user_id(user_id),
            skill_id=skill_id,
        )

    @mcp.tool(name="list_comments")
    def list_comments(entity_type: str, entity_id: str) -> list[dict[str, object]]:
        """List comments on a work item, project, or sprint (oldest first)."""
        return _service().repository.list_comments(entity_type, entity_id)

    # ------------------------------------------------------------------
    # Task transitions (read-only history)
    # ------------------------------------------------------------------

    @mcp.tool(name="list_transitions")
    def list_transitions(work_item_id: str) -> list[dict[str, object]]:
        """Show the stage-change history for a work item.

        Returns each transition with from_stage, to_stage, and timestamp.
        Useful for the end user to see how a task has progressed.
        """
        return _service().repository.list_transitions(work_item_id)

    @mcp.tool(name="list_sessions")
    def list_sessions(user_id: str = "", project_id: str = "", limit: int = 40) -> list[dict[str, object]]:
        """List the end user's connected sessions.

        Project-linked sessions are retained longer. Workspace-only sessions
        are retained for 30 days.
        """
        resolved_user_id = _default_user_id(user_id)
        return _service().repository.list_user_sessions(user_id=resolved_user_id, project_id=project_id, limit=limit)

    @mcp.tool(name="get_session_history")
    def get_session_history(session_id: str, user_id: str = "", limit: int = 60) -> dict[str, object]:
        """Return a unified timeline for one user session."""
        resolved_user_id = _default_user_id(user_id, _sid=session_id)
        history = _service().repository.get_session_history(session_id, user_id=resolved_user_id, limit=limit)
        if not history:
            raise ValueError("Session history not found")
        return history

    @mcp.tool(name="get_dashboard")
    def get_dashboard(session_id: str = "", user_id: str = "", include_shared: bool = True) -> dict[str, Any]:
        """Return the visible project board, active worker, recent events, and latest alignment."""
        resolved_session_id = _default_session_id(session_id)
        resolved_user_id = _default_user_id(user_id, _sid=resolved_session_id)
        return {
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

    @mcp.resource("skill://registry", mime_type="application/json", name="skill-registry")
    def skill_registry_resource() -> str:
        return json.dumps(_service().repository.list_skills(), indent=2)

    @mcp.resource("skill://activation-contract", mime_type="application/json", name="activation-contract")
    def activation_contract_resource() -> str:
        contract = {
            "required_flow": [
                "route_skill_request → returns action directive",
                "follow action: activate → load_skill_context + activate_skill",
                "follow action: auto-build → activate build_skill_id, create skill, activate it",
                "follow action: trivial-bypass → answer directly",
                "answer within the active worker contract",
                "record_skill_event for handoffs or retries",
                "score_response_alignment after substantial responses",
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
