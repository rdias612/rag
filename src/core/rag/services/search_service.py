"""
Serviço de busca de documentos.
"""
from typing import Optional, List, Dict, Any
from src.data.database import search_similar
from src.data.hybrid_search import search_hybrid
from src.data.sentence_window import expand_sentence_results
from src.config import ENABLE_HYBRID_SEARCH, HYBRID_SEARCH_ALPHA, TOP_K_RESULTS, SENTENCE_WINDOW_SIZE


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
    
    def search_with_sentence_window(
        self,
        question: str,
        query_embedding: List[float],
        top_k: int = TOP_K_RESULTS,
        window_size: int = SENTENCE_WINDOW_SIZE,
        collection_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Busca usando Sentence Window Retrieval.
        
        1. Busca sentenças individuais (precisas)
        2. Expande para janelas (contexto)
        3. Deduplica janelas sobrepostas
        
        Args:
            question: Texto da pergunta
            query_embedding: Embedding da pergunta
            top_k: Número de resultados finais
            window_size: Tamanho da janela (sentenças antes/depois)
            collection_id: Filtrar por coleção
            
        Returns:
            Lista de janelas expandidas com contexto
        """
        # 1. Buscar sentenças individuais
        sentence_results = search_similar(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Buscar mais para expandir
            collection_id=collection_id,
            filters={"chunk_type": "sentence"}  # Filtra apenas sentences
        )
        
        if not sentence_results:
            return []
        
        # 2. Agrupar por documento
        sentences_by_doc = {}
        for result in sentence_results:
            doc_id = result.get("metadata", {}).get("document_id")
            if doc_id:
                if doc_id not in sentences_by_doc:
                    sentences_by_doc[doc_id] = []
                sentences_by_doc[doc_id].append(result)
        
        # 3. Para cada documento, expandir janelas
        expanded_results = []
        for doc_id, sentences in sentences_by_doc.items():
            # Buscar todas as sentenças do documento
            all_sentences = self._get_all_sentences_for_document(doc_id)
            
            # Expandir
            windows = expand_sentence_results(
                sentence_results=sentences,
                all_sentences=all_sentences,
                window_size=window_size,
                deduplicate=True
            )
            
            expanded_results.extend(windows)
        
        # 4. Ordenar por similaridade e limitar
        expanded_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return expanded_results[:top_k]
    
    def _get_all_sentences_for_document(self, document_id: str) -> List[dict]:
        """
        Recupera todas as sentenças de um documento ordenadas por índice.
        
        Args:
            document_id: ID do documento
            
        Returns:
            Lista de sentenças ordenadas
        """
        from src.data.database import execute_query
        
        query = """
            SELECT content, metadata
            FROM chunks
            WHERE metadata->>'document_id' = %s
              AND chunk_type = 'sentence'
            ORDER BY (metadata->>'sentence_index')::INTEGER
        """
        
        results = execute_query(query, (document_id,))
        
        return [
            {
                "content": row["content"],
                "metadata": row["metadata"]
            }
            for row in results
        ]
