import os
import pickle
from typing import List, Tuple, Dict, Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

VECTOR_DIR = "vector_store"
os.makedirs(VECTOR_DIR, exist_ok=True)

MODEL_NAME = "BAAI/bge-small-en"
EMBEDDING_DIM = 384

_model = SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> np.ndarray:
    if not isinstance(text, str):
        raise TypeError("embed_text expects a string")
    vector = _model.encode(text)
    return np.asarray(vector, dtype="float32")


def embed_texts(texts: List[str]) -> np.ndarray:
    if not isinstance(texts, list):
        raise TypeError("embed_texts expects a list of strings")
    if len(texts) == 0:
        return np.empty((0, EMBEDDING_DIM), dtype="float32")

    vectors = _model.encode(texts)
    return np.asarray(vectors, dtype="float32")


def _get_index_path(index_name: str) -> str:
    return os.path.join(VECTOR_DIR, f"{index_name}.faiss")


def _get_meta_path(index_name: str) -> str:
    return os.path.join(VECTOR_DIR, f"{index_name}_metadata.pkl")


def load_index(index_name: str) -> Tuple[faiss.IndexFlatL2, List[Dict[str, Any]]]:
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


def save_index(index_name: str, index: faiss.IndexFlatL2, metadata: List[Dict[str, Any]]) -> None:
    index_path = _get_index_path(index_name)
    meta_path = _get_meta_path(index_name)

    faiss.write_index(index, index_path)

    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)


def store_text_chunks(index_name: str, chunks: List[str], filename: str = "unknown.pdf") -> int:
    """
    Store chunks in FAISS with metadata:
    {
      "filename": "...",
      "text": "...",
      "chunk_id": 0
    }
    """
    if not chunks:
        return 0

    clean_chunks = [chunk.strip() for chunk in chunks if isinstance(chunk, str) and chunk.strip()]
    if not clean_chunks:
        return 0

    index, metadata = load_index(index_name)

    vectors = embed_texts(clean_chunks)
    index.add(vectors)

    start_chunk_id = len(metadata)

    for i, chunk in enumerate(clean_chunks):
        metadata.append(
            {
                "filename": filename,
                "text": chunk,
                "chunk_id": start_chunk_id + i,
            }
        )

    save_index(index_name, index, metadata)

    return len(clean_chunks)


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
        if idx == -1:
            continue
        if idx >= len(metadata):
            continue

        item = metadata[idx]

        results.append(
            {
                "filename": item.get("filename", "unknown.pdf"),
                "text": item.get("text", ""),
                "chunk_id": item.get("chunk_id"),
                "distance": float(distances[0][i]),
                "index": int(idx),
            }
        )

    return results