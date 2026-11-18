"""Turn uploaded PDFs into LangChain Document chunks."""

from io import BytesIO

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def pdf_to_pages(file_name, file_bytes):
    """Return one Document per PDF page. Empty pages are skipped."""
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(
                Document(page_content=text, metadata={"source": file_name, "page": number})
            )
    return pages


def split_pages(pages, chunk_size, chunk_overlap):
    """Split pages into chunks. Each chunk keeps its source and page number."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(pages)
