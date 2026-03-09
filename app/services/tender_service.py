from app.rag.loader import load_pdf
from app.rag.cleaner import clean_text
from app.llm.extractor import extract_tender_requirements


async def process_tender(file):

    text = load_pdf(file.file)

    clean = clean_text(text)

    requirements = extract_tender_requirements(clean)

    return {
        "tender_requirements": requirements
    }