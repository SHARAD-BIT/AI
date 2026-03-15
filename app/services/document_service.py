import os

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.services.document_repository import get_document_by_id


def get_document_file(document_id: int) -> FileResponse:
    document = get_document_by_id(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    stored_path = document.get("stored_path")
    if not stored_path or not os.path.exists(stored_path):
        raise HTTPException(status_code=404, detail="Stored document file not found")

    response = FileResponse(stored_path, media_type="application/pdf")
    safe_filename = str(document.get("original_filename") or "document.pdf").replace('"', "")
    response.headers["Content-Disposition"] = f'inline; filename="{safe_filename}"'
    return response
