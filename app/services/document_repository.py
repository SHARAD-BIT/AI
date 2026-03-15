from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import delete, desc, func, select

from app.database.connection import init_db, session_scope
from app.models.db_models import Document, DocumentChunk


init_db()


def _document_to_dict(document: Document | None) -> dict | None:
    if document is None:
        return None

    return {
        "id": document.id,
        "document_type": document.document_type,
        "original_filename": document.original_filename,
        "stored_filename": document.stored_filename,
        "stored_path": document.stored_path,
        "file_hash": document.file_hash,
        "file_size": document.file_size,
        "status": document.status,
        "total_pages": document.total_pages,
        "extraction_backend": document.extraction_backend,
        "structured_data": document.structured_data or {},
        "evidence_map": document.evidence_map or {},
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _chunk_to_dict(chunk: DocumentChunk) -> dict:
    metadata = chunk.metadata_json or {}
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "index_name": chunk.index_name,
        "chunk_id": chunk.chunk_id,
        "text": chunk.chunk_text,
        "chunk_text": chunk.chunk_text,
        "section": chunk.section,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "embedding_backend": chunk.embedding_backend,
        **metadata,
    }


def get_document_by_hash(document_type: str, file_hash: str) -> dict | None:
    with session_scope() as db:
        document = db.scalar(
            select(Document).where(
                Document.document_type == document_type,
                Document.file_hash == file_hash,
            )
        )
        return _document_to_dict(document)


def get_document_by_id(document_id: int) -> dict | None:
    with session_scope() as db:
        document = db.scalar(select(Document).where(Document.id == document_id))
        return _document_to_dict(document)


def delete_all_documents() -> dict[str, int]:
    with session_scope() as db:
        document_count = db.scalar(select(func.count()).select_from(Document)) or 0
        chunk_count = db.scalar(select(func.count()).select_from(DocumentChunk)) or 0

        db.execute(delete(DocumentChunk))
        db.execute(delete(Document))

        return {
            "documents_deleted": int(document_count),
            "chunks_deleted": int(chunk_count),
        }


def get_documents_by_ids(document_ids: list[int]) -> list[dict]:
    ordered_ids = []
    seen = set()

    for value in document_ids:
        try:
            document_id = int(value)
        except (TypeError, ValueError):
            continue

        if document_id in seen:
            continue

        seen.add(document_id)
        ordered_ids.append(document_id)

    if not ordered_ids:
        return []

    with session_scope() as db:
        documents = db.scalars(
            select(Document).where(Document.id.in_(ordered_ids))
        ).all()

    documents_by_id = {
        document.id: _document_to_dict(document)
        for document in documents
        if document is not None
    }

    return [
        documents_by_id[document_id]
        for document_id in ordered_ids
        if document_id in documents_by_id
    ]


def get_latest_document(document_type: str) -> dict | None:
    with session_scope() as db:
        document = db.scalar(
            select(Document)
            .where(Document.document_type == document_type, Document.status == "stored")
            .order_by(desc(Document.updated_at), desc(Document.created_at))
        )
        return _document_to_dict(document)


def get_document_by_original_filename(document_type: str, original_filename: str) -> dict | None:
    with session_scope() as db:
        document = db.scalar(
            select(Document)
            .where(
                Document.document_type == document_type,
                Document.original_filename == original_filename,
            )
            .order_by(desc(Document.updated_at), desc(Document.created_at))
        )
        return _document_to_dict(document)


def create_document_record(**fields) -> dict:
    with session_scope() as db:
        document = Document(**fields)
        db.add(document)
        db.flush()
        db.refresh(document)
        return _document_to_dict(document) or {}


def update_document_record(document_id: int, **fields) -> dict | None:
    with session_scope() as db:
        document = db.scalar(select(Document).where(Document.id == document_id))
        if document is None:
            return None

        for key, value in fields.items():
            setattr(document, key, value)

        document.updated_at = datetime.utcnow()

        db.add(document)
        db.flush()
        db.refresh(document)
        return _document_to_dict(document)


def replace_document_chunks(document_id: int, index_name: str, chunks: Iterable[dict]) -> int:
    chunk_list = list(chunks)

    with session_scope() as db:
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

        for chunk in chunk_list:
            metadata = dict(chunk)
            metadata.pop("text", None)

            db.add(
                DocumentChunk(
                    document_id=document_id,
                    index_name=index_name,
                    chunk_id=int(chunk.get("chunk_id", 0)),
                    chunk_text=chunk.get("text", ""),
                    section=chunk.get("section"),
                    page_start=chunk.get("page_start"),
                    page_end=chunk.get("page_end"),
                    embedding_backend=chunk.get("embedding_backend", "faiss"),
                    metadata_json=metadata,
                )
            )

        return len(chunk_list)


def get_persisted_document_chunks(document_id: int, limit: int | None = None) -> list[dict]:
    with session_scope() as db:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)

        return [_chunk_to_dict(chunk) for chunk in db.scalars(statement).all()]


def rename_document_chunks(document_id: int, filename: str) -> int:
    with session_scope() as db:
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        ).all()

        for chunk in chunks:
            metadata = dict(chunk.metadata_json or {})
            metadata["filename"] = filename
            chunk.metadata_json = metadata
            db.add(chunk)

        return len(chunks)


def get_index_chunks(index_name: str) -> list[dict]:
    with session_scope() as db:
        rows = db.execute(
            select(DocumentChunk, Document.original_filename, Document.document_type)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(DocumentChunk.index_name == index_name)
            .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_id.asc())
        ).all()

        result = []
        for chunk, original_filename, document_type in rows:
            metadata = dict(chunk.metadata_json or {})
            result.append(
                {
                    "filename": metadata.get("filename", original_filename),
                    "text": chunk.chunk_text,
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "document_type": metadata.get("document_type", document_type),
                    "section": chunk.section,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "embedding_backend": chunk.embedding_backend,
                }
            )

        return result
