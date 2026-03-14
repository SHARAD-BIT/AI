import re
from collections import Counter

from app.models.document_pages import PageText


PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\s*page\s+\d+(\s+of\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
]


def _normalize_line(line: str) -> str:
    text = line.replace("\u00a0", " ").replace("\u200b", "").replace("Â", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _line_key(line: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_line(line).lower())


def _non_empty_lines(text: str) -> list[str]:
    return [_normalize_line(line) for line in text.splitlines() if _normalize_line(line)]


def _detect_repeated_boundary_lines(pages: list[PageText]) -> tuple[set[str], set[str]]:
    if len(pages) < 2:
        return set(), set()

    first_line_counter = Counter()
    last_line_counter = Counter()

    for page in pages:
        lines = _non_empty_lines(page.text)
        if not lines:
            continue
        first_line_counter[_line_key(lines[0])] += 1
        last_line_counter[_line_key(lines[-1])] += 1

    threshold = max(2, len(pages) // 2)
    repeated_headers = {line for line, count in first_line_counter.items() if line and count >= threshold}
    repeated_footers = {line for line, count in last_line_counter.items() if line and count >= threshold}

    return repeated_headers, repeated_footers


def clean_page_text(text: str, header_keys: set[str] | None = None, footer_keys: set[str] | None = None) -> str:
    header_keys = header_keys or set()
    footer_keys = footer_keys or set()

    cleaned_lines = []
    lines = _non_empty_lines(text)

    for index, line in enumerate(lines):
        key = _line_key(line)

        if index == 0 and key in header_keys:
            continue
        if index == len(lines) - 1 and key in footer_keys:
            continue
        if any(pattern.match(line) for pattern in PAGE_NUMBER_PATTERNS):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def clean_pages(pages: list[PageText]) -> list[PageText]:
    header_keys, footer_keys = _detect_repeated_boundary_lines(pages)
    cleaned_pages = []

    for page in pages:
        cleaned_text = clean_page_text(page.text, header_keys=header_keys, footer_keys=footer_keys)
        if cleaned_text:
            cleaned_pages.append(PageText(page=page.page, text=cleaned_text))

    return cleaned_pages


def clean_text(text: str) -> str:
    cleaned = clean_page_text(text)
    return re.sub(r"\s+", " ", cleaned).strip()
