"""
Estratégias de recuperação de documentos (Phase 2 e Phase 3).
"""
import logging
from typing import List, Dict, Any, Tuple
from src.config import (
    ENABLE_RERANKING,
    ENABLE_MMR,
    ENABLE_QUERY_EXPANSION,
    ENABLE_HYDE,
    TOP_K_RESULTS,
    RERANKING_TOP_K_INITIAL
)
from src.core.mmr import mmr_filter
from src.core.reranker import rerank_chunks
from src.core.hyde import generate_hyde_embedding

logger = logging.getLogger("rag.pipeline")


class RetrievalStrategy:
    """Encapsula lógica avançada de recuperação (Phase 2/3)."""
    
    def __init__(self):
        self._enable_reranking = ENABLE_RERANKING
        self._enable_mmr = ENABLE_MMR
        self._enable_query_expansion = ENABLE_QUERY_EXPANSION
        self._enable_hyde = ENABLE_HYDE

    def apply_phase2_pipeline(
        self,
        question: str,
        question_embedding: List[float],
        initial_results: List[Dict[str, Any]],
        final_top_k: int = TOP_K_RESULTS,
        search_metrics: Dict[str, Any] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Aplica pipeline Phase 2: Query Expansion, MMR e Re-ranking.
        """
        if search_metrics is None:
            search_metrics = {}
            
        results = initial_results
        
        # 1. Query Expansion (Simulado ou Real se disponível)
        if self._enable_query_expansion:
            # expander = _get_query_expansion()
            # ...
            pass
            
        # 2. MMR (Maximal Marginal Relevance)
        if self._enable_mmr and len(results) > final_top_k:
            results = mmr_filter(question_embedding, results, k=final_top_k * 2)
            search_metrics["mmr_applied"] = True

        # 3. Re-ranking
        if self._enable_reranking and results:
            results = rerank_chunks(question, results, top_k=final_top_k)
            search_metrics["reranking_applied"] = True
            
        return results[:final_top_k], search_metrics

    def apply_hyde(self, question: str) -> List[float]:
        """Aplica Hypothetical Document Embeddings (HyDE)."""
        if self._enable_hyde:
            return generate_hyde_embedding(question)
        return None
