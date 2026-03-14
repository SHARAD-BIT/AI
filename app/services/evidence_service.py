import re
from typing import Any


def _normalize_token(token: str) -> str:
    return "".join(char for char in str(token).lower() if char.isalnum())


def _token_set(value: Any) -> set[str]:
    return {_normalize_token(token) for token in str(value).split() if _normalize_token(token)}


def _extract_snippet(text: str, needle: str | None, max_chars: int = 240) -> str:
    normalized_needle = (needle or "").strip()
    clean_text = re.sub(r"\s+", " ", text).strip()

    if not clean_text:
        return ""

    if not normalized_needle:
        return clean_text[:max_chars]

    lowered_text = clean_text.lower()
    lowered_needle = normalized_needle.lower()
    index = lowered_text.find(lowered_needle)

    if index == -1:
        return clean_text[:max_chars]

    start = max(0, index - 60)
    end = min(len(clean_text), index + len(normalized_needle) + 120)
    return clean_text[start:end].strip()


def _score_chunk_for_value(value: Any, chunk: dict) -> float:
    if value is None or value == "" or value == []:
        return 0.0

    text = str(chunk.get("text", "") or "")
    lowered_text = text.lower()
    lowered_value = str(value).strip().lower()

    if not lowered_text or not lowered_value:
        return 0.0

    if lowered_value in lowered_text:
        return 0.98

    value_tokens = _token_set(lowered_value)
    chunk_tokens = _token_set(lowered_text)

    if not value_tokens or not chunk_tokens:
        return 0.0

    overlap = value_tokens & chunk_tokens
    if not overlap:
        return 0.0

    return round(len(overlap) / max(1, len(value_tokens)), 2)


def _build_evidence_entry(value: Any, chunks: list[dict]) -> dict:
    best_chunk = None
    best_score = 0.0

    for chunk in chunks:
        score = _score_chunk_for_value(value, chunk)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_chunk is None:
        return {
            "value": value,
            "source_text": None,
            "page": None,
            "section": None,
            "confidence": 0.0,
        }

    return {
        "value": value,
        "source_text": _extract_snippet(best_chunk.get("text", ""), str(value) if value is not None else None),
        "page": best_chunk.get("page_start"),
        "section": best_chunk.get("section"),
        "confidence": float(best_score),
    }


def build_evidence_map(structured_data: dict[str, Any], chunks: list[dict]) -> dict[str, Any]:
    evidence_map: dict[str, Any] = {}

    for field, value in structured_data.items():
        if isinstance(value, list):
            evidence_map[field] = [
                _build_evidence_entry(item, chunks)
                for item in value
                if item not in (None, "", [])
            ]
            continue

        evidence_map[field] = _build_evidence_entry(value, chunks)

    return evidence_map
