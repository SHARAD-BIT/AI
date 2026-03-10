from typing import List, Dict
from app.rag.vector_store import search_index

RESUME_INDEX_NAME = "resume"


def search_resume_vectors(query: str, top_k: int = 3) -> List[Dict]:
    return search_index(RESUME_INDEX_NAME, query, top_k)