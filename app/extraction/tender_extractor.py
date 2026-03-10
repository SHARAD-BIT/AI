from app.llm.tender_llm_extractor import extract_tender_requirements_llm


def extract_tender_requirements(text: str):
    data = extract_tender_requirements_llm(text)

    return {
        "role": data.role,
        "domain": data.domain,
        "skills_required": data.skills_required,
        "preferred_skills": data.preferred_skills,
        "experience_required": data.experience_required,
        "qualifications": data.qualifications,
        "responsibilities": data.responsibilities,
    }