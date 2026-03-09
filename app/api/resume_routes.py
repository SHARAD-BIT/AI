from fastapi import APIRouter, File, UploadFile

from app.services.resume_service import process_resume

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    result = await process_resume(file)
    return result
