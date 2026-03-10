from app.llm.provider import llm_json_extract
from app.llm.schemas import ResumeProfile


def extract_resume_profile_llm(text: str) -> ResumeProfile:
    prompt = f"""
You are an expert resume parser.

Your job is to extract a structured candidate profile from resume text.

Return only valid JSON matching the provided schema.

Rules:
- Keep values concise
- Normalize skill names
- Extract candidate name if clearly present
- Extract role if clearly mentioned
- Extract domain if clearly inferable
- Convert total years of experience to integer if possible
- Do not hallucinate
- If something is missing, return null or empty list

Resume text:
{text}
"""

    raw_json = llm_json_extract(
        prompt=prompt,
        schema=ResumeProfile.model_json_schema()
    )

    return ResumeProfile.model_validate_json(raw_json)