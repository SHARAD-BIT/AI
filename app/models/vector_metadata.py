from pydantic import BaseModel


class VectorChunkMetadata(BaseModel):
    filename: str = "unknown.pdf"
    text: str = ""
    chunk_id: int | None = None
    document_id: int | None = None
    document_type: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    embedding_backend: str | None = None
