from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .databricks_auth import DatabricksAuthMiddleware
from .mcp_server import create_mcp_server
from .models import (
    ActivateSkillRequest,
    AlignmentRequest,
    CreateGeneratedDocumentRequest,
    CreateProjectRequest,
    CreateWorkItemRequest,
    DashboardResponse,
    FeedbackRequest,
    ParkSkillRequest,
    ResumeSkillRequest,
    RouteRequest,
    SessionHistoryResponse,
    SessionRecord,
    SkillDetailResponse,
    SkillEventRequest,
    UpdateWorkItemRequest,
)
from .repository import RuntimeRepository
from .runtime_service import RuntimeService, get_runtime_service

_mcp_server = create_mcp_server(
    streamable_http_path="/",
    stateless_http=os.getenv("SKILL_RUNTIME_MCP_STATELESS", "false").lower() in {"1", "true", "yes", "on"},
)


class SinglePageApp(StaticFiles):
    async def get_response(self, path: str, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        if response.status_code != 404:
            return response
        return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = get_runtime_service()
    app.state.runtime_service = service
    app.state.settings = service.settings
    app.state.compiler = service.compiler
    app.state.repository = service.repository
    async with _mcp_server.session_manager.run():
        yield


app = FastAPI(title="Skill Runtime API", version="0.2.0", lifespan=lifespan)
service = get_runtime_service()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(service.settings.allowed_web_origins),
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DatabricksAuthMiddleware)
app.mount(
    "/mcp",
    _mcp_server.streamable_http_app(),
)

def runtime_service() -> RuntimeService:
    return getattr(app.state, "runtime_service", get_runtime_service())  # type: ignore[no-any-return]


def repository() -> RuntimeRepository:
    return runtime_service().repository


@app.get("/api/health")
def health() -> dict[str, object]:
    return runtime_service().health()


@app.post("/api/runtime/compile")
def compile_runtime() -> dict[str, int]:
    return runtime_service().compiler.compile()


@app.get("/api/skills")
def list_skills(query: str = "") -> list[dict[str, object]]:
    return repository().list_skills(query)


@app.get("/api/skills/{skill_id}", response_model=SkillDetailResponse)
def get_skill(skill_id: str, gate: int = 1) -> SkillDetailResponse:
    skill = repository().get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    bundles = repository().load_skill_bundles(skill_id, gate)
    return SkillDetailResponse(
        skill=skill,
        requested_gate=gate,
        loaded_gates=sorted({bundle["gate_level"] for bundle in bundles}),
        bundles=bundles,
    )


@app.post("/api/router/route")
def route_prompt(payload: RouteRequest) -> dict[str, object]:
    return repository().route_request(
        payload.prompt,
        payload.complexity,
        session_id=payload.session_id or None,
        user_id=payload.user_id,
        project_id=payload.project_id,
        client_type=payload.client_type,
    ).model_dump()


@app.get("/api/projects")
def list_projects(user_id: str = "", include_shared: bool = True) -> list[dict[str, object]]:
    return repository().list_projects(user_id=user_id, include_shared=include_shared)


@app.post("/api/projects")
def create_project(payload: CreateProjectRequest) -> dict[str, object]:
    return repository().create_project(payload)


@app.get("/api/work-items")
def list_work_items(project_id: str = "", user_id: str = "") -> list[dict[str, object]]:
    return repository().list_work_items(project_id or None, user_id=user_id)


@app.post("/api/work-items")
def create_work_item(payload: CreateWorkItemRequest) -> dict[str, object]:
    return repository().create_work_item(payload)


@app.patch("/api/work-items/{work_item_id}")
def update_work_item(work_item_id: str, payload: UpdateWorkItemRequest) -> dict[str, object]:
    updated = repository().update_work_item(work_item_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Work item not found")
    return updated


@app.get("/api/projects/{project_id}/templates")
def list_templates(project_id: str, user_id: str = "") -> list[dict[str, object]]:
    try:
        return repository().list_templates(project_id, user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@app.post("/api/projects/{project_id}/templates")
async def upload_template(
    project_id: str,
    user_id: str = Form(""),
    name: str = Form(""),
    category: str = Form("general"),
    description: str = Form(""),
    file: UploadFile = File(...),
) -> dict[str, object]:
    try:
        payload = await file.read()
        return repository().upload_template(
            project_id=project_id,
            user_id=user_id,
            name=name,
            category=category,
            description=description,
            file_name=file.filename or "",
            content_type=file.content_type or "",
            payload=payload,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        await file.close()


@app.get("/api/projects/{project_id}/template-documents")
def list_template_documents(project_id: str, user_id: str = "") -> list[dict[str, object]]:
    try:
        return repository().list_generated_documents(project_id, user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@app.post("/api/projects/{project_id}/templates/{template_id}/generate")
def create_template_document(
    project_id: str,
    template_id: str,
    payload: CreateGeneratedDocumentRequest,
) -> dict[str, object]:
    try:
        return repository().create_generated_document(project_id, template_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/templates/{template_id}/download")
def download_template(template_id: str, user_id: str = "") -> FileResponse:
    try:
        file_info = repository().get_template_file(template_id, user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if not file_info:
        raise HTTPException(status_code=404, detail="Template not found")
    return FileResponse(
        path=file_info["path"],
        media_type=str(file_info["mime_type"]),
        filename=str(file_info["file_name"]),
    )


@app.get("/api/template-documents/{document_id}/download")
def download_template_document(document_id: str, user_id: str = "") -> FileResponse:
    try:
        file_info = repository().get_generated_document_file(document_id, user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if not file_info:
        raise HTTPException(status_code=404, detail="Generated document not found")
    return FileResponse(
        path=file_info["path"],
        media_type=str(file_info["mime_type"]),
        filename=str(file_info["file_name"]),
    )


@app.get("/api/memory/triggers")
def list_memory_triggers(category: str = "", client_type: str = "", limit: int = 20) -> list[dict[str, object]]:
    return repository().list_memory_triggers(category=category, client_type=client_type, limit=limit)


@app.get("/api/sessions", response_model=list[SessionRecord])
def list_sessions(user_id: str = "", project_id: str = "", limit: int = 40) -> list[dict[str, object]]:
    return repository().list_user_sessions(user_id=user_id, project_id=project_id, limit=limit)


@app.get("/api/sessions/{session_id}/history", response_model=SessionHistoryResponse)
def get_session_history(session_id: str, user_id: str = "", limit: int = 60) -> dict[str, object]:
    history = repository().get_session_history(session_id, user_id=user_id, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail="Session history not found")
    return history


@app.get("/api/sessions/{session_id}/parking-lot")
def list_parking_lot(session_id: str, user_id: str = "") -> list[dict[str, object]]:
    return repository().list_parking_lot(session_id, user_id=user_id)


@app.post("/api/skills/{skill_id}/park")
def park_skill(skill_id: str, payload: ParkSkillRequest) -> dict[str, object]:
    if not repository().get_skill(skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")
    return repository().park_skill(skill_id, payload)


@app.post("/api/skills/{skill_id}/resume")
def resume_skill(skill_id: str, payload: ResumeSkillRequest) -> dict[str, object]:
    resumed = repository().resume_skill(skill_id, payload)
    if not resumed:
        raise HTTPException(status_code=404, detail="Parked skill not found")
    return resumed


@app.post("/api/skills/{skill_id}/activate")
def activate_skill(skill_id: str, payload: ActivateSkillRequest) -> dict[str, object]:
    try:
        return repository().activate_skill(skill_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/sessions/{session_id}/active-skill")
def get_active_skill(session_id: str, user_id: str = "") -> dict[str, object]:
    active_skill = repository().get_active_skill(session_id, user_id=user_id)
    if not active_skill:
        raise HTTPException(status_code=404, detail="No active skill for this session")
    return active_skill


@app.post("/api/skill-events")
def record_skill_event(payload: SkillEventRequest) -> dict[str, object]:
    return repository().record_skill_event(payload)


@app.post("/api/alignment/score")
def score_alignment(payload: AlignmentRequest) -> dict[str, object]:
    try:
        return repository().score_response_alignment(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/feedback")
def record_feedback(payload: FeedbackRequest) -> dict[str, object]:
    return repository().record_feedback(payload)


@app.get("/api/dashboard", response_model=DashboardResponse)
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


web_dist_dir = service.settings.repo_root / "runtime" / "web" / "dist"
if web_dist_dir.exists():
    app.mount("/", SinglePageApp(directory=str(web_dist_dir), html=True), name="runtime-web")
