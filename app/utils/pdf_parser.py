"""
PDF Ingestion Utility for Aviation RAG (Production Hardened).
Handles the extraction and merging of raw text from PDF documents using LangChain loaders.
"""

from langchain_community.document_loaders import PyPDFLoader
from app.utils.cleaner import clean_text


def load_and_merge_pdf(path):
    """
    Loads all pages from a target PDF, merges them into a single string,
    and applies standard text cleaning rules.
    """
    loader = PyPDFLoader(path)
    docs = loader.load()

    full_text = " ".join([d.page_content for d in docs])
    cleaned = clean_text(full_text)

    return cleaned
