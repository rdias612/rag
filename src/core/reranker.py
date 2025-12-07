"""
Módulo de Re-ranking com Cross-Encoder.

Utiliza modelos cross-encoder para reordenar chunks por relevância
real em relação à query, melhorando significativamente a precisão.
"""
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Flag para indicar se sentence-transformers está disponível
CROSS_ENCODER_AVAILABLE = False
_cross_encoder_model = None

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    logger.info("sentence-transformers disponível para re-ranking")
except ImportError:
    logger.warning(
        "sentence-transformers não instalado. "
        "Re-ranking com cross-encoder desabilitado. "
        "Instale com: pip install sentence-transformers"
    )


class CrossEncoderReranker:
    """
    Re-ranker usando modelos Cross-Encoder.
    
    Cross-encoders processam query e documento juntos,
    fornecendo scores de relevância mais precisos que
    bi-encoders (embeddings separados).
    """
    
    def __init__(
        self, 
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_length: int = 512
    ):
        """
        Inicializa o re-ranker.
        
        Args:
            model_name: Nome do modelo cross-encoder do HuggingFace
                       Opções recomendadas:
                       - "cross-encoder/ms-marco-MiniLM-L-6-v2" (rápido, ~100MB)
                       - "BAAI/bge-reranker-base" (melhor qualidade, ~400MB)
            max_length: Comprimento máximo de tokens para query+documento
        """
        if not CROSS_ENCODER_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers não está instalado. "
                "Execute: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.max_length = max_length
        self._model = None
        
        logger.info(f"CrossEncoderReranker inicializado com modelo: {model_name}")
    
    @property
    def model(self):
        """Carrega modelo sob demanda (lazy loading)."""
        if self._model is None:
            logger.info(f"Carregando modelo cross-encoder: {self.model_name}")
            start = time.time()
            self._model = CrossEncoder(self.model_name, max_length=self.max_length)
            logger.info(f"Modelo carregado em {time.time() - start:.2f}s")
        return self._model
    
    def score_pair(self, query: str, text: str) -> float:
        """
        Calcula score de relevância para um par query-documento.
        
        Args:
            query: Query do usuário
            text: Texto do documento/chunk
            
        Returns:
            Score de relevância (quanto maior, mais relevante)
        """
        return float(self.model.predict([[query, text]])[0])
    
    def rerank(
        self, 
        query: str, 
        chunks: list[dict], 
        top_k: int = 5,
        content_key: str = "content"
    ) -> list[dict]:
        """
        Reordena chunks por relevância usando cross-encoder.
        
        Args:
            query: Query do usuário
            chunks: Lista de chunks com 'content' e outros campos
            top_k: Número de chunks a retornar após reranking
            content_key: Chave do campo de conteúdo nos chunks
            
        Returns:
            Top K chunks reordenados por relevância
        """
        if not chunks:
            return []
        
        start_time = time.time()
        
        # Preparar pares query-documento
        pairs = [[query, chunk[content_key]] for chunk in chunks]
        
        # Calcular scores
        scores = self.model.predict(pairs)
        
        # Adicionar scores aos chunks
        scored_chunks = []
        for chunk, score in zip(chunks, scores):
            chunk_copy = chunk.copy()
            chunk_copy["rerank_score"] = float(score)
            scored_chunks.append(chunk_copy)
        
        # Ordenar por score (maior = mais relevante)
        scored_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        # Retornar top_k
        result = scored_chunks[:top_k]
        
        duration = time.time() - start_time
        logger.info(
            f"Reranking: {len(chunks)} chunks -> {len(result)} em {duration:.3f}s"
        )
        
        return result


# Instância global (singleton) - carregada sob demanda
_reranker_instance: Optional[CrossEncoderReranker] = None


def get_reranker(model_name: str = None) -> CrossEncoderReranker:
    """
    Obtém instância do reranker (singleton com lazy loading).
    
    Args:
        model_name: Nome do modelo (usa config se None)
        
    Returns:
        Instância do CrossEncoderReranker
    """
    global _reranker_instance
    
    if _reranker_instance is None:
        from src.config import RERANKER_MODEL
        model = model_name or RERANKER_MODEL
        _reranker_instance = CrossEncoderReranker(model_name=model)
    
    return _reranker_instance


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = 5
) -> list[dict]:
    """
    Função de conveniência para reranking de chunks.
    
    Args:
        query: Query do usuário
        chunks: Lista de chunks
        top_k: Número de chunks a retornar
        
    Returns:
        Chunks reordenados por relevância
    """
    if not CROSS_ENCODER_AVAILABLE:
        logger.warning("Cross-encoder não disponível, retornando chunks sem reranking")
        return chunks[:top_k]
    
    reranker = get_reranker()
    return reranker.rerank(query, chunks, top_k)


def check_reranker_available() -> dict:
    """
    Verifica status do reranker.
    
    Returns:
        Dict com status do módulo
    """
    return {
        "cross_encoder_available": CROSS_ENCODER_AVAILABLE,
        "model_loaded": _reranker_instance is not None and _reranker_instance._model is not None,
        "model_name": _reranker_instance.model_name if _reranker_instance else None
    }
