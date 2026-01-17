import io
from pypdf import PdfReader

class Parser:
    @staticmethod
    def from_pdf(pdf_bytes: bytes):
        # Wrap bytes in a file-like object
        bytes_stream = io.BytesIO(pdf_bytes)
        
        # Initialize the reader
        reader = PdfReader(bytes_stream)
        
        # Iterate and extract text from each page
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"
            
        return full_text

    @staticmethod
    def from_txt(txt_bytes: bytes):
        return
    
    @staticmethod
    def from_docx(docx_bytes: bytes):
        return