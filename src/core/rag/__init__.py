"""
Módulo RAG - Refatorado em Services.
"""
from .pipeline import (
    RAGPipeline, 
    query_rag, 
    query_rag_stream, 
    query_rag_with_history, 
    search_only,
    get_conversation_history,
    clear_conversation
)

__all__ = [
    "RAGPipeline", 
    "query_rag", 
    "query_rag_stream", 
    "query_rag_with_history", 
    "search_only",
    "get_conversation_history",
    "clear_conversation"
]
