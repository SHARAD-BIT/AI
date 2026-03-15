from fastapi import APIRouter
from pydantic import BaseModel

from app.services.query_service import answer_query

router = APIRouter(prefix="/match", tags=["Matching"])


class MatchRequest(BaseModel):
    query: str
    tender_document_id: int | None = None
    resume_document_ids: list[int] | None = None
    restrict_to_active_uploads: bool = False


@router.post("/")
def match(request: MatchRequest):
    results = answer_query(
        request.query,
        tender_document_id=request.tender_document_id,
        resume_document_ids=request.resume_document_ids,
        restrict_to_active_uploads=request.restrict_to_active_uploads,
    )

    return {
        "matches": results
    }
