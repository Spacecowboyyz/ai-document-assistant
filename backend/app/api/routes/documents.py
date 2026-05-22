from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user, get_document_service
from app.models.user import User
from app.schemas.document import DeleteResponse, DocumentInfo, UploadResponse
from app.services.document_service import DocumentService

router = APIRouter(tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    return await service.ingest_upload(file, current_user.id)


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents(
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> list[DocumentInfo]:
    return await service.list_documents(current_user.id)


@router.delete("/documents/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    service: DocumentService = Depends(get_document_service),
    current_user: User = Depends(get_current_user),
) -> DeleteResponse:
    return await service.delete_document(doc_id, current_user.id)
