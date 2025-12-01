"""
Pipeline RAG completo: busca + geração de resposta.
"""
import time
from typing import Optional

from src.config import (
    RAG_PROMPT_TEMPLATE, 
    RAG_PROMPT_TEMPLATE_WITH_HISTORY,
    TOP_K_RESULTS, 
    MIN_SIMILARITY_THRESHOLD,
    MAX_CONVERSATION_HISTORY,
    ENABLE_CONTEXT_COMPRESSION,
    CONTEXT_COMPRESSION_THRESHOLD,
    CONTEXT_COMPRESSION_TARGET_RATIO,
    CONTEXT_COMPRESSION_METHOD
)
from src.core.embeddings import get_embedding
from src.core.llm import generate_response
from src.data.database import search_similar
from src.core.logger import (
    rag_logger,
    log_rag_query,
    log_rag_result,
    log_rag_context
)
from src.core.conversation import conversation_manager, Conversation
from src.core.context_compression import smart_compress, extract_key_sentences


def _apply_context_compression(
    context: str, 
    question: str,
    enable_compression: bool = None
) -> dict:
    """
    Aplica compressão de contexto se habilitado e necessário.
    
    Args:
        context: Contexto original
        question: Pergunta do usuário
        enable_compression: Força habilitação/desabilitação (usa config se None)
        
    Returns:
        Dict com contexto (comprimido ou não) e métricas
    """
    # Verificar se compressão está habilitada
    should_compress = enable_compression if enable_compression is not None else ENABLE_CONTEXT_COMPRESSION
    
    if not should_compress:
        return {
            "context": context,
            "was_compressed": False,
            "original_size": len(context),
            "final_size": len(context),
            "compression_ratio": 0.0,
            "compression_time_ms": 0
        }
    
    # Aplicar compressão baseada no método configurado
    if CONTEXT_COMPRESSION_METHOD == "heuristic":
        # Método rápido usando heurísticas
        original_size = len(context)
        if original_size > CONTEXT_COMPRESSION_THRESHOLD:
            # Calcular número de sentenças alvo baseado na razão
            max_sentences = max(5, int(10 * CONTEXT_COMPRESSION_TARGET_RATIO))
            compressed = extract_key_sentences(context, question, max_sentences)
            return {
                "context": compressed,
                "was_compressed": True,
                "original_size": original_size,
                "final_size": len(compressed),
                "compression_ratio": (1 - len(compressed) / original_size) * 100,
                "compression_time_ms": 0
            }
        return {
            "context": context,
            "was_compressed": False,
            "original_size": original_size,
            "final_size": original_size,
            "compression_ratio": 0.0,
            "compression_time_ms": 0
        }
    else:
        # Método LLM (padrão) - mais preciso
        return smart_compress(
            context=context,
            question=question,
            compression_threshold=CONTEXT_COMPRESSION_THRESHOLD,
            target_ratio=CONTEXT_COMPRESSION_TARGET_RATIO
        )


def query_rag(
    question: str,
    top_k: int = TOP_K_RESULTS,
    temperature: float = 0.7,
    include_sources: bool = True,
    min_similarity: float = None,
    enable_compression: bool = None
) -> dict:
    """
    Executa o pipeline RAG completo.
    
    1. Gera embedding da pergunta
    2. Busca chunks similares no pgvector
    3. Monta o contexto
    4. Comprime o contexto se necessário
    5. Gera resposta com o LLM
    
    Args:
        question: Pergunta do usuário
        top_k: Número de chunks a recuperar
        temperature: Temperatura para geração
        include_sources: Se True, inclui as fontes na resposta
        min_similarity: Similaridade mínima para considerar um chunk (usa config se None)
        enable_compression: Força habilitação/desabilitação da compressão (usa config se None)
        
    Returns:
        Dict com answer, sources e metadata
    """
    start_time = time.time()
    log_rag_query(question, top_k)
    
    # 1. Gerar embedding da pergunta
    rag_logger.debug("Generating question embedding...")
    question_embedding = get_embedding(question)
    
    # 2. Buscar chunks similares (já aplica filtro de similaridade mínima)
    rag_logger.debug("Searching similar documents...")
    similar_docs = search_similar(question_embedding, top_k=top_k, min_similarity=min_similarity)
    
    if not similar_docs:
        rag_logger.warning("No similar documents found (all filtered by similarity threshold)")
        return {
            "answer": "Não encontrei documentos suficientemente relevantes para responder sua pergunta. "
                      "Tente reformular a pergunta ou verifique se o tema está nos documentos indexados.",
            "sources": [],
            "context_used": "",
            "chunks_retrieved": 0
        }
    
    # 3. Montar contexto
    context_parts = []
    sources = []
    
    for doc in similar_docs:
        # Normalizar quebras de linha dentro do chunk para exibição
        content = doc["content"].replace("\n\n", " ").replace("\n", " ")
        context_parts.append(content)
        
        source_info = {
            "source": doc["metadata"].get("source", "Desconhecido"),
            "page": doc["metadata"].get("page", "N/A"),
            "similarity": round(doc["similarity"], 4)
        }
        sources.append(source_info)
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Log do contexto montado
    log_rag_context(context, sources)
    
    # 4. Aplicar compressão de contexto se necessário
    compression_result = _apply_context_compression(context, question, enable_compression)
    context = compression_result["context"]
    
    if compression_result["was_compressed"]:
        rag_logger.info(
            f"Context compressed: {compression_result['original_size']} -> "
            f"{compression_result['final_size']} chars "
            f"({compression_result['compression_ratio']:.1f}% reduction)"
        )
    
    # 5. Montar prompt final
    prompt = RAG_PROMPT_TEMPLATE.format(
        contexto=context,
        pergunta=question
    )
    
    # 6. Gerar resposta
    rag_logger.debug("Generating LLM response...")
    answer = generate_response(prompt, temperature=temperature)
    
    result = {
        "answer": answer,
        "context_used": context,
        "chunks_retrieved": len(similar_docs),
        "compression": {
            "was_compressed": compression_result["was_compressed"],
            "original_size": compression_result["original_size"],
            "final_size": compression_result["final_size"],
            "compression_ratio": compression_result["compression_ratio"],
            "compression_time_ms": compression_result["compression_time_ms"]
        }
    }
    
    if include_sources:
        result["sources"] = sources
    
    # Log final
    total_duration = time.time() - start_time
    source_names = [s["source"] for s in sources]
    log_rag_result(len(similar_docs), source_names, total_duration)
    
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
    
    log_rag_query(question, top_k)
    rag_logger.info("Starting RAG stream query")
    
    # 1. Gerar embedding da pergunta
    question_embedding = get_embedding(question)
    
    # 2. Buscar chunks similares
    similar_docs = search_similar(question_embedding, top_k=top_k)
    
    if not similar_docs:
        rag_logger.warning("No similar documents found for stream query")
        yield "Não encontrei documentos relevantes para responder sua pergunta."
        return
    
    # 3. Montar contexto
    context_parts = []
    for doc in similar_docs:
        # Normalizar quebras de linha dentro do chunk para exibição
        content = doc["content"].replace("\n\n", " ").replace("\n", " ")
        context_parts.append(content)
    
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
    
    rag_logger.debug("Starting LLM stream generation")
    for token in _generate_stream(payload):
        yield token


def search_only(
    question: str, 
    top_k: int = TOP_K_RESULTS,
    min_similarity: float = None
) -> list[dict]:
    """
    Apenas busca documentos similares, sem gerar resposta.
    Útil para debug e análise.
    
    Args:
        question: Pergunta/query do usuário
        top_k: Número de resultados
        min_similarity: Similaridade mínima (usa config se None, 0.0 para desabilitar)
        
    Returns:
        Lista de documentos similares com metadata
    """
    rag_logger.info(f"Search only query: '{question[:50]}...' (top_k={top_k})")
    
    question_embedding = get_embedding(question)
    similar_docs = search_similar(question_embedding, top_k=top_k, min_similarity=min_similarity)
    
    rag_logger.info(f"Search returned {len(similar_docs)} documents")
    
    return [
        {
            "content": doc["content"].replace("\n\n", " ").replace("\n", " "),
            "source": doc["metadata"].get("source", "Desconhecido"),
            "page": doc["metadata"].get("page", "N/A"),
            "similarity": round(doc["similarity"], 4)
        }
        for doc in similar_docs
    ]


def query_rag_with_history(
    question: str,
    session_id: Optional[str] = None,
    top_k: int = TOP_K_RESULTS,
    temperature: float = 0.7,
    include_sources: bool = True,
    min_similarity: float = None,
    enable_compression: bool = None
) -> dict:
    """
    Executa o pipeline RAG com suporte a histórico de conversas.
    
    Permite perguntas de follow-up mantendo o contexto da conversa.
    
    Args:
        question: Pergunta do usuário
        session_id: ID da sessão de conversa (cria nova se None)
        top_k: Número de chunks a recuperar
        temperature: Temperatura para geração
        include_sources: Se True, inclui as fontes na resposta
        min_similarity: Similaridade mínima para considerar um chunk
        enable_compression: Força habilitação/desabilitação da compressão (usa config se None)
        
    Returns:
        Dict com answer, sources, session_id e metadata
    """
    start_time = time.time()
    
    # Obter ou criar sessão
    session_id, conversation = conversation_manager.get_or_create_session(session_id)
    
    # Adicionar pergunta do usuário ao histórico
    conversation.add_message("user", question)
    
    rag_logger.info(f"Query with history - Session: {session_id[:8]}..., Messages: {len(conversation.messages)}")
    log_rag_query(question, top_k)
    
    # 1. Gerar embedding da pergunta
    rag_logger.debug("Generating question embedding...")
    question_embedding = get_embedding(question)
    
    # 2. Buscar chunks similares
    rag_logger.debug("Searching similar documents...")
    similar_docs = search_similar(question_embedding, top_k=top_k, min_similarity=min_similarity)
    
    if not similar_docs:
        rag_logger.warning("No similar documents found")
        no_result_answer = (
            "Não encontrei documentos suficientemente relevantes para responder sua pergunta. "
            "Tente reformular a pergunta ou verifique se o tema está nos documentos indexados."
        )
        conversation.add_message("assistant", no_result_answer)
        
        return {
            "answer": no_result_answer,
            "sources": [],
            "context_used": "",
            "chunks_retrieved": 0,
            "session_id": session_id,
            "message_count": len(conversation.messages)
        }
    
    # 3. Montar contexto
    context_parts = []
    sources = []
    
    for doc in similar_docs:
        content = doc["content"].replace("\n\n", " ").replace("\n", " ")
        context_parts.append(content)
        
        source_info = {
            "source": doc["metadata"].get("source", "Desconhecido"),
            "page": doc["metadata"].get("page", "N/A"),
            "similarity": round(doc["similarity"], 4)
        }
        sources.append(source_info)
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Log do contexto montado
    log_rag_context(context, sources)
    
    # 4. Aplicar compressão de contexto se necessário
    compression_result = _apply_context_compression(context, question, enable_compression)
    context = compression_result["context"]
    
    if compression_result["was_compressed"]:
        rag_logger.info(
            f"Context compressed: {compression_result['original_size']} -> "
            f"{compression_result['final_size']} chars "
            f"({compression_result['compression_ratio']:.1f}% reduction)"
        )
    
    # 5. Obter histórico da conversa
    history = conversation.get_history_for_prompt(max_messages=MAX_CONVERSATION_HISTORY)
    
    # 6. Montar prompt final (com ou sem histórico)
    if history:
        rag_logger.debug(f"Using conversation history ({len(history)} chars)")
        prompt = RAG_PROMPT_TEMPLATE_WITH_HISTORY.format(
            historico=history,
            contexto=context,
            pergunta=question
        )
    else:
        # Primeira pergunta da sessão, usar template simples
        prompt = RAG_PROMPT_TEMPLATE.format(
            contexto=context,
            pergunta=question
        )
    
    # 7. Gerar resposta
    rag_logger.debug("Generating LLM response...")
    answer = generate_response(prompt, temperature=temperature)
    
    # 8. Adicionar resposta ao histórico
    conversation.add_message("assistant", answer)
    
    result = {
        "answer": answer,
        "context_used": context,
        "chunks_retrieved": len(similar_docs),
        "session_id": session_id,
        "message_count": len(conversation.messages),
        "compression": {
            "was_compressed": compression_result["was_compressed"],
            "original_size": compression_result["original_size"],
            "final_size": compression_result["final_size"],
            "compression_ratio": compression_result["compression_ratio"],
            "compression_time_ms": compression_result["compression_time_ms"]
        }
    }
    
    if include_sources:
        result["sources"] = sources
    
    # Log final
    total_duration = time.time() - start_time
    source_names = [s["source"] for s in sources]
    log_rag_result(len(similar_docs), source_names, total_duration)
    
    return result


def get_conversation_history(session_id: str) -> Optional[dict]:
    """
    Retorna o histórico de uma conversa.
    
    Args:
        session_id: ID da sessão
        
    Returns:
        Dict com histórico ou None se sessão não existe
    """
    conversation = conversation_manager.get_session(session_id)
    if conversation is None:
        return None
    
    return conversation.to_dict()


def clear_conversation(session_id: str) -> bool:
    """
    Remove uma sessão de conversa.
    
    Args:
        session_id: ID da sessão
        
    Returns:
        True se removeu, False se não existia
    """
    return conversation_manager.delete_session(session_id)
