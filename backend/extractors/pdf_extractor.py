from io import BytesIO
from pdfminer.high_level import extract_text

def extract_text_from_pdf(file_bytes: bytes) -> str:
    bio = BytesIO(file_bytes)
    text = extract_text(bio)
    return text or ""
