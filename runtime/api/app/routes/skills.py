from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import repository
from ..models import ActivateSkillRequest, ParkSkillRequest, ResumeSkillRequest, RouteRequest, SkillDetailResponse

router = APIRouter()


@router.get("/api/skills")
def list_skills(query: str = "") -> list[dict[str, object]]:
    return repository().list_skills(query)


@router.get("/api/skills/{skill_id}", response_model=SkillDetailResponse)
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


@router.post("/api/router/route")
def route_prompt(payload: RouteRequest) -> dict[str, object]:
    return repository().route_request(
        payload.prompt,
        payload.complexity,
        session_id=payload.session_id or None,
        user_id=payload.user_id,
        project_id=payload.project_id,
        client_type=payload.client_type,
    ).model_dump()


@router.post("/api/skills/{skill_id}/park")
def park_skill(skill_id: str, payload: ParkSkillRequest) -> dict[str, object]:
    if not repository().get_skill(skill_id):
        raise HTTPException(status_code=404, detail="Skill not found")
    return repository().park_skill(skill_id, payload)


@router.post("/api/skills/{skill_id}/resume")
def resume_skill(skill_id: str, payload: ResumeSkillRequest) -> dict[str, object]:
    resumed = repository().resume_skill(skill_id, payload)
    if not resumed:
        raise HTTPException(status_code=404, detail="Parked skill not found")
    return resumed


@router.post("/api/skills/{skill_id}/activate")
def activate_skill(skill_id: str, payload: ActivateSkillRequest) -> dict[str, object]:
    try:
        return repository().activate_skill(skill_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/api/sessions/{session_id}/active-skill")
def get_active_skill(session_id: str, user_id: str = "") -> dict[str, object]:
    active_skill = repository().get_active_skill(session_id, user_id=user_id)
    if not active_skill:
        raise HTTPException(status_code=404, detail="No active skill for this session")
    return active_skill