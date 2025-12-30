"""
Serviço de busca de documentos.
"""
from typing import Optional, List, Dict, Any
from src.data.database import search_similar
from src.data.hybrid_search import search_hybrid
from src.config import ENABLE_HYBRID_SEARCH, HYBRID_SEARCH_ALPHA, TOP_K_RESULTS


class SearchService:
    """Encapsula lógica de busca vetorial e híbrida."""
    
    def __init__(self):
        self._use_hybrid = ENABLE_HYBRID_SEARCH
        self._hybrid_alpha = HYBRID_SEARCH_ALPHA
    
    def search(
        self,
        question: str,
        query_embedding: List[float],
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = None,
        use_hybrid: bool = None,
        hybrid_alpha: float = None,
        collection_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Executa busca de documentos.
        
        Args:
            question: Texto da pergunta
            query_embedding: Embedding da pergunta
            top_k: Número de resultados
            min_similarity: Similaridade mínima
            use_hybrid: Forçar busca híbrida on/off
            hybrid_alpha: Alpha para busca híbrida (se None, usa config)
            collection_id: Filtrar por coleção
            
        Returns:
            Lista de documentos com score
        """
        should_use_hybrid = use_hybrid if use_hybrid is not None else self._use_hybrid
        alpha = hybrid_alpha if hybrid_alpha is not None else self._hybrid_alpha
        
        if should_use_hybrid:
            return search_hybrid(
                query=question,
                query_embedding=query_embedding,
                top_k=top_k,
                alpha=alpha,
                collection_id=collection_id
            )
        else:
            return search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                min_similarity=min_similarity,
                collection_id=collection_id
            )
    
    def search_only(
        self,
        question: str,
        query_embedding: List[float],
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = None
    ) -> List[Dict[str, Any]]:
        """Apenas busca documentos similares, sem gerar resposta."""
        return self.search(
            question=question,
            query_embedding=query_embedding,
            top_k=top_k,
            min_similarity=min_similarity,
            use_hybrid=False  # search_only costuma ser puramente vetorial, mas pode ser mudado
        )
