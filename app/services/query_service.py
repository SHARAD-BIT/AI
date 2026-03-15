from app.agents.query_agent import build_answer_prompt, build_fallback_answer, classify_query_intent
from app.llm.provider import llm_text_answer
from app.rag.resume_retriever import (
    get_resume_chunk_window,
    get_resume_document_chunks,
    search_resume_vectors_hybrid,
)
from app.rag.tender_retriever import (
    get_tender_chunk_window,
    get_tender_document_chunks,
    search_tender_vectors_hybrid,
)
from app.rag.vector_store import index_has_data
from app.services.document_repository import (
    get_document_by_id,
    get_document_by_original_filename,
    get_documents_by_ids,
    get_latest_document,
    get_persisted_document_chunks,
)
from app.services.matching_service import match_resumes_with_uploaded_tender


COLLECTION_QUERY_HINTS = {
    "all applicants",
    "all candidates",
    "all profiles",
    "all resumes",
    "compare",
    "comparison",
    "find candidates",
    "find resumes",
    "list applicants",
    "list candidates",
    "list resumes",
    "many resumes",
    "multiple resumes",
    "rank candidate",
    "rank resume",
    "shortlist",
    "top candidate",
    "top candidates",
    "who are the applicants",
    "who are the candidates",
}

COLLECTION_QUERY_TOKENS = {
    "applicants",
    "candidates",
    "files",
    "profiles",
    "resumes",
}


def _build_active_documents_by_type(
    tender_document_id: int | None = None,
    resume_document_ids: list[int] | None = None,
) -> dict[str, list[dict]]:
    document_ids = []
    if tender_document_id is not None:
        document_ids.append(tender_document_id)
    if resume_document_ids:
        document_ids.extend(resume_document_ids)

    active_documents = {"tender": [], "resume": []}

    for document in get_documents_by_ids(document_ids):
        if not document or document.get("status") != "stored":
            continue

        document_type = document.get("document_type")
        if document_type in active_documents:
            active_documents[document_type].append(document)

    return active_documents


def _resolve_document(
    document_type: str,
    match: dict | None = None,
    active_documents: list[dict] | None = None,
) -> dict | None:
    document = None
    active_documents = active_documents or []
    active_documents_by_id = {
        item.get("id"): item
        for item in active_documents
        if item.get("id") is not None
    }

    if match and match.get("document_id") is not None:
        document = active_documents_by_id.get(match["document_id"]) or get_document_by_id(match["document_id"])

    if document is None and match and match.get("filename"):
        document = get_document_by_original_filename(document_type, match["filename"])

    if document is None:
        if active_documents:
            document = active_documents[0]
        else:
            document = get_latest_document(document_type)

    return document


def _load_document_chunks(document_type: str, document: dict | None = None, match: dict | None = None, limit: int = 4) -> list[dict]:
    filename = None
    document_id = None

    if document:
        filename = document.get("original_filename")
        document_id = document.get("id")

    if match:
        filename = filename or match.get("filename")
        if document_id is None:
            document_id = match.get("document_id")

    if document_id is not None:
        persisted_chunks = get_persisted_document_chunks(document_id, limit=limit)
        if persisted_chunks:
            return persisted_chunks

    if document_type == "tender":
        return get_tender_document_chunks(filename=filename, document_id=document_id, limit=limit)

    return get_resume_document_chunks(filename=filename, document_id=document_id, limit=limit)


def _load_match_context_chunks(document_type: str, match: dict, window: int = 1) -> list[dict]:
    if document_type == "tender":
        chunks = get_tender_chunk_window(
            center_chunk_id=match.get("chunk_id"),
            window=window,
            filename=match.get("filename"),
            document_id=match.get("document_id"),
        )
    else:
        chunks = get_resume_chunk_window(
            center_chunk_id=match.get("chunk_id"),
            window=window,
            filename=match.get("filename"),
            document_id=match.get("document_id"),
        )

    if chunks:
        return chunks

    fallback_chunk = dict(match)
    fallback_chunk["document_type"] = document_type
    return [fallback_chunk] if fallback_chunk.get("text") else []


def _should_focus_latest_document(
    document_type: str,
    query: str,
    scope_documents: list[str],
    active_documents: list[dict] | None = None,
) -> bool:
    lowered = " ".join((query or "").lower().split())
    active_documents = active_documents or []

    if document_type == "tender":
        return True

    if document_type != "resume":
        return False

    if active_documents:
        return len(active_documents) == 1

    if len(scope_documents) != 1:
        return False

    if ".pdf" in lowered:
        return False

    if any(hint in lowered for hint in COLLECTION_QUERY_HINTS):
        return False

    query_tokens = set(lowered.replace("?", " ").replace(",", " ").split())
    if query_tokens & COLLECTION_QUERY_TOKENS:
        return False

    return True


def _search_scope_matches(
    scope_documents: list[str],
    query: str,
    active_documents_by_type: dict[str, list[dict]] | None = None,
    requested_active_document_types: set[str] | None = None,
    restrict_to_active_uploads: bool = False,
    top_k_per_type: int = 8,
    total_top_k: int = 10,
) -> list[dict]:
    all_matches = []
    active_documents_by_type = active_documents_by_type or {}
    requested_active_document_types = requested_active_document_types or set()

    for document_type in scope_documents:
        active_documents = active_documents_by_type.get(document_type, [])
        active_document_ids = {
            document.get("id")
            for document in active_documents
            if document.get("id") is not None
        }
        if restrict_to_active_uploads and not active_document_ids:
            continue

        if document_type in requested_active_document_types and not active_document_ids:
            continue

        latest_document = None
        if (
            not active_document_ids
            and not restrict_to_active_uploads
            and document_type not in requested_active_document_types
            and _should_focus_latest_document(
                document_type,
                query,
                scope_documents,
                active_documents=active_documents,
            )
        ):
            latest_document = get_latest_document(document_type)

        if document_type == "tender":
            matches = search_tender_vectors_hybrid(query, top_k=top_k_per_type)
        else:
            matches = search_resume_vectors_hybrid(query, top_k=top_k_per_type)

        if active_document_ids:
            matches = [
                match
                for match in matches
                if match.get("document_id") in active_document_ids
            ]
        elif latest_document:
            latest_matches = [
                match
                for match in matches
                if match.get("document_id") == latest_document.get("id")
            ]
            matches = latest_matches

        for match in matches:
            enriched = dict(match)
            enriched["document_type"] = document_type
            all_matches.append(enriched)

    all_matches.sort(
        key=lambda item: (
            item.get("retrieval_score", 0.0),
            item.get("keyword_score", 0.0),
            -item.get("distance", float("inf")),
        ),
        reverse=True,
    )

    return all_matches[:total_top_k]


def _gather_scope_context(
    scope_documents: list[str],
    query: str,
    active_documents_by_type: dict[str, list[dict]] | None = None,
    requested_active_document_types: set[str] | None = None,
    restrict_to_active_uploads: bool = False,
    top_k_per_type: int = 5,
    total_top_k: int = 6,
    chunk_window: int = 0,
    max_chunks: int = 5,
) -> tuple[list[dict], list[dict]]:
    active_documents_by_type = active_documents_by_type or {}
    requested_active_document_types = requested_active_document_types or set()
    search_results = _search_scope_matches(
        scope_documents,
        query,
        active_documents_by_type=active_documents_by_type,
        requested_active_document_types=requested_active_document_types,
        restrict_to_active_uploads=restrict_to_active_uploads,
        top_k_per_type=top_k_per_type,
        total_top_k=total_top_k,
    )

    chunks = []
    structured_contexts = []
    seen_documents = set()
    seen_chunks = set()

    for match in search_results:
        document_type = match.get("document_type")
        active_documents = active_documents_by_type.get(document_type, [])
        document = _resolve_document(document_type, match, active_documents=active_documents)
        document_key = (document or {}).get("id") or match.get("document_id") or match.get("filename")

        if document_key not in seen_documents and document and document.get("structured_data"):
            structured_contexts.append(document["structured_data"])
            seen_documents.add(document_key)

        context_chunks = _load_match_context_chunks(document_type, match, window=chunk_window)
        for chunk in context_chunks:
            chunk["document_type"] = chunk.get("document_type") or document_type
            chunk_key = (
                chunk.get("document_id"),
                chunk.get("filename"),
                chunk.get("chunk_id"),
            )
            if chunk_key in seen_chunks or not chunk.get("text"):
                continue
            seen_chunks.add(chunk_key)
            chunks.append(chunk)
            if len(chunks) >= max_chunks:
                break

        if len(chunks) >= max_chunks:
            break

    if chunks:
        return structured_contexts[:2], chunks[:max_chunks]

    for document_type in scope_documents:
        active_documents = active_documents_by_type.get(document_type, [])
        if restrict_to_active_uploads and not active_documents:
            continue

        if document_type in requested_active_document_types and not active_documents:
            continue

        fallback_documents = active_documents or (
            [get_latest_document(document_type)]
            if get_latest_document(document_type)
            else []
        )

        if not fallback_documents:
            continue

        for fallback_document in fallback_documents:
            if fallback_document.get("structured_data"):
                document_key = fallback_document.get("id")
                if document_key not in seen_documents:
                    structured_contexts.append(fallback_document["structured_data"])
                    seen_documents.add(document_key)

            fallback_chunks = _load_document_chunks(
                document_type,
                document=fallback_document,
                limit=max(4, max_chunks // max(1, len(scope_documents))),
            )
            for chunk in fallback_chunks:
                chunk["document_type"] = chunk.get("document_type") or document_type
                chunk_key = (
                    chunk.get("document_id"),
                    chunk.get("filename"),
                    chunk.get("chunk_id"),
                )
                if chunk_key in seen_chunks or not chunk.get("text"):
                    continue
                seen_chunks.add(chunk_key)
                chunks.append(chunk)
                if len(chunks) >= max_chunks:
                    break

            if len(chunks) >= max_chunks:
                break

        if len(chunks) >= max_chunks:
            break

    return structured_contexts[:2], chunks[:max_chunks]


def _source_list(chunks: list[dict]) -> list[dict]:
    sources = []
    seen = set()

    for chunk in chunks:
        source = (
            chunk.get("filename"),
            chunk.get("page_start"),
            chunk.get("page_end"),
            chunk.get("section"),
        )
        if source in seen:
            continue
        seen.add(source)
        sources.append(
            {
                "filename": chunk.get("filename", "unknown.pdf"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "section": chunk.get("section"),
            }
        )

    return sources[:6]


def _answer_qa(
    query: str,
    scope: str,
    active_documents_by_type: dict[str, list[dict]] | None = None,
    requested_active_document_types: set[str] | None = None,
    restrict_to_active_uploads: bool = False,
) -> dict:
    scope_map = {
        "tender": ["tender"],
        "resume": ["resume"],
        "both": ["tender", "resume"],
    }

    scope_documents = scope_map.get(scope, [])
    structured_contexts = []
    chunks = []

    structured_contexts, chunks = _gather_scope_context(
        scope_documents,
        query,
        active_documents_by_type=active_documents_by_type,
        requested_active_document_types=requested_active_document_types,
        restrict_to_active_uploads=restrict_to_active_uploads,
    )

    if not chunks:
        return {
            "mode": "qa",
            "query_scope": scope,
            "message": "No uploaded documents are available for this question.",
            "answer_text": "",
            "sources": [],
            "matches": [],
            "reasoning_summary": "",
        }

    scope_label = " and ".join(scope_documents) if scope_documents else scope
    prompt = build_answer_prompt(query, scope_label, structured_contexts, chunks)
    answer_text = llm_text_answer(prompt).strip()

    if not answer_text:
        answer_text = build_fallback_answer(scope_label, chunks)

    return {
        "mode": "qa",
        "query_scope": scope,
        "message": f"Answered using uploaded {scope_label} documents.",
        "answer_text": answer_text,
        "sources": _source_list(chunks),
        "matches": [],
        "reasoning_summary": "",
    }


def answer_query(
    query: str,
    tender_document_id: int | None = None,
    resume_document_ids: list[int] | None = None,
    restrict_to_active_uploads: bool = False,
) -> dict:
    active_documents_by_type = _build_active_documents_by_type(
        tender_document_id=tender_document_id,
        resume_document_ids=resume_document_ids,
    )
    active_scope_enabled = (
        restrict_to_active_uploads
        or tender_document_id is not None
        or bool(resume_document_ids)
    )

    if active_scope_enabled:
        has_tender = bool(active_documents_by_type["tender"])
        has_resume = bool(active_documents_by_type["resume"])
    else:
        has_tender = get_latest_document("tender") is not None or index_has_data("tender")
        has_resume = get_latest_document("resume") is not None or index_has_data("resume")

    requested_active_document_types = set()
    if tender_document_id is not None:
        requested_active_document_types.add("tender")
    if resume_document_ids:
        requested_active_document_types.add("resume")

    intent = classify_query_intent(query, has_tender=has_tender, has_resume=has_resume)

    if intent["mode"] == "matching":
        result = match_resumes_with_uploaded_tender(
            query,
            tender_document_id=tender_document_id,
            resume_document_ids=resume_document_ids,
            restrict_to_active_uploads=restrict_to_active_uploads,
        )
        result["mode"] = "matching"
        result["query_scope"] = "both"
        return result

    if intent["mode"] == "qa":
        return _answer_qa(
            query,
            scope=intent["scope"],
            active_documents_by_type=active_documents_by_type,
            requested_active_document_types=requested_active_document_types,
            restrict_to_active_uploads=restrict_to_active_uploads,
        )

    return {
        "mode": "none",
        "query_scope": "none",
        "message": "No uploaded tender or resume documents were found.",
        "answer_text": "",
        "sources": [],
        "matches": [],
        "reasoning_summary": "",
    }
