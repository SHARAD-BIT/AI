import os
from datetime import datetime

from app.rag.loader import load_pdf
from app.rag.chunker import split_text
from app.rag.vector_store import store_text_chunks

UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _save_uploaded_file(file):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


async def process_resume(file):
    print(f"Resume processing started: {file.filename}")

    file_path = await _save_uploaded_file(file)

    with open(file_path, "rb") as f:
        text = load_pdf(f)

    print("Text extracted length:", len(text))

    if not text or not text.strip():
        return {
            "filename": file.filename,
            "message": "No readable text found in PDF",
            "chunks": 0,
            "stored_chunks": 0,
            "saved_path": file_path,
        }

    chunks = split_text(text, chunk_size=800, overlap=150)
    print("Total chunks:", len(chunks))

    stored_count = store_text_chunks("resume", chunks, filename=file.filename)

    return {
        "filename": file.filename,
        "message": "Resume stored successfully",
        "chunks": len(chunks),
        "stored_chunks": stored_count,
        "saved_path": file_path,
    }


async def process_multiple_resumes(files):
    processed = []
    failed = []

    for file in files:
        try:
            print(f"Bulk processing resume: {file.filename}")

            file_path = await _save_uploaded_file(file)

            with open(file_path, "rb") as f:
                text = load_pdf(f)

            if not text or not text.strip():
                failed.append({
                    "filename": file.filename,
                    "error": "No readable text found in PDF"
                })
                continue

            chunks = split_text(text, chunk_size=800, overlap=150)

            if not chunks:
                failed.append({
                    "filename": file.filename,
                    "error": "No chunks created from extracted text"
                })
                continue

            stored_count = store_text_chunks("resume", chunks, filename=file.filename)

            processed.append({
                "filename": file.filename,
                "chunks": len(chunks),
                "stored_chunks": stored_count,
                "saved_path": file_path,
            })

        except Exception as e:
            failed.append({
                "filename": file.filename,
                "error": str(e),
            })

    return {
        "message": "Bulk resume upload completed",
        "total_files": len(files),
        "processed_files": len(processed),
        "failed_files": len(failed),
        "processed": processed,
        "failed": failed,
    }