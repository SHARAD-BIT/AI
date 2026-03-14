from app.services.document_ingestion import process_uploaded_document


async def process_tender(file):
    return await process_uploaded_document(file, document_type="tender")
