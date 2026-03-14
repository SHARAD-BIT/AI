from app.services.document_ingestion import process_uploaded_document


async def process_resume(file):
    return await process_uploaded_document(file, document_type="resume")


async def process_multiple_resumes(files):
    processed = []
    failed = []

    for file in files:
        result = await process_uploaded_document(file, document_type="resume")

        if result.get("status") in {"stored", "duplicate"}:
            processed.append(result)
        else:
            failed.append(
                {
                    "filename": result.get("filename", file.filename),
                    "error": result.get("message", "Unknown processing failure"),
                    "status": result.get("status"),
                }
            )

    return {
        "message": "Bulk resume upload completed",
        "total_files": len(files),
        "processed_files": len(processed),
        "failed_files": len(failed),
        "processed": processed,
        "failed": failed,
    }
