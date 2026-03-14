from typing import Dict, List

from app.rag.vector_store import get_document_chunks, search_index


TENDER_INDEX_NAME = "tender"


def search_tender_vectors(query: str, top_k: int = 3) -> List[Dict]:
    return search_index(TENDER_INDEX_NAME, query, top_k)


def get_tender_document_chunks(
    filename: str | None = None,
    limit: int | None = None,
    document_id: int | None = None,
) -> List[Dict]:
    return get_document_chunks(TENDER_INDEX_NAME, filename=filename, limit=limit, document_id=document_id)
