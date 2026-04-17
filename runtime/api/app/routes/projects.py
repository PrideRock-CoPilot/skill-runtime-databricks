from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..dependencies import repository
from ..models import CreateGeneratedDocumentRequest, CreateProjectRequest, CreateWorkItemRequest, UpdateWorkItemRequest

router = APIRouter()


@router.get("/api/projects")
def list_projects(user_id: str = "", include_shared: bool = True) -> list[dict[str, object]]:
    return repository().list_projects(user_id=user_id, include_shared=include_shared)


@router.post("/api/projects")
def create_project(payload: CreateProjectRequest) -> dict[str, object]:
    return repository().create_project(payload)


@router.get("/api/work-items")
def list_work_items(project_id: str = "", user_id: str = "") -> list[dict[str, object]]:
    return repository().list_work_items(project_id or None, user_id=user_id)


@router.post("/api/work-items")
def create_work_item(payload: CreateWorkItemRequest) -> dict[str, object]:
    return repository().create_work_item(payload)


@router.patch("/api/work-items/{work_item_id}")
def update_work_item(work_item_id: str, payload: UpdateWorkItemRequest) -> dict[str, object]:
    updated = repository().update_work_item(work_item_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Work item not found")
    return updated


@router.get("/api/projects/{project_id}/templates")
def list_templates(project_id: str, user_id: str = "") -> list[dict[str, object]]:
    try:
        return repository().list_templates(project_id, user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/api/projects/{project_id}/templates")
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


@router.get("/api/projects/{project_id}/template-documents")
def list_template_documents(project_id: str, user_id: str = "") -> list[dict[str, object]]:
    try:
        return repository().list_generated_documents(project_id, user_id=user_id)
    except ValueError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error


@router.post("/api/projects/{project_id}/templates/{template_id}/generate")
def create_template_document(
    project_id: str,
    template_id: str,
    payload: CreateGeneratedDocumentRequest,
) -> dict[str, object]:
    try:
        return repository().create_generated_document(project_id, template_id, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/api/templates/{template_id}/download")
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


@router.get("/api/template-documents/{document_id}/download")
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