from pydantic import BaseModel, Field


class PageText(BaseModel):
    page: int
    text: str


class ExtractedDocument(BaseModel):
    pages: list[PageText] = Field(default_factory=list)
    backend: str | None = None
