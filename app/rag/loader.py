import pdfplumber
import pytesseract
import pypdfium2

pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"
def load_pdf(file):

    text = ""

    # try normal extraction
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    if len(text.strip()) > 50:
        return text

    print("Running OCR fallback...")

    # OCR fallback
    pdf = pypdfium2.PdfDocument(file)

    for page in pdf:
        img = page.render(scale=300/72).to_pil()
        page_text = pytesseract.image_to_string(img)
        text += page_text + "\n"

    return text