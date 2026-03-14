from fastapi import APIRouter, UploadFile, File
from app.services.tender_service import process_tender

router = APIRouter(prefix="/tenders", tags=["Tenders"])

@router.post("/upload")
async def upload_tender(file: UploadFile = File(...)):
    return await process_tender(file)
