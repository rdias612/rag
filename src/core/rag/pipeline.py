"""
Pipeline RAG principal - orquestrador modular.
"""
import time
import logging
from typing import Optional, Dict, Any, List, Literal

from src.config import (
    TOP_K_RESULTS,
    MIN_SIMILARITY_THRESHOLD,
    ENABLE_SELF_RAG,
    SELF_RAG_MIN_SCORE,
    SELF_RAG_MAX_ITERATIONS,
    ENABLE_ADAPTIVE_RETRIEVAL,
    ENABLE_AUTO_EVALUATION,
    EVALUATION_MIN_SCORE_THRESHOLD,
    SENTENCE_WINDOW_SIZE
)
from src.core.embeddings import get_embedding
from src.core.llm import generate_response
from src.core.question_classifier import classify_question
from src.core.query_expansion import expand_query
from src.core.metrics import LatencyTracker, inc_query, observe_chunks_retrieved, inc_error
from src.core.conversation import conversation_manager
from src.core.self_rag import self_rag_pipeline
from src.core.adaptive_retrieval import get_adaptive_params
from src.data.repositories.adaptive_retrieval_repository import adaptive_retrieval_repo
from src.data.repositories.evaluation_repository import evaluation_repo
from src.core.evaluation import evaluate_rag_response

from src.core.rag.services.search_service import SearchService
from src.core.rag.services.context_service import ContextService
from src.core.rag.services.prompt_service import PromptService
from src.core.rag.services.response_service import ResponseService
from src.core.rag.strategies.retrieval_strategy import RetrievalStrategy
from src.core.logger import log_stage, log_step, log_error

logger = logging.getLogger("rag.pipeline")


def determine_search_strategy(question: str) -> Literal["hierarchical", "sentence"]:
    """
    Decide automaticamente qual estratégia de chunking usar baseada na pergunta.
    
    Heurística:
    - Perguntas curtas/diretas → Sentence Window (mais preciso)
    - Perguntas explicativas → Hierarchical (mais contexto)
    - Padrão: Hierarchical (mais seguro)
    
    Args:
        question: Texto da pergunta do usuário
        
    Returns:
        'hierarchical' ou 'sentence'
    """
    question_lower = question.lower()
    words = question.split()
    
    # Critério 1: Perguntas muito curtas (até 5 palavras)
    if len(words) <= 5:
        return "sentence"
    
    # Critério 2: Indicadores de perguntas específicas/diretas
    specific_indicators = [
        "qual é", "o que é", "quanto custa", "onde fica", 
        "quem é", "qual", "quanto", "onde", "quem",
        "qual o valor", "qual o nome", "quanto tempo"
    ]
    if any(ind in question_lower for ind in specific_indicators):
        return "sentence"
    
    # Critério 3: Indicadores de perguntas explicativas
    explanatory_indicators = [
        "como funciona", " pq ", "por que", "porque", "como fazer",
        "explique", "detalhe", "descreva", "o processo de",
        "como pode", "de que forma", "de que maneira", "de qual maneira", "de que jeito", "de qual jeito"
    ]
    if any(ind in question_lower for ind in explanatory_indicators):
        return "hierarchical"
    
    # Critério 4: Perguntas começando com "como"
    if question_lower.startswith("como "):
        return "hierarchical"
    
    # Padrão: Hierarchical (mais seguro)
    return "hierarchical"


class RAGPipeline:
    """Orquestrador do pipeline RAG com injeção de dependências."""
    
    def __init__(
        self,
        search_service: SearchService = None,
        context_service: ContextService = None,
        prompt_service: PromptService = None,
        response_service: ResponseService = None,
        retrieval_strategy: RetrievalStrategy = None
    ):
        self.search = search_service or SearchService()
        self.context = context_service or ContextService()
        self.prompts = prompt_service or PromptService()
        self.responses = response_service or ResponseService()
        self.strategies = retrieval_strategy or RetrievalStrategy()
    
    def query(
        self,
        question: str,
        top_k: int = TOP_K_RESULTS,
        temperature: float = 0.7,
        include_sources: bool = True,
        min_similarity: float = None,
        enable_compression: bool = None,
        use_hybrid_search: bool = None,
        hybrid_alpha: float = None,
        collection_id: str = None,
        response_style: str = "detailed",
        debug_mode: bool = False,
        history: str = None,
        enable_adaptive: bool = None,
        search_mode: Optional[Literal["auto", "hierarchical", "sentence"]] = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """Executa query RAG completa."""
        start_time = time.time()
        request_id = request_id or "unknown"
        inc_query()
        
        # Log início da query
        log_step(logger, "Query Started",
                  request_id=request_id,
                  question=question[:100],
                  top_k=top_k,
                  collection_id=collection_id)
        
        # Determinar estratégia de chunking (Sentence Window vs Hierarchical)
        if search_mode == "auto" or search_mode is None:
            # Decisão automática baseada na pergunta
            strategy = determine_search_strategy(question)
            use_sentence_window = (strategy == "sentence")
            logger.info(f"Search mode: auto, Strategy: {strategy}, Use Sentence Window: {use_sentence_window} | request_id={request_id}")
            log_step(logger, "Strategy Determined",
                      request_id=request_id,
                      strategy=strategy,
                      use_sentence_window=use_sentence_window)
        elif search_mode == "hierarchical":
            use_sentence_window = False
            logger.info(f"Search mode: hierarchical, Use Sentence Window: False | request_id={request_id}")
            log_step(logger, "Strategy Determined",
                      request_id=request_id,
                      strategy="hierarchical",
                      use_sentence_window=False)
        elif search_mode == "sentence":
            use_sentence_window = True
            logger.info(f"Search mode: sentence, Use Sentence Window: True | request_id={request_id}")
            log_step(logger, "Strategy Determined",
                      request_id=request_id,
                      strategy="sentence",
                      use_sentence_window=True)
        else:
            # Fallback seguro
            use_sentence_window = False
            logger.warning(f"Invalid search_mode: {search_mode}, using hierarchical | request_id={request_id}")
            log_step(logger, "Strategy Fallback",
                      request_id=request_id,
                      strategy="hierarchical",
                      reason=f"Invalid search_mode: {search_mode}")
        
        # Inicializar métricas de adaptive retrieval
        adaptive_metrics = {"applied": False, "reason": "disabled_by_config"}
        
        try:
            with LatencyTracker("rag_total"):
                # 1. Classificar pergunta
                with log_stage("Classification", logger, request_id=request_id):
                    question_type = classify_question(question)
                    log_step(logger, "Classification Complete",
                              request_id=request_id,
                              question_type=question_type)
                
                # 1.5 Aplicar Adaptive Retrieval se habilitado
                with log_stage("Adaptive Retrieval", logger, request_id=request_id):
                    if ENABLE_ADAPTIVE_RETRIEVAL and enable_adaptive:
                        base_min_sim = min_similarity if min_similarity is not None else MIN_SIMILARITY_THRESHOLD
                        adaptive_result = get_adaptive_params(
                            question,
                            base_top_k=top_k,
                            base_min_similarity=base_min_sim
                        )
                        top_k = adaptive_result["top_k"]
                        min_similarity = adaptive_result["min_similarity"]
                        adaptive_metrics = {
                            "applied": True,
                            "complexity_score": adaptive_result["analysis"]["complexity_score"],
                            "word_count": adaptive_result["analysis"]["word_count"],
                            "top_k": top_k,
                            "min_similarity": min_similarity,
                            "original_top_k": adaptive_result["original_top_k"],
                            "original_min_similarity": adaptive_result["original_min_similarity"],
                            "adjustment_reason": adaptive_result["adjustment_reason"],
                            "characteristics": adaptive_result["analysis"]
                        }
                        log_step(logger, "Adaptive Applied",
                                  request_id=request_id,
                                  adaptive_params=adaptive_metrics)
                    elif enable_adaptive and not ENABLE_ADAPTIVE_RETRIEVAL:
                        adaptive_metrics = {"applied": False, "reason": "disabled_in_config"}
                        log_step(logger, "Adaptive Skipped",
                                  request_id=request_id,
                                  reason="disabled_in_config")
                    else:
                        adaptive_metrics = {"applied": False, "reason": "disabled_by_user"}
                        log_step(logger, "Adaptive Skipped",
                                  request_id=request_id,
                                  reason="disabled_by_user")
                
                # 2. Gerar embedding (com HyDE se habilitado)
                with log_stage("Embedding", logger, request_id=request_id):
                    hyde_embedding = self.strategies.apply_hyde(question)
                    embedding = hyde_embedding or get_embedding(question)
                    log_step(logger, "Embedding Generated",
                              request_id=request_id,
                              dimension=len(embedding))
                
                # 3. Buscar documentos (Phase 1)
                with log_stage("Search", logger, request_id=request_id):
                    search_metrics = {}
                    if use_sentence_window:
                        # Usa Sentence Window Retrieval
                        initial_docs = self.search.search_with_sentence_window(
                            question=question,
                            query_embedding=embedding,
                            top_k=top_k,
                            window_size=SENTENCE_WINDOW_SIZE,
                            collection_id=collection_id,
                            request_id=request_id
                        )
                    else:
                        # Usa Hierarchical Chunking (padrão)
                        initial_docs = self.search.search(
                            question=question,
                            query_embedding=embedding,
                            top_k=top_k * 3,  # Busca mais para o re-ranking
                            min_similarity=min_similarity,
                            use_hybrid=use_hybrid_search,
                            hybrid_alpha=hybrid_alpha,
                            collection_id=collection_id,
                            request_id=request_id
                        )
                    log_step(logger, "Search Complete",
                              request_id=request_id,
                              documents_found=len(initial_docs))
                
                # 4. Refinar busca (Phase 2: MMR, Re-ranking)
                with log_stage("Reranking", logger, request_id=request_id):
                    documents, search_metrics = self.strategies.apply_phase2_pipeline(
                        question=question,
                        question_embedding=embedding,
                        initial_results=initial_docs,
                        final_top_k=top_k,
                        search_metrics=search_metrics
                    )
                    log_step(logger, "Reranking Complete",
                              request_id=request_id,
                              documents_after_rerank=len(documents))
                
                observe_chunks_retrieved(len(documents))
                
                if not documents:
                    log_step(logger, "No Results Found",
                              request_id=request_id,
                              question=question[:100])
                    return self.responses.build_no_results_response(question, question_type, search_metrics)
                
                # 5. Montar e comprimir contexto
                with log_stage("Context Building", logger, request_id=request_id):
                    raw_context = self.context.build_context(documents, request_id=request_id)
                    context_result = self.context.compress_if_needed(
                        raw_context, 
                        question, 
                        enable_compression,
                        request_id=request_id
                    )
                    log_step(logger, "Context Ready",
                              request_id=request_id,
                              context_chars=len(raw_context),
                              was_compressed=context_result["was_compressed"])
                
                # 6. Construir prompt
                with log_stage("Prompt Building", logger, request_id=request_id):
                    prompt = self.prompts.build_prompt(
                        context=context_result["context"],
                        question=question,
                        question_type=question_type,
                        history=history,
                        response_style=response_style
                    )
                    log_step(logger, "Prompt Built",
                              request_id=request_id,
                              prompt_length=len(prompt))
                
                # 7. Gerar resposta
                with log_stage("LLM", logger, request_id=request_id):
                    answer = generate_response(prompt, temperature=temperature, request_id=request_id)
                    log_step(logger, "LLM Complete",
                              request_id=request_id,
                              answer_length=len(answer))
                
                # 7.5. Auto-avaliação (opcional)
                evaluation_metrics = {}
                if ENABLE_AUTO_EVALUATION:
                    with LatencyTracker("evaluation"):
                        try:
                            # Avaliar resposta
                            evaluation_result = evaluate_rag_response(
                                question=question,
                                answer=answer,
                                context=raw_context,
                                chunks=documents
                            )
                            
                            # Filtrar avaliações muito baixas
                            if evaluation_result["overall_score"] >= EVALUATION_MIN_SCORE_THRESHOLD:
                                evaluation_metrics = evaluation_result
                                
                                # Salvar no banco (assíncrono para não impactar performance)
                                try:
                                    evaluation_repo.save_evaluation(
                                        question=question,
                                        answer=answer,
                                        context=raw_context,
                                        scores=evaluation_result,
                                        session_id=collection_id,  # Usando collection_id temporariamente
                                        chunks_retrieved=len(documents),
                                        search_mode=search_mode,
                                        adaptive_used=adaptive_metrics.get("applied", False)
                                    )
                                    logger.debug(f"Evaluation saved: score={evaluation_result['overall_score']:.2%}")
                                except Exception as e:
                                    logger.warning(f"Failed to save evaluation: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to evaluate response: {e}")
                
                # 7.6. Self-RAG - Avaliar e refinar se habilitado
                self_rag_metrics = {}
                if ENABLE_SELF_RAG:
                    with LatencyTracker("self_rag"):
                        # Função de busca adicional usando Query Expansion
                        def additional_search(query: str, top_k: int):
                            expanded_queries = expand_query(query)
                            results = []
                            for eq in expanded_queries[:2]:  # Limitar para não demorar muito
                                eq_embedding = get_embedding(eq)
                                results.extend(
                                    self.search.search(
                                        question=eq,
                                        query_embedding=eq_embedding,
                                        top_k=top_k,
                                        min_similarity=min_similarity,
                                        use_hybrid=use_hybrid_search,
                                        hybrid_alpha=hybrid_alpha,
                                        collection_id=collection_id
                                    )
                                )
                            return results[:top_k]
                        
                        # Aplicar Self-RAG
                        answer, self_rag_metrics = self_rag_pipeline(
                            question=question,
                            answer=answer,
                            context=raw_context,
                            search_function=additional_search,
                            min_score=SELF_RAG_MIN_SCORE,
                            max_iterations=SELF_RAG_MAX_ITERATIONS
                        )
                
                # 8. Formatar resposta
                total_duration = time.time() - start_time
                
                # 8.1 Salvar métricas de adaptive retrieval se aplicado
                if adaptive_metrics.get("applied") and collection_id:
                    try:
                        adaptive_retrieval_repo.save_metric(
                            session_id=collection_id,  # Usando collection_id como session_id temporariamente
                            question=question,
                            complexity_score=adaptive_metrics["complexity_score"],
                            word_count=adaptive_metrics["word_count"],
                            top_k_original=adaptive_metrics["original_top_k"],
                            top_k_adjusted=adaptive_metrics["top_k"],
                            min_similarity_original=adaptive_metrics["original_min_similarity"],
                            min_similarity_adjusted=adaptive_metrics["min_similarity"],
                            adjustment_reason=adaptive_metrics["adjustment_reason"],
                            characteristics=adaptive_metrics["characteristics"],
                            duration_ms=int(total_duration * 1000)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save adaptive metric: {e}")
                
                # Log final
                log_step(logger, "Query Complete",
                          request_id=request_id,
                          total_duration=f"{total_duration:.3f}s",
                          status="success")
                
                return self.responses.format_response(
                    answer=answer,
                    documents=documents if include_sources else [],
                    question_type=question_type,
                    was_compressed=context_result["was_compressed"],
                    search_metrics=search_metrics,
                    self_rag_metrics=self_rag_metrics,
                    adaptive_params_used=adaptive_metrics,
                    evaluation_metrics=evaluation_metrics,
                    duration=total_duration
                )
                
        except Exception as e:
            log_error(logger, "RAG Pipeline", e,
                      request_id=request_id,
                      question=question,
                      collection_id=collection_id)
            # Track error type for Prometheus metrics
            inc_error(type(e).__name__)
            raise

    def query_stream(
        self,
        question: str,
        top_k: int = TOP_K_RESULTS,
        temperature: float = 0.7,
        response_style: str = "detailed",
        request_id: str = None
    ):
        """Versão simplificada para streaming."""
        request_id = request_id or "unknown"
        
        # Repete lógica básica mas foca no gerador
        embedding = get_embedding(question)
        docs = self.search.search(question, embedding, top_k, request_id=request_id)
        
        if not docs:
            log_step(logger, "No Results (Stream)",
                      request_id=request_id,
                      question=question[:100])
            yield "Desculpe, não encontrei informações para responder."
            return

        context = self.context.build_context(docs, request_id=request_id)
        prompt = self.prompts.build_prompt(context, question, response_style=response_style)
        
        log_step(logger, "Stream Query Started",
                  request_id=request_id,
                  question=question[:100])
        
        return generate_response(prompt, temperature=temperature, stream=True, request_id=request_id)

    def query_with_history(
        self,
        question: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Query RAG com suporte a histórico."""
        request_id = kwargs.get("request_id", "unknown")
        
        log_step(logger, "History Retrieved",
                  request_id=request_id,
                  session_id=session_id)
        
        history_text = conversation_manager.get_history_as_text(session_id)
        
        # Injeta o histórico no processamento
        result = self.query(question, history=history_text, **kwargs)
        
        # Salva a nova iteração no histórico
        conversation_manager.add_message(session_id, "user", question)
        conversation_manager.add_message(session_id, "assistant", result["answer"])
        
        log_step(logger, "History Saved",
                  request_id=request_id,
                  session_id=session_id,
                  messages_count=2)
        
        return result

    def search_only(
        self,
        question: str,
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = None,
        request_id: str = None
    ) -> List[Dict[str, Any]]:
        """Apenas busca documentos similares, sem gerar resposta."""
        request_id = request_id or "unknown"
        
        log_step(logger, "Search Only Started",
                  request_id=request_id,
                  question=question[:100],
                  top_k=top_k)
        
        embedding = get_embedding(question)
        results = self.search.search(
            question=question,
            query_embedding=embedding,
            top_k=top_k,
            min_similarity=min_similarity,
            use_hybrid=False,
            request_id=request_id
        )
        
        log_step(logger, "Search Only Complete",
                  request_id=request_id,
                  results_count=len(results))
        
        return results

# Instância global para compatibilidade
_default_pipeline = RAGPipeline()

def query_rag(question: str, **kwargs) -> Dict[str, Any]:
    return _default_pipeline.query(question, **kwargs)

def query_rag_stream(question: str, search_mode: Optional[Literal["auto", "hierarchical", "sentence"]] = None, **kwargs):
    return _default_pipeline.query_stream(question, search_mode=search_mode, **kwargs)

def query_rag_with_history(question: str, session_id: str, search_mode: Optional[Literal["auto", "hierarchical", "sentence"]] = None, **kwargs):
    return _default_pipeline.query_with_history(question, session_id, search_mode=search_mode, **kwargs)

def search_only(question: str, **kwargs):
    return _default_pipeline.search_only(question, **kwargs)

def get_conversation_history(session_id: str):
    session = conversation_manager.get_session(session_id)
    return session.to_dict() if session else None

def clear_conversation(session_id: str):
    return conversation_manager.delete_session(session_id)
