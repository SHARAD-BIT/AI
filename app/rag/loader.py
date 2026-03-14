import io
import os

import pdfplumber

try:
    from docling.document_converter import DocumentConverter
    from docling_core.types.io import DocumentStream
except Exception:
    DocumentConverter = None
    DocumentStream = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

from app.models.document_pages import ExtractedDocument, PageText


converter = DocumentConverter() if DocumentConverter else None


def _to_page_records(text_parts: list[str]) -> list[PageText]:
    pages = []

    for index, text in enumerate(text_parts, start=1):
        clean_text = (text or "").strip()
        if clean_text:
            pages.append(PageText(page=index, text=clean_text))

    return pages


def flatten_pages(pages: list[PageText]) -> str:
    return "\n\n".join(page.text for page in pages if page.text).strip()


def _extract_with_docling_pages(pdf_bytes: bytes, document_name: str) -> list[PageText]:
    if converter is None or DocumentStream is None:
        return []

    try:
        result = converter.convert(
            DocumentStream(
                name=document_name or "document.pdf",
                stream=io.BytesIO(pdf_bytes),
            )
        )
        text = result.document.export_to_markdown()
        return _to_page_records([text])
    except Exception as e:
        print("Docling extraction failed:", str(e))
        return []


def _extract_with_pdfplumber_pages(pdf_bytes: bytes) -> list[PageText]:
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

        return _to_page_records(text_parts)
    except Exception as e:
        print("pdfplumber extraction failed:", str(e))
        return []


def _extract_with_pymupdf_pages(pdf_bytes: bytes) -> list[PageText]:
    if not fitz:
        return []

    try:
        text_parts = []
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page in pdf_doc:
            text_parts.append(page.get_text("text") or "")

        return _to_page_records(text_parts)
    except Exception as e:
        print("PyMuPDF extraction failed:", str(e))
        return []


def _extract_with_ocr_pages(pdf_bytes: bytes) -> list[PageText]:
    if not fitz or not pytesseract or not Image:
        print("OCR dependencies not available")
        return []

    try:
        text_parts = []
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img) or ""
            text_parts.append(page_text)

        return _to_page_records(text_parts)
    except Exception as e:
        print("OCR extraction failed:", str(e))
        return []


def load_pdf_pages(file_obj_or_bytes, document_name: str | None = None) -> ExtractedDocument:
    try:
        if isinstance(file_obj_or_bytes, bytes):
            pdf_bytes = file_obj_or_bytes
        else:
            file_obj_or_bytes.seek(0)
            pdf_bytes = file_obj_or_bytes.read()

        resolved_name = document_name or os.path.basename(
            getattr(file_obj_or_bytes, "name", "") or ""
        ) or "document.pdf"

        if not pdf_bytes:
            return ExtractedDocument(pages=[], backend=None)

        extraction_pipeline = [
            ("pymupdf", _extract_with_pymupdf_pages),
            ("pdfplumber", _extract_with_pdfplumber_pages),
            ("docling", lambda raw_bytes: _extract_with_docling_pages(raw_bytes, resolved_name)),
            ("ocr", _extract_with_ocr_pages),
        ]

        for backend, extractor in extraction_pipeline:
            pages = extractor(pdf_bytes)
            if len(flatten_pages(pages)) > 50:
                print(f"Text extracted using {backend}")
                return ExtractedDocument(pages=pages, backend=backend)

        return ExtractedDocument(pages=[], backend=None)
    except Exception as e:
        print("load_pdf_pages failed:", str(e))
        return ExtractedDocument(pages=[], backend=None)


def load_pdf(file_obj):
    extracted = load_pdf_pages(file_obj)
    return flatten_pages(extracted.pages)
