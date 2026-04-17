from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..dependencies import repository
from ..models import AlignmentRequest, FeedbackRequest, SkillEventRequest

router = APIRouter()


@router.post("/api/skill-events")
def record_skill_event(payload: SkillEventRequest) -> dict[str, object]:
    return repository().record_skill_event(payload)


@router.post("/api/alignment/score")
def score_alignment(payload: AlignmentRequest) -> dict[str, object]:
    try:
        return repository().score_response_alignment(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/api/feedback")
def record_feedback(payload: FeedbackRequest) -> dict[str, object]:
    return repository().record_feedback(payload)