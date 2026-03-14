from datetime import date, datetime
import re
from typing import Dict, List

from app.llm.resume_llm_extractor import extract_resume_profile_llm


RESUME_SKILL_PATTERNS = [
    ("python", "Python"),
    ("fastapi", "FastAPI"),
    ("nlp", "NLP"),
    ("machine learning", "Machine Learning"),
    ("aws", "AWS"),
    ("highway", "Highway Construction"),
    ("road", "Road Construction"),
    ("bridge", "Bridge Engineering"),
    ("structural", "Structural Engineering"),
    ("civil engineering", "Civil Engineering"),
    ("construction supervision", "Construction Supervision"),
    ("project management", "Project Management"),
    ("construction management", "Construction Management"),
    ("project monitoring", "Project Monitoring"),
    ("quality control", "Quality Control"),
    ("survey", "Survey"),
    ("dpr", "Detailed Project Report"),
]


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" :-")


def _prepare_focus_text(text: str, char_limit: int = 12000) -> str:
    return _normalize_whitespace(text[:char_limit])


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []

    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)

    return result


def _dedupe_projects(values: List[str]) -> List[str]:
    unique_projects = []
    signatures = []

    for value in values:
        cleaned = _normalize_whitespace(value)
        signature = re.sub(r"[^a-z0-9]", "", cleaned.lower())

        if not signature:
            continue

        prefix = signature[:80]
        if any(prefix == existing_prefix[:80] for existing_prefix in signatures):
            continue
        if any(signature in existing or existing in signature for existing in signatures):
            continue

        signatures.append(signature)
        unique_projects.append(cleaned)

    return unique_projects


def _line_candidates(text: str, limit: int = 160) -> List[str]:
    return [_normalize_whitespace(line) for line in text.splitlines()[:limit] if _normalize_whitespace(line)]


def _extract_value_near_label(lines: List[str], labels: List[str], stop_labels: List[str]) -> str | None:
    normalized_labels = {label.lower().rstrip(":") for label in labels}
    normalized_stop_labels = {label.lower().rstrip(":") for label in stop_labels}

    for index, line in enumerate(lines):
        current = line.lower().rstrip(":")

        if current in normalized_labels:
            for next_index in range(index + 1, min(index + 4, len(lines))):
                candidate = lines[next_index]
                candidate_key = candidate.lower().rstrip(":")
                if candidate == ":" or candidate_key in normalized_stop_labels:
                    continue
                return candidate

        for label in normalized_labels:
            prefix = f"{label}:"
            if current.startswith(prefix):
                candidate = _normalize_whitespace(line[len(prefix):])
                if candidate:
                    return candidate

    return None


def _extract_between_labels(flat_text: str, labels: List[str], stop_labels: List[str], max_chars: int = 120) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    stop_pattern = "|".join(re.escape(label) for label in stop_labels)

    pattern = rf"(?:{label_pattern})\s*:?\s*(.+?)(?=\s+(?:{stop_pattern})\s*:|$)"
    match = re.search(pattern, flat_text, flags=re.IGNORECASE)

    if not match:
        return None

    value = _normalize_whitespace(match.group(1))
    if not value:
        return None

    return value[:max_chars].strip(" ,;:-")


def _sanitize_name(value: str | None) -> str | None:
    if not value:
        return None

    value = re.sub(r"[^A-Za-z.\s'-]", " ", value)
    value = _normalize_whitespace(value)
    tokens = [token for token in value.split() if token]

    if not 2 <= len(tokens) <= 6:
        return None

    filtered = [
        token
        for token in tokens
        if token.lower() not in {"name", "staff", "candidate", "profession", "firm", "position"}
    ]

    if len(filtered) < 2:
        return None

    return " ".join(filtered[:6])


def _sanitize_role(value: str | None) -> str | None:
    if not value:
        return None

    value = re.sub(r"[^A-Za-z/&().,\-\s]", " ", value)
    value = _normalize_whitespace(value)

    if len(value) > 90:
        return None

    tokens = value.split()
    if not 1 <= len(tokens) <= 10:
        return None

    return value


def _extract_header_role(lines: List[str]) -> str | None:
    for index, line in enumerate(lines[:12]):
        lowered = line.lower()
        if lowered in {"technical proposal", "curriculum vitae", "cv", "profile"}:
            continue

        if "engineer" in lowered or "manager" in lowered or "specialist" in lowered or "consultant" in lowered:
            return _sanitize_role(line)

        if index == 1 and len(line.split()) <= 10:
            return _sanitize_role(line)

    return None


def _extract_candidate_name(text: str):
    lines = _line_candidates(text)
    flat_text = _prepare_focus_text(text)

    value = _extract_value_near_label(
        lines,
        ["Name of Staff", "Name of Candidate", "Candidate Name"],
        ["Profession", "Date of Birth", "Years with Firm/Entity", "Nationality", "Membership of Professional Societies"],
    )
    if value:
        return _sanitize_name(value)

    value = _extract_between_labels(
        flat_text,
        ["Name of Staff", "Name of Candidate", "Candidate Name"],
        ["Profession", "Date of Birth", "Years with Firm/Entity", "Nationality", "Membership of Professional Societies", "Detailed Task Assigned"],
        max_chars=80,
    )
    if value:
        return _sanitize_name(value)

    for line in lines[:40]:
        if line.lower() == "name":
            continue
        sanitized = _sanitize_name(line)
        if sanitized:
            return sanitized

    return None


def _extract_role(text: str):
    lines = _line_candidates(text)
    flat_text = _prepare_focus_text(text)

    value = _extract_value_near_label(
        lines,
        ["Proposed Position", "Position", "Role", "Profession"],
        ["Name of Firm", "Name of Staff", "Candidate Name", "Date of Birth", "Years with Firm/Entity", "Nationality"],
    )
    if value:
        return _sanitize_role(value)

    value = _extract_between_labels(
        flat_text,
        ["Proposed Position", "Position", "Role", "Profession"],
        ["Name of Firm", "Name of Staff", "Candidate Name", "Date of Birth", "Years with Firm/Entity", "Nationality", "Membership of Professional Societies"],
        max_chars=90,
    )
    if value:
        return _sanitize_role(value)

    return _extract_header_role(lines)


def _extract_domain(text: str):
    lowered = text.lower()

    if "highway" in lowered or "nhai" in lowered:
        return "Highway Construction"

    if "bridge" in lowered or "structural" in lowered:
        return "Bridge Engineering"

    if "civil engineering" in lowered or "civil engineer" in lowered:
        return "Civil Engineering"

    if "python" in lowered or "machine learning" in lowered or "fastapi" in lowered:
        return "AI/ML"

    return None


def _extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    skills = [skill for pattern, skill in RESUME_SKILL_PATTERNS if pattern in lowered]
    return _unique(skills)


def _extract_experience(text: str):
    direct_matches = [
        int(value)
        for value in re.findall(
            r"(?:total|overall|professional|relevant)?\s*(\d+)\+?\s+years?(?:\s+of)?\s+(?:professional\s+)?experience",
            text,
            flags=re.IGNORECASE,
        )
    ]
    if direct_matches:
        return max(direct_matches)

    labelled_patterns = [
        r"Years with Firm/Entity\s*:?\s*(\d{1,2})(?:\.\d+)?",
        r"Experience Details\s*:?\s*(\d{1,2})(?:\.\d+)?",
        r"Professional Experience\s*:?\s*(\d{1,2})(?:\.\d+)?",
    ]
    for pattern in labelled_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(float(match.group(1)))

    date_token = (
        r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{1,2}-[A-Za-z]{3}-\d{2,4}"
        r"|[A-Za-z]{3,9}\s+\d{4}"
        r"|[A-Za-z]{3}-\d{2,4}"
        r"|Till Date|Present|Current)"
    )
    pair_pattern = re.compile(
        rf"({date_token})\s+(?:to\s+)?({date_token})",
        flags=re.IGNORECASE,
    )

    ranges = []

    for match in pair_pattern.finditer(text):
        start = _parse_resume_date(match.group(1))
        end = _parse_resume_date(match.group(2))

        if not start or not end:
            continue
        if start.year < 1990 or end < start:
            continue

        span_years = (end - start).days / 365.25
        if 0.25 <= span_years <= 40:
            ranges.append((start, end))

    if ranges:
        earliest = min(start for start, _ in ranges)
        latest = max(end for _, end in ranges)
        years = round((latest - earliest).days / 365.25)
        if 1 <= years <= 40:
            return years

    return None


def _extract_projects(text: str) -> List[str]:
    focus_text = text[:40000]
    projects = []

    project_patterns = [
        r"(Independent Engineer Services for .{30,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
        r"(Consultancy Services for .{30,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
        r"(Construction of .{30,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
        r"(Widening and strengthening .{30,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
        r"(Rehabilitation and Upgradation .{30,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
        r"(Four laning .{30,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
        r"(Detailed Project Report .{20,220}?)(?=(?:\s+(?:India|Country|State|Employer Name|Project Status|Completion Certificate|View)\b|[.;]))",
    ]

    noise_patterns = [
        "authority of india would be at liberty",
        "certification by the candidate",
        "certification by the firm",
        "self-evaluation",
        "date of birth",
        "candidate_name",
        "signature of",
        "debar",
        "construction program and monitoring day-to-day site activities",
        "monitoring day-to-day site activities",
    ]

    for pattern in project_patterns:
        for match in re.finditer(pattern, focus_text, flags=re.IGNORECASE):
            snippet = _normalize_whitespace(match.group(1))
            lowered = snippet.lower()
            if any(noise in lowered for noise in noise_patterns):
                continue
            if 30 <= len(snippet) <= 220:
                projects.append(snippet[:200])

    return _dedupe_projects(_unique(projects))[:6]


def _parse_resume_date(value: str) -> date | None:
    raw_value = _normalize_whitespace(value).strip(".")
    lowered = raw_value.lower()

    if lowered in {"till date", "present", "current"}:
        return date.today()

    cleaned = re.sub(r"(\d)(st|nd|rd|th)", r"\1", raw_value, flags=re.IGNORECASE)
    cleaned = cleaned.replace("Â", " ")

    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d %B %Y",
        "%b-%Y",
        "%b-%y",
        "%b %Y",
        "%B %Y",
        "%Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            if fmt == "%Y":
                parsed = parsed.replace(month=1, day=1)
            elif fmt in {"%b-%Y", "%b-%y", "%b %Y", "%B %Y"}:
                parsed = parsed.replace(day=1)
            return parsed.date()
        except ValueError:
            continue

    return None


def _heuristic_extract_resume(text: str) -> Dict:
    focus_text = text[:50000]

    return {
        "candidate_name": _extract_candidate_name(focus_text),
        "role": _extract_role(focus_text),
        "domain": _extract_domain(focus_text),
        "skills": _extract_skills(focus_text),
        "experience": _extract_experience(focus_text),
        "qualifications": [],
        "projects": _extract_projects(focus_text),
    }


def extract_resume_data(text: str):
    heuristic = _heuristic_extract_resume(text)
    data = extract_resume_profile_llm(text)

    llm_skills = _unique(data.skills or [])
    llm_qualifications = _unique(data.qualifications or [])
    llm_projects = _unique(data.projects or [])

    return {
        "candidate_name": heuristic["candidate_name"] or data.candidate_name,
        "role": heuristic["role"] or data.role,
        "domain": heuristic["domain"] or data.domain,
        "skills": heuristic["skills"] or llm_skills,
        "experience": heuristic["experience"] or data.experience_years,
        "qualifications": heuristic["qualifications"] or llm_qualifications,
        "projects": heuristic["projects"] or llm_projects,
    }
