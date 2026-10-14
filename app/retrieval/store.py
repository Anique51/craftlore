from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import settings

COLLECTION = "craftlore"


def get_embeddings():
    return HuggingFaceEmbeddings(model_name=settings.embed_model)


def get_vectorstore():
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )
