from fastapi import APIRouter
from pydantic import BaseModel

from app.services.matching_service import match_resumes_with_uploaded_tender

router = APIRouter(prefix="/match", tags=["Matching"])


class MatchRequest(BaseModel):
    query: str


@router.post("/")
def match(request: MatchRequest):
    results = match_resumes_with_uploaded_tender(request.query)

    return {
        "matches": results
    }