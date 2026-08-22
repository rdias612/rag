"""
Serviço de busca de documentos.
"""
from typing import Optional, List, Dict, Any

from src.data.hybrid_search import search_hybrid
from src.data.sentence_window import expand_sentence_results
from src.data.repositories.document_repository import DocumentRepository
from src.config import ENABLE_HYBRID_SEARCH, HYBRID_SEARCH_ALPHA, TOP_K_RESULTS, SENTENCE_WINDOW_SIZE
from src.core.logger import get_logger

logger = get_logger("rag.search_service")


class SearchService:
    """Encapsula lógica de busca vetorial e híbrida."""
    
    def __init__(self):
        self._use_hybrid = ENABLE_HYBRID_SEARCH
        self._hybrid_alpha = HYBRID_SEARCH_ALPHA
        self._doc_repo = DocumentRepository()
    
    def search(
        self,
        question: str,
        query_embedding: List[float],
        top_k: int = TOP_K_RESULTS,
        min_similarity: float = None,
        use_hybrid: bool = None,
        hybrid_alpha: float = None,
        collection_id: str = None,
        chunking_type: Optional[str] = None,
        request_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Executa busca de documentos.
        """
        request_id = request_id or "unknown"
        should_use_hybrid = use_hybrid if use_hybrid is not None else self._use_hybrid
        alpha = hybrid_alpha if hybrid_alpha is not None else self._hybrid_alpha
        
        logger.info("Search Started | request_id=%s | search_type=%s | top_k=%d | alpha=%s | chunking_type=%s | collection_id=%s",
                    request_id, "hybrid" if should_use_hybrid else "vector", top_k,
                    alpha if should_use_hybrid else None, chunking_type, collection_id)
        
        try:
            if should_use_hybrid:
                logger.debug("Hybrid Search | request_id=%s", request_id)
                results = search_hybrid(
                    query=question,
                    query_embedding=query_embedding,
                    top_k=top_k,
                    alpha=alpha,
                    collection_id=collection_id,
                    request_id=request_id
                )
                logger.info("Hybrid Search Complete | request_id=%s | results=%d", request_id, len(results))
                return results
            else:
                logger.debug("Vector Search | request_id=%s", request_id)
                if chunking_type:
                    results = self._doc_repo.find_similar_by_chunking_type(
                        query_embedding=query_embedding,
                        chunking_type=chunking_type,
                        top_k=top_k,
                        min_similarity=min_similarity,
                        collection_id=collection_id
                    )
                else:
                    results = self._doc_repo.find_similar(
                        query_embedding=query_embedding,
                        top_k=top_k,
                        min_similarity=min_similarity,
                        collection_id=collection_id
                    )
                logger.info("Vector Search Complete | request_id=%s | results=%d", request_id, len(results))
                return results
        except Exception as e:
            logger.error("Search Service Error | request_id=%s | question=%s | search_type=%s | error=%s",
                         request_id, question[:100], "hybrid" if should_use_hybrid else "vector", e, exc_info=True)
            raise
    
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
            use_hybrid=False
        )
    
    def search_with_sentence_window(
        self,
        question: str,
        query_embedding: List[float],
        top_k: int = TOP_K_RESULTS,
        window_size: int = SENTENCE_WINDOW_SIZE,
        collection_id: str = None,
        request_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Busca usando Sentence Window Retrieval.
        """
        request_id = request_id or "unknown"
        
        logger.info("Sentence Window Search Started | request_id=%s | top_k=%d | window_size=%d | collection_id=%s",
                    request_id, top_k, window_size, collection_id)
        
        try:
            sentence_results = self._doc_repo.find_similar(
                query_embedding=query_embedding,
                top_k=top_k * 2,
                collection_id=collection_id,
                chunking_type="sentence"
            )
            logger.debug("Sentence Search Complete | request_id=%s | sentences_found=%d",
                         request_id, len(sentence_results))
            
            if not sentence_results:
                logger.info("No Sentences Found | request_id=%s | question=%s", request_id, question[:100])
                return []
            
            sentences_by_doc = {}
            for result in sentence_results:
                source_path = result.get("metadata", {}).get("source_path")
                if source_path:
                    if source_path not in sentences_by_doc:
                        sentences_by_doc[source_path] = []
                    sentences_by_doc[source_path].append(result)
            
            expanded_results = []
            for source_path, sentences in sentences_by_doc.items():
                all_sentences = self._get_all_sentences_for_document(source_path)
                windows = expand_sentence_results(
                    sentence_results=sentences,
                    all_sentences=all_sentences,
                    window_size=window_size,
                    deduplicate=True
                )
                expanded_results.extend(windows)
            
            expanded_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            final_results = expanded_results[:top_k]
            
            logger.info("Sentence Window Search Complete | request_id=%s | final_results=%d",
                        request_id, len(final_results))
            return final_results
        
        except Exception as e:
            logger.error("Sentence Window Search Error | request_id=%s | question=%s | error=%s",
                         request_id, question, e, exc_info=True)
            raise
    
    def _get_all_sentences_for_document(self, source_path: str) -> List[dict]:
        """
        Recupera todas as sentenças de um documento ordenadas por índice.
        """
        with self._doc_repo._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT content, metadata
                FROM documentos
                WHERE metadata->>'source_path' = %s
                  AND metadata->>'chunk_type' = 'sentence'
                ORDER BY (metadata->>'sentence_index')::INTEGER
            """, (source_path,))
            
            return [
                {
                    "content": row["content"],
                    "metadata": row["metadata"]
                }
                for row in cur.fetchall()
            ]
