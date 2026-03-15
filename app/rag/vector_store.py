import os
import pickle
import re
from typing import Any, List, Tuple

import faiss
import numpy as np

from app.models.vector_metadata import VectorChunkMetadata
from app.rag.embeddings import EMBEDDING_DIM, create_embedding, create_embeddings


VECTOR_DIR = "vector_store"
os.makedirs(VECTOR_DIR, exist_ok=True)

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
RRF_K = 60


def _ensure_index_materialized(index_name: str) -> None:
    index_path = _get_index_path(index_name)
    meta_path = _get_meta_path(index_name)

    if os.path.exists(index_path) and os.path.exists(meta_path):
        return

    try:
        from app.services.document_repository import get_index_chunks

        chunks = get_index_chunks(index_name)
        if not chunks:
            return

        clean_chunks = []
        for chunk in chunks:
            text = str(chunk.get("text", "")).strip()
            if not text:
                continue
            metadata = VectorChunkMetadata(
                filename=chunk.get("filename", "unknown.pdf"),
                text=text,
                chunk_id=chunk.get("chunk_id"),
                document_id=chunk.get("document_id"),
                document_type=chunk.get("document_type"),
                section=chunk.get("section"),
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                embedding_backend=chunk.get("embedding_backend", "faiss"),
            )
            clean_chunks.append(metadata.model_dump(exclude_none=True))

        if not clean_chunks:
            return

        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        vectors = embed_texts([chunk["text"] for chunk in clean_chunks])
        index.add(vectors)
        save_index(index_name, index, clean_chunks)
    except Exception as exc:
        print(f"Failed to rebuild FAISS index '{index_name}' from DB: {exc}")


def embed_text(text: str) -> np.ndarray:
    if not isinstance(text, str):
        raise TypeError("embed_text expects a string")
    return np.asarray(create_embedding(text), dtype="float32")


def embed_texts(texts: List[str]) -> np.ndarray:
    if not isinstance(texts, list):
        raise TypeError("embed_texts expects a list of strings")
    if len(texts) == 0:
        return np.empty((0, EMBEDDING_DIM), dtype="float32")

    return np.asarray(create_embeddings(texts), dtype="float32")


def _get_index_path(index_name: str) -> str:
    return os.path.join(VECTOR_DIR, f"{index_name}.faiss")


def _get_meta_path(index_name: str) -> str:
    return os.path.join(VECTOR_DIR, f"{index_name}_metadata.pkl")


def load_index(index_name: str) -> Tuple[faiss.IndexFlatL2, List[dict[str, Any]]]:
    _ensure_index_materialized(index_name)

    index_path = _get_index_path(index_name)
    meta_path = _get_meta_path(index_name)

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
    else:
        index = faiss.IndexFlatL2(EMBEDDING_DIM)

    if os.path.exists(meta_path):
        with open(meta_path, "rb") as f:
            metadata = pickle.load(f)
    else:
        metadata = []

    return index, metadata


def index_has_data(index_name: str) -> bool:
    index, metadata = load_index(index_name)
    return index.ntotal > 0 and len(metadata) > 0


def invalidate_index(index_name: str) -> None:
    index_path = _get_index_path(index_name)
    meta_path = _get_meta_path(index_name)

    if os.path.exists(index_path):
        os.remove(index_path)

    if os.path.exists(meta_path):
        os.remove(meta_path)


def save_index(index_name: str, index: faiss.IndexFlatL2, metadata: List[dict[str, Any]]) -> None:
    index_path = _get_index_path(index_name)
    meta_path = _get_meta_path(index_name)

    faiss.write_index(index, index_path)

    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)


def store_document_chunks(index_name: str, chunks: List[dict], filename: str = "unknown.pdf") -> int:
    if not chunks:
        return 0

    clean_chunks = []
    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue

        metadata = VectorChunkMetadata(
            filename=chunk.get("filename", filename),
            text=text,
            chunk_id=chunk.get("chunk_id"),
            document_id=chunk.get("document_id"),
            document_type=chunk.get("document_type"),
            section=chunk.get("section"),
            page_start=chunk.get("page_start"),
            page_end=chunk.get("page_end"),
            embedding_backend=chunk.get("embedding_backend", "faiss"),
        )
        clean_chunks.append(metadata.model_dump(exclude_none=True))

    if not clean_chunks:
        return 0

    index, metadata = load_index(index_name)
    vectors = embed_texts([chunk["text"] for chunk in clean_chunks])
    index.add(vectors)
    metadata.extend(clean_chunks)
    save_index(index_name, index, metadata)

    return len(clean_chunks)


def store_text_chunks(index_name: str, chunks: List[str], filename: str = "unknown.pdf") -> int:
    normalized_chunks = [
        {"filename": filename, "text": chunk, "chunk_id": index}
        for index, chunk in enumerate(chunks)
    ]
    return store_document_chunks(index_name, normalized_chunks, filename=filename)


def search_index(index_name: str, query_text: str, top_k: int = 3):
    if not query_text or not query_text.strip():
        return []

    index, metadata = load_index(index_name)

    if index.ntotal == 0 or len(metadata) == 0:
        return []

    query_vector = embed_text(query_text).reshape(1, -1)
    safe_k = min(top_k, len(metadata))
    distances, indices = index.search(query_vector, safe_k)

    results = []

    for i, idx in enumerate(indices[0]):
        if idx == -1 or idx >= len(metadata):
            continue

        item = dict(metadata[idx])
        results.append(
            {
                "filename": item.get("filename", "unknown.pdf"),
                "text": item.get("text", ""),
                "chunk_id": item.get("chunk_id"),
                "document_id": item.get("document_id"),
                "document_type": item.get("document_type"),
                "section": item.get("section"),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "embedding_backend": item.get("embedding_backend", "faiss"),
                "distance": float(distances[0][i]),
                "index": int(idx),
            }
        )

    return results


def _tokenize_for_search(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(str(text).lower())


def _keyword_score(query_text: str, chunk_text: str) -> float:
    query = str(query_text or "").strip().lower()
    text = str(chunk_text or "").strip().lower()

    if not query or not text:
        return 0.0

    query_tokens = set(_tokenize_for_search(query))
    if not query_tokens:
        return 0.0

    text_tokens = set(_tokenize_for_search(text))
    if not text_tokens:
        return 0.0

    overlap = query_tokens & text_tokens
    if not overlap:
        return 0.0

    score = len(overlap) / len(query_tokens)

    if query in text:
        score += 1.0

    contiguous_overlap = " ".join(token for token in query.split() if token in overlap)
    if contiguous_overlap and contiguous_overlap in text:
        score += 0.5

    return score


def search_index_hybrid(
    index_name: str,
    query_text: str,
    top_k: int = 6,
    semantic_multiplier: int = 4,
    lexical_multiplier: int = 8,
):
    if not query_text or not query_text.strip():
        return []

    index, metadata = load_index(index_name)
    if index.ntotal == 0 or len(metadata) == 0:
        return []

    semantic_limit = max(top_k, top_k * semantic_multiplier)
    semantic_results = search_index(index_name, query_text, top_k=semantic_limit)

    lexical_scored = []
    lexical_limit = max(top_k, top_k * lexical_multiplier)
    for idx, item in enumerate(metadata):
        score = _keyword_score(query_text, item.get("text", ""))
        if score <= 0:
            continue
        lexical_scored.append((score, idx, item))

    lexical_scored.sort(key=lambda entry: (entry[0], -len(str(entry[2].get("text", "")))), reverse=True)
    lexical_results = [
        {
            "filename": item.get("filename", "unknown.pdf"),
            "text": item.get("text", ""),
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "document_type": item.get("document_type"),
            "section": item.get("section"),
            "page_start": item.get("page_start"),
            "page_end": item.get("page_end"),
            "embedding_backend": item.get("embedding_backend", "faiss"),
            "keyword_score": float(score),
            "index": int(idx),
        }
        for score, idx, item in lexical_scored[:lexical_limit]
    ]

    fused_results: dict[tuple[Any, Any, Any], dict[str, Any]] = {}

    for rank, result in enumerate(semantic_results, start=1):
        key = (
            result.get("document_id"),
            result.get("filename"),
            result.get("chunk_id"),
        )
        entry = fused_results.setdefault(key, dict(result))
        entry["semantic_rank"] = rank
        entry["retrieval_score"] = entry.get("retrieval_score", 0.0) + (1.0 / (RRF_K + rank))

    for rank, result in enumerate(lexical_results, start=1):
        key = (
            result.get("document_id"),
            result.get("filename"),
            result.get("chunk_id"),
        )
        entry = fused_results.setdefault(key, dict(result))
        for field, value in result.items():
            entry.setdefault(field, value)
        entry["keyword_rank"] = rank
        entry["retrieval_score"] = entry.get("retrieval_score", 0.0) + (1.0 / (RRF_K + rank))

    ranked = sorted(
        fused_results.values(),
        key=lambda item: (
            item.get("retrieval_score", 0.0),
            item.get("keyword_score", 0.0),
            -item.get("distance", float("inf")),
        ),
        reverse=True,
    )

    return ranked[:top_k]


def get_document_chunks(
    index_name: str,
    filename: str | None = None,
    limit: int | None = None,
    document_id: int | None = None,
):
    _, metadata = load_index(index_name)
    chunks = []

    for item in metadata:
        if document_id is not None:
            if item.get("document_id") != document_id:
                continue
        elif filename is not None:
            if item.get("filename") != filename:
                continue
        else:
            continue

        chunks.append(
            {
                "filename": item.get("filename", "unknown.pdf"),
                "text": item.get("text", ""),
                "chunk_id": item.get("chunk_id"),
                "document_id": item.get("document_id"),
                "document_type": item.get("document_type"),
                "section": item.get("section"),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "embedding_backend": item.get("embedding_backend", "faiss"),
            }
        )

    chunks.sort(key=lambda item: item.get("chunk_id", 0) or 0)

    if limit is not None:
        chunks = chunks[:limit]

    return chunks


def get_chunk_window(
    index_name: str,
    *,
    center_chunk_id: int | None,
    window: int = 1,
    filename: str | None = None,
    document_id: int | None = None,
) -> list[dict]:
    if center_chunk_id is None:
        return []

    lower_bound = center_chunk_id - max(0, window)
    upper_bound = center_chunk_id + max(0, window)

    chunks = get_document_chunks(
        index_name,
        filename=filename,
        document_id=document_id,
    )

    return [
        chunk
        for chunk in chunks
        if chunk.get("chunk_id") is not None and lower_bound <= chunk["chunk_id"] <= upper_bound
    ]
