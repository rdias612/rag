"""
Pipeline RAG principal - orquestrador modular.
"""
import time
import logging
from typing import Optional, Dict, Any, List

from src.config import TOP_K_RESULTS, ENABLE_SELF_RAG, SELF_RAG_MIN_SCORE, SELF_RAG_MAX_ITERATIONS
from src.core.embeddings import get_embedding
from src.core.llm import generate_response
from src.core.question_classifier import classify_question
from src.core.metrics import LatencyTracker, inc_query, observe_chunks_retrieved, inc_error
from src.core.conversation import conversation_manager
from src.core.self_rag import self_rag_pipeline

from src.core.rag.services.search_service import SearchService
from src.core.rag.services.context_service import ContextService
from src.core.rag.services.prompt_service import PromptService
from src.core.rag.services.response_service import ResponseService
from src.core.rag.strategies.retrieval_strategy import RetrievalStrategy

logger = logging.getLogger("rag.pipeline")


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
        history: str = None
    ) -> Dict[str, Any]:
        """Executa query RAG completa."""
        start_time = time.time()
        inc_query()
        
        try:
            with LatencyTracker("rag_total"):
                # 1. Classificar pergunta
                question_type = classify_question(question)
                
                # 2. Gerar embedding (com HyDE se habilitado)
                with LatencyTracker("embedding"):
                    hyde_embedding = self.strategies.apply_hyde(question)
                    embedding = hyde_embedding or get_embedding(question)
                
                # 3. Buscar documentos (Phase 1)
                search_metrics = {}
                with LatencyTracker("search"):
                    initial_docs = self.search.search(
                        question=question,
                        query_embedding=embedding,
                        top_k=top_k * 3,  # Busca mais para o re-ranking
                        min_similarity=min_similarity,
                        use_hybrid=use_hybrid_search,
                        hybrid_alpha=hybrid_alpha,
                        collection_id=collection_id
                    )
                
                # 4. Refinar busca (Phase 2: MMR, Re-ranking)
                with LatencyTracker("phase2"):
                    documents, search_metrics = self.strategies.apply_phase2_pipeline(
                        question=question,
                        question_embedding=embedding,
                        initial_results=initial_docs,
                        final_top_k=top_k,
                        search_metrics=search_metrics
                    )
                
                observe_chunks_retrieved(len(documents))
                
                if not documents:
                    return self.responses.build_no_results_response(question, question_type, search_metrics)
                
                # 5. Montar e comprimir contexto
                raw_context = self.context.build_context(documents)
                context_result = self.context.compress_if_needed(raw_context, question, enable_compression)
                
                # 6. Construir prompt
                prompt = self.prompts.build_prompt(
                    context=context_result["context"],
                    question=question,
                    question_type=question_type,
                    history=history,
                    response_style=response_style
                )
                
                # 7. Gerar resposta
                with LatencyTracker("llm"):
                    answer = generate_response(prompt, temperature=temperature)
                
                # 7.5. Self-RAG - Avaliar e refinar se habilitado
                self_rag_metrics = {}
                if ENABLE_SELF_RAG:
                    with LatencyTracker("self_rag"):
                        # Função de busca adicional usando Query Expansion
                        def additional_search(query: str, top_k: int):
                            from src.core.query_expansion import expand_query
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
                return self.responses.format_response(
                    answer=answer,
                    documents=documents if include_sources else [],
                    question_type=question_type,
                    was_compressed=context_result["was_compressed"],
                    search_metrics=search_metrics,
                    self_rag_metrics=self_rag_metrics,
                    duration=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Error in RAG Pipeline: {e}", exc_info=True)
            inc_error()
            raise

    def query_stream(
        self,
        question: str,
        top_k: int = TOP_K_RESULTS,
        temperature: float = 0.7,
        response_style: str = "detailed"
    ):
        """Versão simplificada para streaming."""
        # Repete lógica básica mas foca no gerador
        embedding = get_embedding(question)
        docs = self.search.search(question, embedding, top_k)
        
        if not docs:
            yield "Desculpe, não encontrei informações para responder."
            return

        context = self.context.build_context(docs)
        prompt = self.prompts.build_prompt(context, question, response_style=response_style)
        
        return generate_response(prompt, temperature=temperature, stream=True)

    def query_with_history(
        self,
        question: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Query RAG com suporte a histórico."""
        history_text = conversation_manager.get_history_as_text(session_id)
        
        # Injeta o histórico no processamento
        result = self.query(question, history=history_text, **kwargs)
        
        # Salva a nova iteração no histórico
        conversation_manager.add_message(session_id, "user", question)
        conversation_manager.add_message(session_id, "assistant", result["answer"])
        
        return result

    def search_only(
        self,
        question: str,
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = None
    ) -> List[Dict[str, Any]]:
        """Apenas busca documentos similares, sem gerar resposta."""
        embedding = get_embedding(question)
        return self.search.search(
            question=question,
            query_embedding=embedding,
            top_k=top_k,
            min_similarity=min_similarity,
            use_hybrid=False
        )

# Instância global para compatibilidade
_default_pipeline = RAGPipeline()

def query_rag(question: str, **kwargs) -> Dict[str, Any]:
    return _default_pipeline.query(question, **kwargs)

def query_rag_stream(question: str, **kwargs):
    return _default_pipeline.query_stream(question, **kwargs)

def query_rag_with_history(question: str, session_id: str, **kwargs):
    return _default_pipeline.query_with_history(question, session_id, **kwargs)

def search_only(question: str, **kwargs):
    return _default_pipeline.search_only(question, **kwargs)

def get_conversation_history(session_id: str):
    session = conversation_manager.get_session(session_id)
    return session.to_dict() if session else None

def clear_conversation(session_id: str):
    return conversation_manager.delete_session(session_id)
