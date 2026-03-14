import re

from app.models.document_pages import PageText


TENDER_SECTION_MARKERS = {
    "eligibility": ["eligibility", "eligible", "qualification criteria", "bidder eligibility"],
    "qualifications": ["qualification", "qualifications", "technical capacity", "financial capacity"],
    "experience": ["experience", "work experience", "similar works", "similar project"],
    "responsibilities": ["scope of work", "responsibilities", "services to be provided", "obligations"],
    "personnel": ["key personnel", "staff", "team leader", "experts"],
    "commercial": ["financial", "commercial", "payment", "bid security"],
}

RESUME_SECTION_MARKERS = {
    "summary": ["summary", "profile", "professional summary", "career objective"],
    "skills": ["skills", "technical skills", "core competencies", "expertise"],
    "experience": ["experience", "employment history", "professional experience", "work experience"],
    "projects": ["projects", "project experience", "relevant projects", "assignments"],
    "education": ["education", "academic qualification", "qualifications"],
    "certifications": ["certifications", "training", "licenses"],
}


def _normalize_heading(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" :-").lower()


def _is_heading_candidate(line: str) -> bool:
    if not line or len(line) > 120:
        return False

    words = line.split()
    if len(words) > 12:
        return False

    uppercase_ratio = sum(1 for char in line if char.isupper()) / max(1, sum(1 for char in line if char.isalpha()))
    return line.endswith(":") or uppercase_ratio > 0.6


def _match_section(line: str, document_type: str) -> str | None:
    normalized = _normalize_heading(line)
    marker_map = TENDER_SECTION_MARKERS if document_type == "tender" else RESUME_SECTION_MARKERS

    for section, markers in marker_map.items():
        if any(normalized == marker or normalized.startswith(marker) for marker in markers):
            return section

    if _is_heading_candidate(line):
        for section, markers in marker_map.items():
            if any(marker in normalized for marker in markers):
                return section

    return None


def build_semantic_blocks(pages: list[PageText], document_type: str) -> list[dict]:
    blocks = []
    current_section = "general"
    current_lines: list[str] = []
    page_start = None
    page_end = None

    def flush_block() -> None:
        nonlocal current_lines, page_start, page_end, current_section
        text = "\n".join(line for line in current_lines if line).strip()
        if text:
            blocks.append(
                {
                    "section": current_section,
                    "page_start": page_start,
                    "page_end": page_end,
                    "text": text,
                }
            )
        current_lines = []
        page_start = None
        page_end = None

    for page in pages:
        for raw_line in page.text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            matched_section = _match_section(line, document_type)
            if matched_section:
                flush_block()
                current_section = matched_section
                continue

            if page_start is None:
                page_start = page.page

            page_end = page.page
            current_lines.append(line)

        flush_block()

    flush_block()

    if not blocks:
        return [
            {
                "section": "general",
                "page_start": page.page,
                "page_end": page.page,
                "text": page.text,
            }
            for page in pages
            if page.text
        ]

    return blocks
