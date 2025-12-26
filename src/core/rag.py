"""
Pipeline RAG completo: busca + geração de resposta.
"""
import time
from typing import Optional

from src.config import (
    RAG_PROMPT_TEMPLATE, 
    RAG_PROMPT_TEMPLATE_WITH_HISTORY,
    RAG_PROMPT_ENHANCED,
    RAG_PROMPT_ENHANCED_WITH_HISTORY,
    TOP_K_RESULTS, 
    MIN_SIMILARITY_THRESHOLD,
    MAX_CONVERSATION_HISTORY,
    ENABLE_CONTEXT_COMPRESSION,
    CONTEXT_COMPRESSION_THRESHOLD,
    CONTEXT_COMPRESSION_TARGET_RATIO,
    CONTEXT_COMPRESSION_METHOD,
    ENABLE_HYBRID_SEARCH,
    HYBRID_SEARCH_ALPHA,
    USE_QUESTION_CLASSIFIER,
    USE_ENHANCED_PROMPTS,
    # Phase 2
    ENABLE_RERANKING,
    RERANKING_TOP_K_INITIAL,
    ENABLE_QUERY_EXPANSION,
    QUERY_EXPANSION_COUNT,
    ENABLE_MMR,
    MMR_LAMBDA,
    # Phase 3
    ENABLE_HYDE,
    HYDE_WEIGHT
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
from src.core.question_classifier import (
    classify_question,
    get_instructions_for_type,
    get_question_type_description
)
from src.core.metrics import (
    LatencyTracker,
    inc_query,
    observe_chunks_retrieved,
    observe_compression_ratio,
    inc_error
)

# Phase 2 imports (lazy loaded quando necessário)
def _get_reranker():
    from src.core.reranker import rerank_chunks, CROSS_ENCODER_AVAILABLE
    return rerank_chunks, CROSS_ENCODER_AVAILABLE

def _get_query_expansion():
    from src.core.query_expansion import expand_query, merge_search_results
    return expand_query, merge_search_results

def _get_mmr():
    from src.core.mmr import mmr_rerank
    return mmr_rerank

# Phase 3 imports
def _get_hyde():
    from src.core.hyde import hyde_enhanced_query
    return hyde_enhanced_query


def _search_documents(
    question: str,
    question_embedding: list[float],
    top_k: int,
    min_similarity: float = None,
    use_hybrid: bool = None,
    hybrid_alpha: float = None,
    collection_id: str = None
) -> tuple[list[dict], dict]:
    """
    Busca documentos usando busca vetorial ou híbrida.
    
    Args:
        question: Texto da pergunta
        question_embedding: Embedding da pergunta
        top_k: Número de resultados
        min_similarity: Similaridade mínima
        use_hybrid: Força uso de busca híbrida (usa config se None)
        hybrid_alpha: Peso da busca vetorial (usa config se None)
        collection_id: Filtrar por coleção específica
        
    Returns:
        Tupla (lista de documentos, métricas de busca)
    """
    should_use_hybrid = use_hybrid if use_hybrid is not None else ENABLE_HYBRID_SEARCH
    
    search_metrics = {
        "search_type": "hybrid" if should_use_hybrid else "vector",
        "hybrid_alpha": None,
        "vector_results": 0,
        "fts_results": 0
    }
    
    if should_use_hybrid:
        try:
            from src.data.hybrid_search import search_hybrid, check_fulltext_ready
            
            # Verificar se FTS está configurado
            if not check_fulltext_ready():
                rag_logger.warning("Full-Text Search not ready, falling back to vector search")
                search_metrics["search_type"] = "vector"
                search_metrics["fallback_reason"] = "FTS not initialized"
                return search_similar(question_embedding, top_k=top_k, min_similarity=min_similarity, collection_id=collection_id), search_metrics
            
            alpha = hybrid_alpha if hybrid_alpha is not None else HYBRID_SEARCH_ALPHA
            search_metrics["hybrid_alpha"] = alpha
            
            # TODO: Atualizar search_hybrid para suportar collection_id
            # Por enquanto, fallback para busca vetorial se collection_id for usado
            if collection_id:
                 rag_logger.warning("Hybrid search does not support collection_id yet, falling back to vector search")
                 return search_similar(question_embedding, top_k=top_k, min_similarity=min_similarity, collection_id=collection_id), search_metrics

            results = search_hybrid(
                query=question,
                query_embedding=question_embedding,
                top_k=top_k,
                alpha=alpha,
                min_similarity=min_similarity
            )
            
            # Extrair métricas dos resultados
            if results:
                vector_contrib = sum(1 for r in results if r.get('vector_contribution', 0) > 0)
                fts_contrib = sum(1 for r in results if r.get('fts_contribution', 0) > 0)
                search_metrics["vector_results"] = vector_contrib
                search_metrics["fts_results"] = fts_contrib
            
            return results, search_metrics
            
        except ImportError as e:
            rag_logger.warning(f"Hybrid search module not available: {e}")
            search_metrics["search_type"] = "vector"
            search_metrics["fallback_reason"] = str(e)
    
    # Busca vetorial padrão
    return search_similar(question_embedding, top_k=top_k, min_similarity=min_similarity, collection_id=collection_id), search_metrics


def _apply_phase2_pipeline(
    question: str,
    question_embedding: list[float],
    initial_results: list[dict],
    final_top_k: int,
    search_metrics: dict
) -> tuple[list[dict], dict]:
    """
    Aplica pipeline Phase 2: Query Expansion, MMR e Re-ranking.
    
    Args:
        question: Pergunta do usuário
        question_embedding: Embedding da pergunta
        initial_results: Resultados da busca inicial
        final_top_k: Número final de resultados desejados
        search_metrics: Métricas da busca para atualização
        
    Returns:
        Tupla (resultados processados, métricas atualizadas)
    """
    results = initial_results
    phase2_metrics = {
        "query_expanded": False,
        "mmr_applied": False,
        "reranking_applied": False
    }
    
    # 1. Query Expansion (busca adicional com variações)
    if ENABLE_QUERY_EXPANSION and len(results) > 0:
        try:
            expand_query, merge_search_results = _get_query_expansion()
            
            # Gerar variações da query
            query_variations = expand_query(question, QUERY_EXPANSION_COUNT)
            
            if len(query_variations) > 1:
                rag_logger.info(f"Query expanded to {len(query_variations)} variations")
                phase2_metrics["query_expanded"] = True
                phase2_metrics["query_variations"] = len(query_variations)
                
                # Buscar com cada variação (além da original já buscada)
                all_results = [results]  # Resultados originais
                
                for variation in query_variations[1:]:  # Pular original
                    var_embedding = get_embedding(variation)
                    var_results, _ = _search_documents(
                        question=variation,
                        question_embedding=var_embedding,
                        top_k=RERANKING_TOP_K_INITIAL if ENABLE_RERANKING else final_top_k,
                        use_hybrid=ENABLE_HYBRID_SEARCH
                    )
                    if var_results:
                        all_results.append(var_results)
                
                # Merge resultados com RRF
                results = merge_search_results(all_results, top_k=len(results) * 2)
                
        except Exception as e:
            rag_logger.warning(f"Query expansion failed: {e}")
    
    # 2. MMR para diversidade
    if ENABLE_MMR and len(results) > final_top_k:
        try:
            mmr_rerank = _get_mmr()
            
            results = mmr_rerank(
                query_embedding=question_embedding,
                chunks=results,
                top_k=RERANKING_TOP_K_INITIAL if ENABLE_RERANKING else final_top_k,
                lambda_param=MMR_LAMBDA
            )
            
            phase2_metrics["mmr_applied"] = True
            rag_logger.info(f"MMR applied: {len(initial_results)} -> {len(results)} chunks")
            
        except Exception as e:
            rag_logger.warning(f"MMR failed: {e}")
    
    # 3. Re-ranking com Cross-Encoder
    if ENABLE_RERANKING and len(results) > 0:
        try:
            rerank_chunks, CROSS_ENCODER_AVAILABLE = _get_reranker()
            
            if CROSS_ENCODER_AVAILABLE:
                results = rerank_chunks(
                    query=question,
                    chunks=results,
                    top_k=final_top_k
                )
                
                phase2_metrics["reranking_applied"] = True
                rag_logger.info(f"Reranking applied: top {final_top_k} selected")
            else:
                rag_logger.warning("Cross-encoder not available, skipping reranking")
                results = results[:final_top_k]
                
        except Exception as e:
            rag_logger.warning(f"Reranking failed: {e}")
            results = results[:final_top_k]
    else:
        results = results[:final_top_k]
    
    # Atualizar métricas
    search_metrics["phase2"] = phase2_metrics
    
    return results, search_metrics

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
        )


def _build_prompt(
    context: str,
    question: str,
    question_type: str = None,
    history: str = None
) -> str:
    """
    Constrói o prompt final baseado no tipo de pergunta e configurações.
    
    Args:
        context: Contexto dos documentos
        question: Pergunta do usuário
        question_type: Tipo da pergunta (de classify_question)
        history: Histórico da conversa (opcional)
        
    Returns:
        Prompt formatado para o LLM
    """
    # Obter instruções específicas para o tipo de pergunta
    instrucoes_tipo = ""
    if question_type and USE_ENHANCED_PROMPTS:
        instrucoes_tipo = get_instructions_for_type(question_type)
    
    # Escolher template baseado nas configurações
    if USE_ENHANCED_PROMPTS:
        if history:
            return RAG_PROMPT_ENHANCED_WITH_HISTORY.format(
                historico=history,
                contexto=context,
                pergunta=question,
                instrucoes_tipo=instrucoes_tipo
            )
        else:
            return RAG_PROMPT_ENHANCED.format(
                contexto=context,
                pergunta=question,
                instrucoes_tipo=instrucoes_tipo
            )
    else:
        # Templates originais (sem instruções por tipo)
        if history:
            return RAG_PROMPT_TEMPLATE_WITH_HISTORY.format(
                historico=history,
                contexto=context,
                pergunta=question
            )
        else:
            return RAG_PROMPT_TEMPLATE.format(
                contexto=context,
                pergunta=question
            )


def _build_no_results_response(
    question: str,
    question_type: str,
    search_metrics: dict
) -> dict:
    """
    Constrói resposta inteligente quando não há documentos relevantes.
    
    Args:
        question: Pergunta original do usuário
        question_type: Tipo da pergunta classificada
        search_metrics: Métricas da busca realizada
        
    Returns:
        Dict com resposta de fallback e metadata
    """
    # Mensagem base
    base_message = "Não encontrei documentos suficientemente relevantes para responder sua pergunta."
    
    # Sugestões baseadas no tipo de pergunta
    suggestions = []
    
    if question_type == "definition":
        suggestions.append("Tente usar termos mais específicos ou o nome completo do conceito.")
    elif question_type == "comparison":
        suggestions.append("Verifique se ambos os itens comparados estão nos documentos indexados.")
    elif question_type == "listing":
        suggestions.append("Tente perguntar sobre categorias ou tópicos específicos.")
    elif question_type == "procedure":
        suggestions.append("Verifique se há documentação de processos ou tutoriais indexados.")
    
    # Sugestões gerais
    suggestions.append("Reformule a pergunta usando palavras-chave diferentes.")
    suggestions.append("Verifique se o tema está coberto nos documentos indexados.")
    
    # Montar mensagem final
    suggestion_text = "\n".join(f"• {s}" for s in suggestions)
    full_message = f"{base_message}\n\n**Sugestões:**\n{suggestion_text}"
    
    return {
        "answer": full_message,
        "sources": [],
        "context_used": "",
        "chunks_retrieved": 0,
        "question_type": question_type,
        "search": search_metrics,
        "fallback": True
    }


def query_rag(
    question: str,
    top_k: int = TOP_K_RESULTS,
    temperature: float = 0.7,
    include_sources: bool = True,
    min_similarity: float = None,
    enable_compression: bool = None,
    use_hybrid_search: bool = None,
    hybrid_alpha: float = None,
    collection_id: str = None
) -> dict:
    """
    Executa o pipeline RAG completo.
    
    1. Gera embedding da pergunta
    2. Busca chunks similares (vetorial ou híbrida)
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
        use_hybrid_search: Força uso de busca híbrida (usa config se None)
        hybrid_alpha: Peso da busca vetorial na busca híbrida (usa config se None)
        collection_id: Filtrar por coleção específica (opcional)
        
    Returns:
        Dict com answer, sources e metadata
    """
    start_time = time.time()
    log_rag_query(question, top_k)
    
    # 1. Gerar embedding da pergunta
    rag_logger.debug("Generating question embedding...")
    with LatencyTracker('embedding'):
        question_embedding = get_embedding(question)
    
    # Phase 3: HyDE - usar embedding de documento hipotético
    hyde_metrics = {"hyde_applied": False}
    if ENABLE_HYDE:
        try:
            hyde_enhanced_query = _get_hyde()
            question_embedding, hyde_metrics = hyde_enhanced_query(
                question=question,
                original_embedding=question_embedding,
                hyde_weight=HYDE_WEIGHT
            )
            rag_logger.info("HyDE embedding applied")
        except Exception as e:
            rag_logger.warning(f"HyDE failed, using original embedding: {e}")
    
    # 2. Buscar chunks similares (vetorial ou híbrida)
    # Phase 2: Buscar mais chunks inicialmente se re-ranking estiver habilitado
    initial_top_k = RERANKING_TOP_K_INITIAL if ENABLE_RERANKING else top_k
    
    rag_logger.debug(f"Searching similar documents (initial top_k={initial_top_k})...")
    with LatencyTracker('search'):
        similar_docs, search_metrics = _search_documents(
            question=question,
            question_embedding=question_embedding,
            top_k=initial_top_k,
            min_similarity=min_similarity,
            use_hybrid=use_hybrid_search,
            hybrid_alpha=hybrid_alpha,
            collection_id=collection_id
        )
    
    # Adicionar métricas HyDE
    search_metrics["hyde"] = hyde_metrics
    
    # Phase 2: Aplicar Query Expansion, MMR e Re-ranking
    if similar_docs and (ENABLE_QUERY_EXPANSION or ENABLE_MMR or ENABLE_RERANKING):
        with LatencyTracker('rerank'):
            similar_docs, search_metrics = _apply_phase2_pipeline(
                question=question,
                question_embedding=question_embedding,
                initial_results=similar_docs,
                final_top_k=top_k,
                search_metrics=search_metrics
            )
    
    # Classificar tipo de pergunta (Phase 1)
    question_type = None
    if USE_QUESTION_CLASSIFIER:
        question_type = classify_question(question)
        rag_logger.debug(f"Question classified as: {question_type}")
    
    if not similar_docs:
        rag_logger.warning("No similar documents found (all filtered by similarity threshold)")
        inc_query(status='no_results', question_type=question_type or 'unknown')
        return _build_no_results_response(question, question_type, search_metrics)
    
    # 3. Montar contexto
    context_parts = []
    sources = []
    
    for doc in similar_docs:
        # Normalizar quebras de linha dentro do chunk para exibição
        content = doc["content"].replace("\n\n", " ").replace("\n", " ")
        
        # Enriquecer com metadados contextuais (Contextual Chunking)
        metadata = doc.get("metadata", {})
        chunk_context = []
        
        # Adicionar título da seção se disponível
        if metadata.get("possible_section"):
            chunk_context.append(f"Seção: {metadata['possible_section']}")
            
        # Adicionar contexto anterior (se disponível)
        if metadata.get("prev_chunk_text"):
            prev_text = metadata["prev_chunk_text"][-200:] # Últimos 200 chars
            chunk_context.append(f"[Contexto Anterior: ...{prev_text}]")
            
        # Conteúdo principal
        chunk_context.append(f"Conteúdo: {content}")
        
        # Adicionar contexto posterior (se disponível)
        if metadata.get("next_chunk_text"):
            next_text = metadata["next_chunk_text"][:200] # Primeiros 200 chars
            chunk_context.append(f"[Contexto Posterior: {next_text}...]")
            
        # Juntar tudo
        if len(chunk_context) > 1:
            full_chunk_text = "\n".join(chunk_context)
        else:
            full_chunk_text = content
            
        context_parts.append(full_chunk_text)
        
        source_info = {
            "source": doc["metadata"].get("source", "Desconhecido"),
            "page": doc["metadata"].get("page", "N/A"),
            "similarity": round(doc.get("similarity", 0), 4)
        }
        
        # Adicionar info de busca híbrida se disponível
        if "hybrid_score" in doc:
            source_info["hybrid_score"] = round(doc["hybrid_score"], 4)
        
        sources.append(source_info)
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Log do contexto montado
    log_rag_context(context, sources)
    
    # 4. Aplicar compressão de contexto se necessário
    with LatencyTracker('compression'):
        compression_result = _apply_context_compression(context, question, enable_compression)
    context = compression_result["context"]
    
    # Registrar razão de compressão nas métricas
    if compression_result["was_compressed"]:
        observe_compression_ratio(compression_result["compression_ratio"] / 100.0)
    
    if compression_result["was_compressed"]:
        rag_logger.info(
            f"Context compressed: {compression_result['original_size']} -> "
            f"{compression_result['final_size']} chars "
            f"({compression_result['compression_ratio']:.1f}% reduction)"
        )
    
    # 5. Montar prompt final (com suporte a prompts melhorados Phase 1)
    prompt = _build_prompt(
        context=context,
        question=question,
        question_type=question_type,
        history=None
    )
    
    # 6. Gerar resposta
    rag_logger.debug("Generating LLM response...")
    with LatencyTracker('llm'):
        answer = generate_response(prompt, temperature=temperature)
    
    result = {
        "answer": answer,
        "context_used": context,
        "chunks_retrieved": len(similar_docs),
        "search": search_metrics,
        "question_type": question_type,
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
    
    # Métricas Prometheus
    inc_query(status='success', question_type=question_type or 'unknown')
    observe_chunks_retrieved(len(similar_docs))
    
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
        
        # Enriquecer com metadados contextuais (Contextual Chunking)
        metadata = doc.get("metadata", {})
        chunk_context = []
        
        if metadata.get("possible_section"):
            chunk_context.append(f"Seção: {metadata['possible_section']}")
            
        if metadata.get("prev_chunk_text"):
            prev_text = metadata["prev_chunk_text"][-200:]
            chunk_context.append(f"[Contexto Anterior: ...{prev_text}]")
            
        chunk_context.append(f"Conteúdo: {content}")
        
        if metadata.get("next_chunk_text"):
            next_text = metadata["next_chunk_text"][:200]
            chunk_context.append(f"[Contexto Posterior: {next_text}...]")
            
        if len(chunk_context) > 1:
            full_chunk_text = "\n".join(chunk_context)
        else:
            full_chunk_text = content
            
        context_parts.append(full_chunk_text)
    
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
    enable_compression: bool = None,
    use_hybrid_search: bool = None,
    hybrid_alpha: float = None,
    collection_id: str = None
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
        use_hybrid_search: Força uso de busca híbrida (usa config se None)
        hybrid_alpha: Peso da busca vetorial na busca híbrida (usa config se None)
        
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
    
    # 2. Buscar chunks similares (vetorial ou híbrida)
    rag_logger.debug("Searching similar documents...")
    similar_docs, search_metrics = _search_documents(
        question=question,
        question_embedding=question_embedding,
        top_k=top_k,
        min_similarity=min_similarity,
        use_hybrid=use_hybrid_search,
        hybrid_alpha=hybrid_alpha,
        collection_id=collection_id
    )
    
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
            "message_count": len(conversation.messages),
            "search": search_metrics
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
            "similarity": round(doc.get("similarity", 0), 4)
        }
        
        # Adicionar info de busca híbrida se disponível
        if "hybrid_score" in doc:
            source_info["hybrid_score"] = round(doc["hybrid_score"], 4)
        
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
        "search": search_metrics,
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
