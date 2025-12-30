"""
Módulo RAG - Fachada de compatibilidade.
Delega chamadas para o novo sistema modular em src.core.rag.
"""
from src.core.rag.pipeline import (
    query_rag,
    query_rag_stream,
    query_rag_with_history,
    search_only,
    get_conversation_history,
    clear_conversation,
    RAGPipeline
)

# Exportar funções principais para manter compatibilidade com imports antigos
__all__ = [
    "query_rag",
    "query_rag_stream",
    "query_rag_with_history",
    "search_only",
    "get_conversation_history",
    "clear_conversation",
    "RAGPipeline"
]

# Nota: As funções auxiliares _search_documents, _build_prompt, etc. 
# foram migradas para SearchService, PromptService, etc.
