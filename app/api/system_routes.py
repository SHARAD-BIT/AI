from fastapi import APIRouter

from app.services.system_service import clear_application_data


router = APIRouter(prefix="/system", tags=["System"])


@router.post("/clear-database")
def clear_database():
    return clear_application_data()
