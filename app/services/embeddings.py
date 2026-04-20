"""
Embeddings Service for Aviation RAG.
Generates vector representations of documents and queries using Voyage AI.
"""

import os

from dotenv import load_dotenv
from langchain_voyageai import VoyageAIEmbeddings

load_dotenv()


def get_embedding_model():
    """
    Initializes and returns the Voyage AI embedding model.
    """
    return VoyageAIEmbeddings(
        voyage_api_key=os.getenv("VOYAGE_API_KEY"),
        model="voyage-large-2"
    )
