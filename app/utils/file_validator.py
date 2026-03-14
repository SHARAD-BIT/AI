import os

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


MAX_UPLOAD_FILE_SIZE_MB = int(os.getenv("MAX_UPLOAD_FILE_SIZE_MB", "25"))
MAX_UPLOAD_FILE_SIZE_BYTES = MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024
ALLOWED_PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream", ""}


def validate_pdf_upload(filename: str, content_type: str | None, data: bytes) -> dict:
    safe_content_type = (content_type or "").strip().lower()

    if not filename or not filename.strip():
        return {"is_valid": False, "error": "Missing filename", "page_count": None}

    if not filename.lower().endswith(".pdf"):
        return {"is_valid": False, "error": "Only PDF files are supported", "page_count": None}

    if not data:
        return {"is_valid": False, "error": "Uploaded file is empty", "page_count": None}

    if len(data) > MAX_UPLOAD_FILE_SIZE_BYTES:
        return {
            "is_valid": False,
            "error": f"File exceeds {MAX_UPLOAD_FILE_SIZE_MB} MB limit",
            "page_count": None,
        }

    if safe_content_type not in ALLOWED_PDF_CONTENT_TYPES:
        return {"is_valid": False, "error": "Unsupported content type for PDF upload", "page_count": None}

    if not data.lstrip().startswith(b"%PDF"):
        return {"is_valid": False, "error": "File does not appear to be a valid PDF", "page_count": None}

    if fitz is None:
        return {"is_valid": True, "error": None, "page_count": None}

    try:
        pdf_doc = fitz.open(stream=data, filetype="pdf")
        page_count = len(pdf_doc)
        if page_count <= 0:
            return {"is_valid": False, "error": "PDF has no readable pages", "page_count": 0}
        return {"is_valid": True, "error": None, "page_count": page_count}
    except Exception as exc:
        return {"is_valid": False, "error": f"Unreadable or corrupted PDF: {exc}", "page_count": None}
