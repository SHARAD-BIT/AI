from app.extraction.tender_extractor import extract_tender_requirements
from app.extraction.resume_extractor import extract_resume_data
from app.rag.resume_retriever import search_resume_vectors
from app.rag.tender_retriever import search_tender_vectors
from app.graph.matching_graph import build_matching_graph


matching_graph = build_matching_graph()


def _to_int(value):
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _text_match(a, b):
    if not a or not b:
        return False
    return str(a).strip().lower() == str(b).strip().lower()


def _build_verdict(score, experience_match):
    if score >= 80 and experience_match:
        return "Highly Suitable"
    if score >= 50:
        return "Partially Suitable"
    return "Low Suitable"


def _build_resume_search_query(query, tender_data):
    parts = []

    role = tender_data.get("role")
    domain = tender_data.get("domain")
    skills = tender_data.get("skills_required", [])
    preferred_skills = tender_data.get("preferred_skills", [])
    experience = tender_data.get("experience_required")

    if role:
        parts.append(role)

    if domain:
        parts.append(domain)

    if skills:
        parts.extend(skills)

    if preferred_skills:
        parts.extend(preferred_skills[:5])

    if experience is not None:
        parts.append(f"{experience} years experience")

    if not parts:
        parts.append(query)

    return " ".join(parts)


def _score_candidate(tender_data, resume_data):
    required_skills = tender_data.get("skills_required", [])
    preferred_skills = tender_data.get("preferred_skills", [])
    required_experience = _to_int(tender_data.get("experience_required"))

    candidate_skills = resume_data.get("skills", [])
    candidate_experience = _to_int(resume_data.get("experience"))
    candidate_role = resume_data.get("role")
    candidate_domain = resume_data.get("domain")

    tender_role = tender_data.get("role")
    tender_domain = tender_data.get("domain")

    matched_skills = sorted(list(set(required_skills) & set(candidate_skills)))
    missing_skills = sorted(list(set(required_skills) - set(candidate_skills)))
    matched_preferred_skills = sorted(list(set(preferred_skills) & set(candidate_skills)))

    if len(required_skills) == 0:
        skill_score = 0
    else:
        skill_score = (len(matched_skills) / len(required_skills)) * 70

    preferred_score = 0
    if preferred_skills:
        preferred_score = (len(matched_preferred_skills) / len(preferred_skills)) * 10

    role_match = _text_match(tender_role, candidate_role)
    domain_match = _text_match(tender_domain, candidate_domain)

    role_score = 10 if role_match else 0
    domain_score = 10 if domain_match else 0

    if required_experience is not None and candidate_experience is not None:
        experience_match = candidate_experience >= required_experience
        experience_score = 10 if experience_match else 0
    else:
        experience_match = False
        experience_score = 0

    final_score = round(
        min(100, skill_score + preferred_score + role_score + domain_score + experience_score),
        2
    )

    verdict = _build_verdict(final_score, experience_match)

    return {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_preferred_skills": matched_preferred_skills,
        "required_experience": required_experience,
        "candidate_experience": candidate_experience,
        "experience_match": experience_match,
        "role_match": role_match,
        "domain_match": domain_match,
        "score": final_score,
        "verdict": verdict,
    }


def match_resumes_with_uploaded_tender(query: str):
    """
    Full pipeline:
    query
    ↓
    search tender index
    ↓
    LLM tender extraction
    ↓
    search resume index
    ↓
    LLM resume extraction
    ↓
    scoring
    ↓
    LangGraph reasoning
    """

    # 1. Find relevant tender chunks
    tender_matches = search_tender_vectors(query, top_k=5)
    tender_chunks = [item["text"] for item in tender_matches]

    if not tender_chunks:
        return {
            "message": "No uploaded tender data found. Please upload a tender PDF first.",
            "tender_requirements": {
                "role": None,
                "domain": None,
                "skills_required": [],
                "preferred_skills": [],
                "experience_required": None,
                "qualifications": [],
                "responsibilities": [],
            },
            "matches": [],
            "reasoning_summary": "No tender available for reasoning."
        }

    # 2. Merge tender chunks and extract requirements using LLM
    tender_text = "\n".join(tender_chunks)
    tender_data = extract_tender_requirements(tender_text)

    # 3. Build better resume search query from tender extraction
    resume_search_query = _build_resume_search_query(query, tender_data)

    # 4. Search resumes
    resume_matches = search_resume_vectors(resume_search_query, top_k=10)

    if not resume_matches:
        return {
            "message": "No resume matches found. Please upload resume PDFs first.",
            "tender_requirements": tender_data,
            "matches": [],
            "reasoning_summary": "No resume matches were available for reasoning."
        }

    results = []

    # 5. Extract resume profiles + score
    for match in resume_matches:
        resume_text = match["text"]
        resume_filename = match.get("filename", "unknown.pdf")

        resume_data = extract_resume_data(resume_text)

        scored = _score_candidate(tender_data, resume_data)

        results.append({
            "filename": resume_filename,
            "resume_excerpt": resume_text[:300],
            "candidate_name": resume_data.get("candidate_name"),
            "candidate_role": resume_data.get("role"),
            "candidate_domain": resume_data.get("domain"),
            "candidate_skills": resume_data.get("skills", []),
            "candidate_qualifications": resume_data.get("qualifications", []),
            "candidate_projects": resume_data.get("projects", []),
            **scored
        })

    # 6. Deduplicate by filename - keep best result per file
    best_by_file = {}

    for item in results:
        filename = item["filename"]

        if filename not in best_by_file:
            best_by_file[filename] = item
        else:
            current_best = best_by_file[filename]

            if (
                item["score"] > current_best["score"]
                or (
                    item["score"] == current_best["score"]
                    and item["experience_match"] > current_best["experience_match"]
                )
            ):
                best_by_file[filename] = item

    unique_results = list(best_by_file.values())

    unique_results.sort(
        key=lambda x: (x["score"], x["experience_match"]),
        reverse=True
    )

    # 7. LangGraph reasoning layer
    graph_result = matching_graph.invoke({
        "query": query,
        "tender_requirements": tender_data,
        "matches": unique_results
    })

    return {
        "message": "Matching completed using uploaded tender.",
        "tender_requirements": tender_data,
        "matches": graph_result.get("matches", unique_results),
        "reasoning_summary": graph_result.get("reasoning_summary", "")
    }