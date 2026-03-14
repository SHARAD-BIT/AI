from typing import Dict, List

from app.rag.vector_store import get_document_chunks, search_index


RESUME_INDEX_NAME = "resume"


def search_resume_vectors(query: str, top_k: int = 3) -> List[Dict]:
    return search_index(RESUME_INDEX_NAME, query, top_k)


def get_resume_document_chunks(
    filename: str | None = None,
    limit: int | None = None,
    document_id: int | None = None,
) -> List[Dict]:
    return get_document_chunks(RESUME_INDEX_NAME, filename=filename, limit=limit, document_id=document_id)
