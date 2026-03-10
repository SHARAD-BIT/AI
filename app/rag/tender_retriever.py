from typing import List, Dict
from app.rag.vector_store import search_index

TENDER_INDEX_NAME = "tender"


def search_tender_vectors(query: str, top_k: int = 3) -> List[Dict]:
    return search_index(TENDER_INDEX_NAME, query, top_k)