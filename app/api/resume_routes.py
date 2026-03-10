from fastapi import APIRouter, UploadFile, File
from typing import List

from app.services.resume_service import process_resume, process_multiple_resumes

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    result = await process_resume(file)
    return result


@router.post("/upload-multiple")
async def upload_multiple_resumes(files: List[UploadFile] = File(...)):
    result = await process_multiple_resumes(files)
    return result