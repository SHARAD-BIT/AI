import io

import pdfplumber
from docling.document_converter import DocumentConverter

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
except Exception:
    fitz = None
    pytesseract = None
    Image = None


converter = DocumentConverter()


def _extract_with_docling(pdf_bytes: bytes) -> str:
    try:
        result = converter.convert(io.BytesIO(pdf_bytes))
        text = result.document.export_to_markdown()
        return text.strip() if text else ""
    except Exception as e:
        print("Docling extraction failed:", str(e))
        return ""


def _extract_with_pdfplumber(pdf_bytes: bytes) -> str:
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        text = "\n".join(text_parts).strip()
        return text
    except Exception as e:
        print("pdfplumber extraction failed:", str(e))
        return ""


def _extract_with_ocr(pdf_bytes: bytes) -> str:
    if not fitz or not pytesseract or not Image:
        print("OCR dependencies not available")
        return ""

    try:
        text_parts = []

        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            page_text = pytesseract.image_to_string(img)
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts).strip()

    except Exception as e:
        print("OCR extraction failed:", str(e))
        return ""


def load_pdf(file_obj):
    """
    Hybrid PDF loader:
    1. Docling
    2. pdfplumber fallback
    3. OCR fallback
    """
    try:
        file_obj.seek(0)
        pdf_bytes = file_obj.read()

        if not pdf_bytes:
            return ""

        # 1. Docling
        text = _extract_with_docling(pdf_bytes)
        if len(text.strip()) > 50:
            print("Text extracted using Docling")
            return text

        # 2. pdfplumber
        text = _extract_with_pdfplumber(pdf_bytes)
        if len(text.strip()) > 50:
            print("Text extracted using pdfplumber fallback")
            return text

        # 3. OCR
        text = _extract_with_ocr(pdf_bytes)
        if len(text.strip()) > 50:
            print("Text extracted using OCR fallback")
            return text

        return ""

    except Exception as e:
        print("load_pdf failed:", str(e))
        return ""