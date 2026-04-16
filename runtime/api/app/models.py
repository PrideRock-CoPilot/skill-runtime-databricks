from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


Complexity = Literal["simple", "standard", "deep", "expert"]
FeedbackRating = Literal["correct", "wrong"]
WorkItemStage = Literal["backlog", "discovery", "design", "build", "review", "done"]
SprintStatus = Literal["planning", "active", "completed"]
ClientType = Literal["genie-code", "ide", "web", "api"]
ProjectVisibility = Literal["private", "shared"]

_COMPLEXITY_ALIASES = {
    "simple": "simple",
    "low": "simple",
    "small": "simple",
    "trivial": "simple",
    "standard": "standard",
    "medium": "standard",
    "moderate": "standard",
    "normal": "standard",
    "default": "standard",
    "deep": "deep",
    "high": "deep",
    "complex": "deep",
    "advanced": "deep",
    "expert": "expert",
    "very-high": "expert",
    "strategic": "expert",
}


def normalize_complexity_label(value: str | None) -> Complexity | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^a-z]+", "-", value.strip().lower()).strip("-")
    if not cleaned:
        return None
    normalized = _COMPLEXITY_ALIASES.get(cleaned)
    return normalized if normalized is not None else None


class SkillSummary(BaseModel):
    skill_id: str
    slug: str
    name: str
    display_name: str
    description: str
    packet_level: str
    source_dir: str
    search_score: float = 0


class SkillBundle(BaseModel):
    bundle_id: str
    skill_id: str
    gate_level: int
    gate_name: str
    title: str
    content: str
    source_file: str
    sort_order: int


class SkillDetailResponse(BaseModel):
    skill: SkillSummary
    requested_gate: int
    loaded_gates: list[int]
    bundles: list[SkillBundle]


class RouteMatch(BaseModel):
    skill_id: str
    display_name: str
    description: str
    search_score: float


RouteAction = Literal["activate", "auto-build", "trivial-bypass"]


class RouteResponse(BaseModel):
    prompt: str
    complexity: Complexity
    recommended_gate: int
    matches: list[RouteMatch]
    action: RouteAction = "activate"
    next_step: str = ""
    build_skill_id: str = ""
    work_item_id: str = ""
    project_id: str = ""


class RouteRequest(BaseModel):
    prompt: str = Field(min_length=3)
    complexity: Complexity | None = None
    session_id: str = ""
    user_id: str = ""
    project_id: str = ""
    client_type: ClientType = "web"

    @field_validator("complexity", mode="before")
    @classmethod
    def normalize_complexity(cls, value: object) -> Complexity | None:
        if value is None:
            return None
        if isinstance(value, str):
            return normalize_complexity_label(value)
        return None


class ParkSkillRequest(BaseModel):
    session_id: str
    user_id: str = ""
    project_id: str = ""
    client_type: ClientType = "web"
    gate_level: int = Field(ge=0, le=4)
    note: str = ""


class ResumeSkillRequest(BaseModel):
    session_id: str
    user_id: str = ""


class CreateSkillRequest(BaseModel):
    skill_id: str = Field(min_length=2, pattern=r"^[a-z0-9][a-z0-9-]*$")
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=10)
    purpose: str = ""
    use_when: str = ""
    do_not_use_when: str = ""
    personality: str = ""
    standards: str = ""
    handoffs: str = ""


MemoryScope = Literal["enterprise", "user", "project"]


class StoreMemoryRequest(BaseModel):
    scope: MemoryScope
    subject: str = Field(min_length=2, description="Short title or key for the memory")
    content: str = Field(min_length=3, description="The memory content")
    category: str = Field(default="note", description="Tag: requirement, decision, assumption, constraint, question, handoff, preference, lesson, convention, note")
    project_id: str = Field(default="", description="Required when scope is 'project'")
    skill_id: str = ""
    tags: str = Field(default="", description="Comma-separated tags for search")
    status: str = Field(default="", description="Lifecycle: open, provisional, confirmed, superseded, rejected")
    importance: int = Field(default=0, ge=0, le=5, description="Relative importance. Use 1-5, or 0 to auto-derive.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in this memory. Use 0.0-1.0, or 0 to auto-derive.")
    source: str = Field(default="", description="Origin: user, worker, system, inferred, imported")
    owner: str = Field(default="", description="Who owns the fact or decision: end-user, worker, shared, system")
    decision_scope: str = Field(default="", description="Business, design, technical, delivery, policy, or other")
    pinned: bool = Field(default=False, description="Keep this memory near the top during browse and recall")
    supersedes_memory_id: str = Field(default="", description="Optional memory_id that this memory replaces")
    expires_at: str = Field(default="", description="Optional ISO timestamp for time-bounded memory")


class UpdateMemoryRequest(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None
    importance: Optional[int] = Field(default=None, ge=1, le=5)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Optional[str] = None
    owner: Optional[str] = None
    decision_scope: Optional[str] = None
    pinned: Optional[bool] = None
    supersedes_memory_id: Optional[str] = None
    expires_at: Optional[str] = None


class MemoryRecord(BaseModel):
    memory_id: str
    scope: MemoryScope
    user_id: str
    project_id: str
    category: str
    subject: str
    content: str
    skill_id: str
    session_id: str
    tags: str
    status: str = ""
    importance: int = 0
    confidence: float = 0.0
    source: str = ""
    owner: str = ""
    decision_scope: str = ""
    pinned: bool = False
    supersedes_memory_id: str = ""
    expires_at: str = ""
    last_accessed_at: str = ""
    access_count: int = 0
    relevance_score: float = 0.0
    created_at: str
    updated_at: str
    archived: bool = False


class TemplateRecord(BaseModel):
    template_id: str
    project_id: str
    user_id: str
    name: str
    category: str
    description: str
    original_file_name: str
    stored_relative_path: str
    file_extension: str
    mime_type: str
    size_bytes: int
    created_at: str
    updated_at: str
    archived: bool = False


class GeneratedDocumentRecord(BaseModel):
    document_id: str
    template_id: str
    project_id: str
    user_id: str
    name: str
    description: str
    file_name: str
    stored_relative_path: str
    file_extension: str
    mime_type: str
    size_bytes: int
    source_template_name: str
    created_at: str
    updated_at: str
    archived: bool = False


class CreateGeneratedDocumentRequest(BaseModel):
    user_id: str = ""
    name: str = Field(min_length=2, description="Name for the generated working copy")
    description: str = ""


class ParkedSkillRecord(BaseModel):
    parking_id: str
    session_id: str
    user_id: str
    project_id: str
    client_type: str
    skill_id: str
    display_name: str
    gate_level: int
    status: str
    note: str
    parked_at: str
    resumed_at: str = ""


class FeedbackRequest(BaseModel):
    session_id: str
    user_id: str = ""
    project_id: str = ""
    client_type: ClientType = "web"
    skill_id: str
    rating: FeedbackRating
    prompt: str
    response_excerpt: str = ""
    note: str = ""
    work_item_id: str = ""


class ProjectRecord(BaseModel):
    project_id: str
    user_id: str
    name: str
    summary: str
    owner_name: str
    stage: str
    visibility: ProjectVisibility
    updated_at: str


class WorkItemRecord(BaseModel):
    work_item_id: str
    project_id: str
    user_id: str
    title: str
    summary: str
    stage: WorkItemStage
    owner_skill_id: str
    owner_display_name: str
    priority: str
    updated_at: str


class CreateProjectRequest(BaseModel):
    user_id: str
    name: str = Field(min_length=3)
    summary: str = ""
    owner_name: str = ""
    visibility: ProjectVisibility = "private"
    stage: str = "active"


class CreateWorkItemRequest(BaseModel):
    project_id: str
    user_id: str = ""
    title: str = Field(min_length=3)
    summary: str = ""
    stage: WorkItemStage = "backlog"
    owner_skill_id: str = ""
    owner_display_name: str = "Unassigned"
    priority: str = "medium"


class UpdateWorkItemRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    stage: Optional[WorkItemStage] = None
    owner_skill_id: Optional[str] = None
    owner_display_name: Optional[str] = None
    priority: Optional[str] = None


class CreateSprintRequest(BaseModel):
    project_id: str
    name: str = Field(min_length=2)
    status: SprintStatus = "planning"


class SprintRecord(BaseModel):
    sprint_id: str
    project_id: str
    user_id: str
    name: str
    status: SprintStatus
    created_at: str


class AddCommentRequest(BaseModel):
    entity_type: str = Field(description="Type: 'work_item', 'project', 'sprint'")
    entity_id: str
    body: str = Field(min_length=1)


class ActivateSkillRequest(BaseModel):
    session_id: str
    user_id: str = ""
    project_id: str = ""
    client_type: ClientType = "web"
    gate_level: int = Field(ge=0, le=4)
    prompt: str = ""
    activation_reason: str = ""


class ActiveSkillRecord(BaseModel):
    activation_id: str
    session_id: str
    user_id: str
    project_id: str
    client_type: str
    skill_id: str
    display_name: str
    gate_level: int
    status: str
    route_prompt: str
    activation_reason: str
    activated_at: str
    deactivated_at: str = ""


class SkillEventRequest(BaseModel):
    session_id: str
    user_id: str = ""
    project_id: str = ""
    activation_id: str = ""
    skill_id: str = ""
    event_type: str
    status: str = "info"
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SkillEventRecord(BaseModel):
    event_id: str
    activation_id: str
    session_id: str
    user_id: str
    project_id: str
    skill_id: str
    event_type: str
    status: str
    summary: str
    payload_json: str
    created_at: str


class AlignmentRequest(BaseModel):
    session_id: str
    user_id: str = ""
    project_id: str = ""
    skill_id: str = ""
    prompt: str
    response_excerpt: str
    gate_level: int | None = None
    note: str = ""


class AlignmentRecord(BaseModel):
    alignment_id: str
    activation_id: str
    session_id: str
    user_id: str
    project_id: str
    skill_id: str
    display_name: str
    gate_level: int
    score: int
    status: str
    summary: str
    checks_json: str
    created_at: str


class SessionStoryStep(BaseModel):
    title: str
    detail: str
    time: str = ""


class SessionStory(BaseModel):
    headline: str
    current_step: str
    next_step: str
    active_worker: str
    hiring_in_progress: bool = False
    timeline: list[SessionStoryStep] = Field(default_factory=list)


class SessionRecord(BaseModel):
    session_id: str
    user_id: str
    project_id: str
    project_name: str = ""
    client_type: str
    status: str
    top_skill_id: str = ""
    active_skill_id: str = ""
    last_used_at: str
    last_route_prompt: str = ""
    route_count: int = 0
    event_count: int = 0
    history_scope: Literal["project", "workspace"] = "workspace"
    retention_days: int | None = None


class SessionHistoryEntry(BaseModel):
    entry_id: str
    entry_type: str
    title: str
    detail: str
    created_at: str
    skill_id: str = ""


class SessionHistoryResponse(BaseModel):
    session: SessionRecord
    timeline: list[SessionHistoryEntry] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    user_id: str
    projects: list[ProjectRecord]
    user_sessions: list[SessionRecord] = Field(default_factory=list)
    work_items: list[WorkItemRecord]
    parking_lot: list[ParkedSkillRecord]
    active_skill: ActiveSkillRecord | None = None
    recent_events: list[SkillEventRecord] = Field(default_factory=list)
    latest_alignment: AlignmentRecord | None = None
    session_story: SessionStory | None = None
