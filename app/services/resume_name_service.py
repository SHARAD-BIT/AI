import os

from app.extraction.resume_extractor import extract_candidate_name, extract_candidate_role
from app.rag.loader import load_pdf_pages


RESUME_NAME_QUERY_HINTS = (
    "applicant name",
    "candidate name",
    "name of applicant",
    "name of candidate",
    "name of the applicant",
    "name of the candidate",
    "resume name",
    "name in the resume",
    "who is the applicant",
    "who is the candidate",
)


def is_resume_name_query(query: str) -> bool:
    lowered = " ".join((query or "").lower().split())

    if any(hint in lowered for hint in RESUME_NAME_QUERY_HINTS):
        return True

    return "name" in lowered and any(
        token in lowered for token in ["applicant", "candidate", "resume", "cv", "staff"]
    )


def resolve_candidate_name_from_resume_context(
    chunks: list[dict],
    structured_contexts: list[dict] | None = None,
    document: dict | None = None,
) -> tuple[str | None, dict | None]:
    for chunk in chunks:
        candidate_name = extract_candidate_name(chunk.get("text", ""))
        if candidate_name:
            return candidate_name, chunk

    for structured_context in structured_contexts or []:
        candidate_name = extract_candidate_name(str(structured_context.get("candidate_name") or ""))
        if candidate_name:
            return candidate_name, None

    combined_text = "\n".join(chunk.get("text", "") for chunk in chunks if chunk.get("text"))
    candidate_name = extract_candidate_name(combined_text)
    if candidate_name:
        source_chunk = chunks[0] if chunks else None
        return candidate_name, source_chunk

    if document:
        stored_path = document.get("stored_path")
        if stored_path and os.path.exists(stored_path):
            with open(stored_path, "rb") as file_obj:
                extracted = load_pdf_pages(
                    file_obj.read(),
                    document_name=document.get("original_filename"),
                )
            for page in extracted.pages:
                candidate_name = extract_candidate_name(page.text)
                if candidate_name:
                    return candidate_name, {
                        "filename": document.get("original_filename", "unknown.pdf"),
                        "text": page.text,
                        "document_id": document.get("id"),
                        "document_type": "resume",
                        "page_start": page.page,
                        "page_end": page.page,
                        "section": "general",
                    }

    return None, None


def resolve_candidate_role_from_resume_context(
    chunks: list[dict],
    structured_contexts: list[dict] | None = None,
    document: dict | None = None,
) -> tuple[str | None, dict | None]:
    for chunk in chunks:
        candidate_role = extract_candidate_role(chunk.get("text", ""))
        if candidate_role:
            return candidate_role, chunk

    for structured_context in structured_contexts or []:
        candidate_role = extract_candidate_role(str(structured_context.get("role") or ""))
        if candidate_role:
            return candidate_role, None

    combined_text = "\n".join(chunk.get("text", "") for chunk in chunks if chunk.get("text"))
    candidate_role = extract_candidate_role(combined_text)
    if candidate_role:
        source_chunk = chunks[0] if chunks else None
        return candidate_role, source_chunk

    if document:
        stored_path = document.get("stored_path")
        if stored_path and os.path.exists(stored_path):
            with open(stored_path, "rb") as file_obj:
                extracted = load_pdf_pages(
                    file_obj.read(),
                    document_name=document.get("original_filename"),
                )
            for page in extracted.pages:
                candidate_role = extract_candidate_role(page.text)
                if candidate_role:
                    return candidate_role, {
                        "filename": document.get("original_filename", "unknown.pdf"),
                        "text": page.text,
                        "document_id": document.get("id"),
                        "document_type": "resume",
                        "page_start": page.page,
                        "page_end": page.page,
                        "section": "general",
                    }

    return None, None


def repair_resume_structured_data(
    structured_data: dict | None,
    chunks: list[dict],
    document: dict | None = None,
) -> tuple[dict, dict | None, bool]:
    repaired_data = dict(structured_data or {})
    existing_name = repaired_data.get("candidate_name")
    existing_role = repaired_data.get("role")
    candidate_name, source_chunk = resolve_candidate_name_from_resume_context(
        chunks,
        structured_contexts=[repaired_data],
        document=document,
    )
    candidate_role, role_source_chunk = resolve_candidate_role_from_resume_context(
        chunks,
        structured_contexts=[repaired_data],
        document=document,
    )

    changed = False

    if candidate_name and repaired_data.get("candidate_name") != candidate_name:
        repaired_data["candidate_name"] = candidate_name
        changed = True
    elif existing_name and not extract_candidate_name(str(existing_name)):
        repaired_data["candidate_name"] = None
        changed = True

    if candidate_role and repaired_data.get("role") != candidate_role:
        repaired_data["role"] = candidate_role
        changed = True
    elif existing_role and not extract_candidate_role(str(existing_role)):
        repaired_data["role"] = None
        changed = True

    return repaired_data, source_chunk or role_source_chunk, changed
