import json


MATCH_KEYWORDS = {
    "match",
    "matching",
    "shortlist",
    "suitable candidate",
    "suitable resume",
    "best resume",
    "best resumes",
    "top candidate",
    "top candidates",
    "rank candidate",
    "rank resume",
    "find resumes",
    "find candidates",
}

TENDER_HINTS = {
    "tender",
    "rfp",
    "eligibility",
    "scope",
    "bid",
    "authority",
    "qualification",
    "requirements",
}

RESUME_HINTS = {
    "resume",
    "cv",
    "candidate",
    "candidate name",
    "applicant",
    "applicant name",
    "profile",
    "skill",
    "experience",
    "project",
}


def classify_query_intent(query: str, has_tender: bool, has_resume: bool) -> dict:
    lowered = " ".join(query.lower().split())

    is_match_query = has_tender and has_resume and any(keyword in lowered for keyword in MATCH_KEYWORDS)
    if is_match_query:
        return {"mode": "matching", "scope": "both"}

    if has_tender and not has_resume:
        return {"mode": "qa", "scope": "tender"}

    if has_resume and not has_tender:
        return {"mode": "qa", "scope": "resume"}

    if has_tender and has_resume:
        tender_hint = any(keyword in lowered for keyword in TENDER_HINTS)
        resume_hint = any(keyword in lowered for keyword in RESUME_HINTS)

        if tender_hint and not resume_hint:
            return {"mode": "qa", "scope": "tender"}
        if resume_hint and not tender_hint:
            return {"mode": "qa", "scope": "resume"}

        return {"mode": "qa", "scope": "both"}

    return {"mode": "none", "scope": "none"}


def build_answer_prompt(query: str, scope_label: str, structured_contexts: list[dict], chunks: list[dict]) -> str:
    structured_json = json.dumps(structured_contexts[:2], ensure_ascii=True, indent=2)

    rendered_chunks = []
    for index, chunk in enumerate(chunks[:5], start=1):
        filename = chunk.get("filename", "unknown.pdf")
        page_start = chunk.get("page_start") or "?"
        page_end = chunk.get("page_end") or page_start
        section = chunk.get("section") or "general"
        text = chunk.get("text", "").strip()
        compact_text = " ".join(text.split())[:1200]
        rendered_chunks.append(
            f"[{index}] file={filename} page={page_start}-{page_end} section={section}\n{compact_text}"
        )

    chunk_block = "\n\n".join(rendered_chunks)

    return f"""
You answer questions using only the supplied {scope_label} context.

Rules:
- Answer directly and concisely.
- Treat retrieved context as the primary evidence.
- Use structured context only as a secondary hint and ignore it if it conflicts with retrieved context.
- If multiple uploaded documents support different answers, say the question is ambiguous and list the plausible answers with sources.
- If the answer is not supported by the context, say so clearly.
- Mention source filename and page numbers when possible.
- Do not invent facts.

Question:
{query}

Structured context:
{structured_json}

Retrieved context:
{chunk_block}
""".strip()


def build_fallback_answer(scope_label: str, chunks: list[dict]) -> str:
    if not chunks:
        return f"No relevant uploaded {scope_label} context was found."

    snippets = []
    for chunk in chunks[:3]:
        filename = chunk.get("filename", "unknown.pdf")
        page = chunk.get("page_start") or "?"
        text = " ".join(str(chunk.get("text", "")).split())[:220]
        snippets.append(f"{filename} (page {page}): {text}")

    return f"LLM answer unavailable. Most relevant {scope_label} context: " + " | ".join(snippets)
