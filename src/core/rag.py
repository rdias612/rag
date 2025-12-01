"""
Pipeline RAG completo: busca + geração de resposta.
"""
from typing import Optional

from src.config import RAG_PROMPT_TEMPLATE, TOP_K_RESULTS
from src.core.embeddings import get_embedding
from src.core.llm import generate_response
from src.data.database import search_similar


def query_rag(
    question: str,
    top_k: int = TOP_K_RESULTS,
    temperature: float = 0.7,
    include_sources: bool = True
) -> dict:
    """
    Executa o pipeline RAG completo.
    
    1. Gera embedding da pergunta
    2. Busca chunks similares no pgvector
    3. Monta o contexto
    4. Gera resposta com o LLM
    
    Args:
        question: Pergunta do usuário
        top_k: Número de chunks a recuperar
        temperature: Temperatura para geração
        include_sources: Se True, inclui as fontes na resposta
        
    Returns:
        Dict com answer, sources e metadata
    """
    # 1. Gerar embedding da pergunta
    question_embedding = get_embedding(question)
    
    # 2. Buscar chunks similares
    similar_docs = search_similar(question_embedding, top_k=top_k)
    
    if not similar_docs:
        return {
            "answer": "Não encontrei documentos relevantes para responder sua pergunta.",
            "sources": [],
            "context_used": ""
        }
    
    # 3. Montar contexto
    context_parts = []
    sources = []
    
    for doc in similar_docs:
        context_parts.append(doc["content"])
        
        source_info = {
            "source": doc["metadata"].get("source", "Desconhecido"),
            "page": doc["metadata"].get("page", "N/A"),
            "similarity": round(doc["similarity"], 4)
        }
        sources.append(source_info)
    
    context = "\n\n---\n\n".join(context_parts)
    
    # 4. Montar prompt final
    prompt = RAG_PROMPT_TEMPLATE.format(
        contexto=context,
        pergunta=question
    )
    
    # 5. Gerar resposta
    answer = generate_response(prompt, temperature=temperature)
    
    result = {
        "answer": answer,
        "context_used": context,
        "chunks_retrieved": len(similar_docs)
    }
    
    if include_sources:
        result["sources"] = sources
    
    return result


def query_rag_stream(
    question: str,
    top_k: int = TOP_K_RESULTS,
    temperature: float = 0.7
):
    """
    Executa o pipeline RAG com streaming da resposta.
    
    Yields:
        Tokens da resposta conforme são gerados
    """
    from src.core.llm import _generate_stream
    from src.config import LLM_MODEL, LM_STUDIO_BASE_URL
    
    # 1. Gerar embedding da pergunta
    question_embedding = get_embedding(question)
    
    # 2. Buscar chunks similares
    similar_docs = search_similar(question_embedding, top_k=top_k)
    
    if not similar_docs:
        yield "Não encontrei documentos relevantes para responder sua pergunta."
        return
    
    # 3. Montar contexto
    context_parts = [doc["content"] for doc in similar_docs]
    context = "\n\n---\n\n".join(context_parts)
    
    # 4. Montar prompt final
    prompt = RAG_PROMPT_TEMPLATE.format(
        contexto=context,
        pergunta=question
    )
    
    # 5. Gerar resposta em streaming
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": temperature,
        "stream": True
    }
    
    for token in _generate_stream(payload):
        yield token


def search_only(question: str, top_k: int = TOP_K_RESULTS) -> list[dict]:
    """
    Apenas busca documentos similares, sem gerar resposta.
    Útil para debug e análise.
    
    Args:
        question: Pergunta/query do usuário
        top_k: Número de resultados
        
    Returns:
        Lista de documentos similares com metadata
    """
    question_embedding = get_embedding(question)
    similar_docs = search_similar(question_embedding, top_k=top_k)
    
    return [
        {
            "content": doc["content"],
            "source": doc["metadata"].get("source", "Desconhecido"),
            "page": doc["metadata"].get("page", "N/A"),
            "similarity": round(doc["similarity"], 4)
        }
        for doc in similar_docs
    ]
