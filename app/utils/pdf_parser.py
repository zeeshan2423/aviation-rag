from langchain_community.document_loaders import PyPDFLoader
from app.utils.cleaner import clean_text


def load_and_merge_pdf(path):
    """Load and merge PDF"""
    loader = PyPDFLoader(path)
    docs = loader.load()

    full_text = " ".join([d.page_content for d in docs])
    cleaned = clean_text(full_text)

    return cleaned
