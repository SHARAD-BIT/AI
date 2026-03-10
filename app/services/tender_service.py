import os
from datetime import datetime

from app.rag.loader import load_pdf
from app.rag.chunker import split_text
from app.rag.vector_store import store_text_chunks

UPLOAD_DIR = "uploads/tenders"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _save_uploaded_file(file):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


async def process_tender(file):
    print(f"Tender processing started: {file.filename}")

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

    stored_count = store_text_chunks("tender", chunks, filename=file.filename)

    return {
        "filename": file.filename,
        "message": "Tender stored successfully",
        "chunks": len(chunks),
        "stored_chunks": stored_count,
        "saved_path": file_path,
    }