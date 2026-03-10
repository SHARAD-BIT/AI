from app.llm.resume_llm_extractor import extract_resume_profile_llm


def extract_resume_data(text: str):
    data = extract_resume_profile_llm(text)

    return {
        "candidate_name": data.candidate_name,
        "role": data.role,
        "domain": data.domain,
        "skills": data.skills,
        "experience": data.experience_years,
        "qualifications": data.qualifications,
        "projects": data.projects,
    }