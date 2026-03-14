from app.agents.query_agent import build_answer_prompt, build_fallback_answer, classify_query_intent
from app.llm.provider import llm_text_answer
from app.rag.resume_retriever import get_resume_document_chunks, search_resume_vectors
from app.rag.tender_retriever import get_tender_document_chunks, search_tender_vectors
from app.rag.vector_store import index_has_data
from app.services.document_repository import (
    get_document_by_id,
    get_document_by_original_filename,
    get_latest_document,
    get_persisted_document_chunks,
)
from app.services.matching_service import match_resumes_with_uploaded_tender


def _resolve_document(document_type: str, match: dict | None = None) -> dict | None:
    document = None

    if match and match.get("document_id") is not None:
        document = get_document_by_id(match["document_id"])

    if document is None and match and match.get("filename"):
        document = get_document_by_original_filename(document_type, match["filename"])

    if document is None:
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


def _gather_scope_context(document_type: str, query: str, top_k: int = 6, per_doc_limit: int = 4) -> tuple[list[dict], list[dict]]:
    latest_document = get_latest_document(document_type)
    active_document_id = latest_document.get("id") if latest_document else None

    if document_type == "tender":
        search_results = search_tender_vectors(query, top_k=top_k)
    else:
        search_results = search_resume_vectors(query, top_k=top_k)

    chunks = []
    structured_contexts = []
    seen_documents = set()

    filtered_results = []
    if active_document_id is not None:
        filtered_results = [
            match
            for match in search_results
            if match.get("document_id") == active_document_id
        ]

    for match in filtered_results or search_results:
        document = _resolve_document(document_type, match)
        document_key = (document or {}).get("id") or match.get("document_id") or match.get("filename")

        if document_key in seen_documents:
            continue
        seen_documents.add(document_key)

        if document and document.get("structured_data"):
            structured_contexts.append(document["structured_data"])

        chunks.extend(_load_document_chunks(document_type, document=document, match=match, limit=per_doc_limit))

    if latest_document and active_document_id not in seen_documents:
        if latest_document.get("structured_data"):
            structured_contexts.insert(0, latest_document["structured_data"])
        latest_chunks = _load_document_chunks(document_type, document=latest_document, limit=per_doc_limit)
        if latest_chunks:
            chunks = latest_chunks + chunks
        seen_documents.add(active_document_id)
    elif not chunks and latest_document:
        if latest_document.get("structured_data"):
            structured_contexts.append(latest_document["structured_data"])
        chunks.extend(_load_document_chunks(document_type, document=latest_document, limit=per_doc_limit))

    return structured_contexts, chunks


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


def _answer_qa(query: str, scope: str) -> dict:
    scope_map = {
        "tender": ["tender"],
        "resume": ["resume"],
        "both": ["tender", "resume"],
    }

    scope_documents = scope_map.get(scope, [])
    structured_contexts = []
    chunks = []

    for document_type in scope_documents:
        scope_structured, scope_chunks = _gather_scope_context(document_type, query)
        structured_contexts.extend(scope_structured)
        chunks.extend(scope_chunks)

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


def answer_query(query: str) -> dict:
    has_tender = get_latest_document("tender") is not None or index_has_data("tender")
    has_resume = get_latest_document("resume") is not None or index_has_data("resume")

    intent = classify_query_intent(query, has_tender=has_tender, has_resume=has_resume)

    if intent["mode"] == "matching":
        result = match_resumes_with_uploaded_tender(query)
        result["mode"] = "matching"
        result["query_scope"] = "both"
        return result

    if intent["mode"] == "qa":
        return _answer_qa(query, scope=intent["scope"])

    return {
        "mode": "none",
        "query_scope": "none",
        "message": "No uploaded tender or resume documents were found.",
        "answer_text": "",
        "sources": [],
        "matches": [],
        "reasoning_summary": "",
    }
