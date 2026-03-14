from fastapi import APIRouter
from pydantic import BaseModel

from app.services.query_service import answer_query

router = APIRouter(prefix="/match", tags=["Matching"])


class MatchRequest(BaseModel):
    query: str


@router.post("/")
def match(request: MatchRequest):
    results = answer_query(request.query)

    return {
        "matches": results
    }
