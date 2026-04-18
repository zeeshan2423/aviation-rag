"""
This module provides services for generating embeddings using the Voyage AI API.
"""
import os

from dotenv import load_dotenv
from langchain_voyageai import VoyageAIEmbeddings

load_dotenv()

def get_embedding_model():
    return VoyageAIEmbeddings(
        voyage_api_key=os.getenv("VOYAGE_API_KEY"),
        model="voyage-large-2"
    )

