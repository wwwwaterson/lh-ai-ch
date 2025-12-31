import fitz


def extract_text_from_pdf_sync(file_path: str) -> tuple[str, int]:
    """
    Synchronous PDF text extraction function.
    
    This function performs CPU-intensive PDF parsing and should be executed
    in a separate process via ProcessPoolExecutor to avoid blocking the
    async event loop.
    
    Args:
        file_path: Path to the PDF file to process
        
    Returns:
        Tuple of (extracted_text, page_count)
    """
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    page_count = len(doc)
    doc.close()
    return text, page_count

