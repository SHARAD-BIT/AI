from functools import lru_cache

from app.llm.provider import llm_json_extract
from app.llm.schemas import TenderRequirements


@lru_cache(maxsize=128)
def extract_tender_requirements_llm(text: str) -> TenderRequirements:
    prompt = f"""
You are an expert tender and RFP analyst.

Your job is to extract structured hiring or project requirements from tender text.

Return only valid JSON matching the provided schema.

Rules:
- Keep values concise
- Normalize skill names
- Extract role if clearly mentioned
- Extract domain if clearly inferable
- Convert years of experience to integer if possible
- Do not hallucinate
- If something is missing, return null or empty list

Tender text:
{text}
"""

    raw_json = llm_json_extract(
        prompt=prompt,
        schema=TenderRequirements.model_json_schema(),
        task="extraction",
    )

    return TenderRequirements.model_validate_json(raw_json)
