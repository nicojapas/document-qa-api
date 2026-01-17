import re

from langchain_text_splitters import RecursiveCharacterTextSplitter


def clean_text(text: str) -> str:
    # 1. Replace multiple newlines/spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # 2. Remove non-printable characters (sometimes found in old PDFs)
    text = "".join(char for char in text if char.isprintable())
    
    # 3. Strip leading/trailing whitespace
    return text.strip()


def split_and_process_text(text: str, should_clean: bool = True):
    if should_clean:
        text = clean_text(text)
        
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        
    return text_splitter.split_text(text)

