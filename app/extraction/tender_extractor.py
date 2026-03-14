import re
from typing import Dict, List

from app.llm.tender_llm_extractor import extract_tender_requirements_llm


TENDER_SKILL_PATTERNS = [
    ("highway", "Highway Construction"),
    ("4 lanning", "Road Construction"),
    ("four-lane", "Road Construction"),
    ("road", "Road Construction"),
    ("bridge", "Bridge Engineering"),
    ("civil", "Civil Engineering"),
    ("project management", "Project Management"),
    ("construction", "Construction Management"),
]

PREFERRED_MARKERS = ["preferred", "preferably", "desirable"]
PERSONNEL_MARKERS = [
    "candidate",
    "staff",
    "personnel",
    "engineer",
    "expert",
    "manager",
    "consultant",
    "team leader",
    "professional",
]


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" :-")


def _unique(values: List[str]) -> List[str]:
    seen = set()
    result = []

    for value in values:
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            result.append(value)

    return result


def _extract_domain(text: str):
    lowered = text.lower()

    if "highway" in lowered or "nhai" in lowered or "hybrid annuity mode" in lowered:
        return "Highway Construction"

    if "bridge" in lowered:
        return "Bridge Engineering"

    if "civil" in lowered:
        return "Civil Engineering"

    if "python" in lowered or "machine learning" in lowered or "fastapi" in lowered:
        return "AI/ML"

    return None


def _is_noise_line(line: str) -> bool:
    lowered = line.lower()

    if len(line) < 15:
        return True

    noise_patterns = [
        "request for proposals",
        "table of contents",
        "notice inviting bid",
        "appendix",
        "section-",
        "section ",
        "bid security",
        "power of attorney",
        "general terms of bidding",
        "opening and evaluation",
        "authority shall",
        "bidder",
        "contractor(s)",
        "consultant(s)",
    ]

    return any(pattern in lowered for pattern in noise_patterns)


def _extract_role(text: str):
    compact_text = _normalize_whitespace(text[:5000])

    if re.search(r"construction of .{0,160}?(?:highway|road|lanning|lane)", compact_text, flags=re.IGNORECASE):
        return "Highway Construction Contractor"

    if re.search(r"construction of .{0,160}?bridge", compact_text, flags=re.IGNORECASE):
        return "Bridge Engineering Contractor"

    title_lines = []

    for raw_line in text.splitlines()[:80]:
        clean_line = _normalize_whitespace(raw_line)
        if not clean_line or _is_noise_line(clean_line):
            continue
        title_lines.append(clean_line)

    title_block = " ".join(title_lines[:12])

    if "highway" in title_block.lower() or "lanning" in title_block.lower():
        return "Highway Construction Contractor"

    if "bridge" in title_block.lower():
        return "Bridge Engineering Contractor"

    match = re.search(r"(construction of .{20,180}?)($| under | in the state| on hybrid annuity)", title_block, flags=re.IGNORECASE)
    if match:
        role = _normalize_whitespace(match.group(1))
        if role and not _is_noise_line(role):
            return role[:120]

    return None


def _extract_skills(text: str) -> List[str]:
    lowered = text.lower()
    skills = [skill for pattern, skill in TENDER_SKILL_PATTERNS if pattern in lowered]
    return _unique(skills)


def _extract_experience(text: str):
    clauses = re.split(r"[\n.;]", text)

    for clause in clauses:
        clean_clause = _normalize_whitespace(clause)
        lowered = clean_clause.lower()

        if not clean_clause:
            continue
        if not any(marker in lowered for marker in PERSONNEL_MARKERS):
            continue

        patterns = [
            r"(?:minimum|at least|not less than)\s+(\d+)\s+years?(?:\s+of)?\s+experience",
            r"(\d+)\+?\s+years?(?:\s+of)?\s+experience",
        ]

        for pattern in patterns:
            match = re.search(pattern, clean_clause, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))

    return None


def _extract_preferred_skills(text: str) -> List[str]:
    clauses = re.split(r"[\n.;]", text)
    preferred_skills = []

    for clause in clauses:
        clean_clause = _normalize_whitespace(clause)
        lowered = clean_clause.lower()

        if not clean_clause:
            continue
        if "undesirable" in lowered:
            continue
        if not any(marker in lowered for marker in PREFERRED_MARKERS):
            continue

        preferred_skills.extend(_extract_skills(clean_clause))

    return _unique(preferred_skills)


def _extract_qualifications(text: str) -> List[str]:
    lowered = text.lower()
    qualifications = []

    if "technical capacity" in lowered:
        qualifications.append("Technical capacity in similar infrastructure projects")
    if "financial capacity" in lowered or "net worth" in lowered:
        qualifications.append("Financial capacity / net worth compliance")
    if "eligibility" in lowered or "qualification" in lowered:
        qualifications.append("Eligibility and qualification compliance")
    if "experience certificate" in lowered:
        qualifications.append("Experience certificate for similar projects")
    if "bid security" in lowered:
        qualifications.append("Bid security submission")

    return qualifications[:5]


def _extract_responsibilities(text: str) -> List[str]:
    lowered = text.lower()
    responsibilities = []

    if "highway" in lowered or "road" in lowered or "lanning" in lowered:
        responsibilities.append("Execute highway and road construction works")
    if "bridge" in lowered:
        responsibilities.append("Deliver bridge and structural works where applicable")
    if "construction" in lowered or "project management" in lowered:
        responsibilities.append("Manage construction execution and project delivery")
    if "hybrid annuity mode" in lowered:
        responsibilities.append("Comply with Hybrid Annuity Mode project requirements")

    return responsibilities[:5]


def _heuristic_extract_tender(text: str) -> Dict:
    focus_text = "\n".join(text.splitlines()[:200])

    return {
        "role": _extract_role(focus_text),
        "domain": _extract_domain(focus_text),
        "skills_required": _extract_skills(focus_text),
        "preferred_skills": _extract_preferred_skills(focus_text),
        "experience_required": _extract_experience(focus_text),
        "qualifications": _extract_qualifications(focus_text),
        "responsibilities": _extract_responsibilities(focus_text),
    }


def extract_tender_requirements(text: str):
    heuristic = _heuristic_extract_tender(text)
    data = extract_tender_requirements_llm(text)

    llm_skills = _unique(data.skills_required or [])
    llm_qualifications = _unique(data.qualifications or [])
    llm_responsibilities = _unique(data.responsibilities or [])

    return {
        "role": heuristic["role"] or data.role,
        "domain": heuristic["domain"] or data.domain,
        "skills_required": heuristic["skills_required"] or llm_skills,
        "preferred_skills": heuristic["preferred_skills"],
        "experience_required": heuristic["experience_required"],
        "qualifications": heuristic["qualifications"] or llm_qualifications,
        "responsibilities": heuristic["responsibilities"] or llm_responsibilities,
    }
