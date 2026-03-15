from fastapi import APIRouter

from app.services.document_service import get_document_file


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{document_id}/file")
def open_document_file(document_id: int):
    return get_document_file(document_id)
