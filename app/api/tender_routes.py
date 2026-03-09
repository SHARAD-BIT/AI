from fastapi import APIRouter
from app.services.matching_service import match_candidates

router = APIRouter(prefix="/tenders", tags=["Tenders"])


@router.get("/match")
def match(query: str):

    results = match_candidates(query)

    return {
        "matches": results
    }