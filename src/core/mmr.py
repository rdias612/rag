"""
Módulo MMR (Maximal Marginal Relevance).

Reordena chunks para maximizar diversidade enquanto
mantém relevância, evitando redundância no contexto.
"""
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Calcula similaridade de cosseno entre dois vetores.
    
    Args:
        vec1: Primeiro vetor
        vec2: Segundo vetor
        
    Returns:
        Similaridade entre -1 e 1
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vetores devem ter o mesmo tamanho")
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def mmr_filter(
    query_embedding: list[float],
    chunks: list[dict],
    k: int = 5,
    lambda_param: float = 0.7,
    embedding_key: str = "embedding",
    similarity_key: str = "similarity"
) -> list[dict]:
    """
    Aplica Maximal Marginal Relevance para selecionar chunks diversos.
    
    MMR balanceia:
    - Relevância: similaridade com a query
    - Diversidade: dissimilaridade com chunks já selecionados
    
    Score MMR = λ * Relevância - (1-λ) * max(Similaridade com selecionados)
    
    Args:
        query_embedding: Embedding da query
        chunks: Lista de chunks com embeddings
        k: Número de chunks a selecionar
        lambda_param: Balanço entre relevância (1.0) e diversidade (0.0)
                     Recomendado: 0.7 (70% relevância, 30% diversidade)
        embedding_key: Chave do embedding nos chunks
        similarity_key: Chave da similaridade nos chunks
        
    Returns:
        Top K chunks selecionados com diversidade
    """
    if not chunks:
        return []
    
    if len(chunks) <= k:
        return chunks
    
    # Verificar se chunks têm embeddings
    has_embeddings = all(embedding_key in c for c in chunks)
    
    if not has_embeddings:
        logger.warning("Chunks sem embeddings, usando similaridade existente como aproximação")
        return _mmr_without_embeddings(chunks, k, lambda_param, similarity_key)
    
    selected = []
    candidates = list(range(len(chunks)))  # Índices dos candidatos
    
    while len(selected) < k and candidates:
        best_score = float("-inf")
        best_idx = -1
        best_candidate_pos = -1
        
        for pos, idx in enumerate(candidates):
            chunk = chunks[idx]
            
            # Relevância: similaridade com query
            if similarity_key in chunk:
                relevance = chunk[similarity_key]
            else:
                relevance = cosine_similarity(query_embedding, chunk[embedding_key])
            
            # Diversidade: 1 - max similaridade com selecionados
            if selected:
                max_sim_to_selected = max(
                    cosine_similarity(chunk[embedding_key], chunks[s][embedding_key])
                    for s in selected
                )
                diversity = 1 - max_sim_to_selected
            else:
                diversity = 1.0
            
            # Score MMR
            mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
            
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
                best_candidate_pos = pos
        
        if best_idx >= 0:
            selected.append(best_idx)
            candidates.pop(best_candidate_pos)
    
    # Construir resultado com scores MMR
    result = []
    for idx in selected:
        chunk = chunks[idx].copy()
        # Remover embedding do resultado (muito grande)
        if embedding_key in chunk:
            del chunk[embedding_key]
        result.append(chunk)
    
    logger.info(f"MMR: {len(chunks)} chunks -> {len(result)} diversos (λ={lambda_param})")
    
    return result


def _mmr_without_embeddings(
    chunks: list[dict],
    k: int,
    lambda_param: float,
    similarity_key: str
) -> list[dict]:
    """
    Versão simplificada do MMR quando não há embeddings.
    Usa apenas a similaridade existente e aproximação de diversidade por texto.
    """
    if len(chunks) <= k:
        return chunks
    
    selected = []
    candidates = chunks.copy()
    
    while len(selected) < k and candidates:
        best_score = float("-inf")
        best_idx = -1
        
        for i, chunk in enumerate(candidates):
            # Relevância
            relevance = chunk.get(similarity_key, 0.5)
            
            # Diversidade aproximada: penalizar se texto similar a selecionados
            if selected:
                # Aproximação simples: usar sobreposição de palavras
                chunk_words = set(chunk.get("content", "").lower().split())
                max_overlap = 0
                for sel in selected:
                    sel_words = set(sel.get("content", "").lower().split())
                    if chunk_words and sel_words:
                        overlap = len(chunk_words & sel_words) / len(chunk_words | sel_words)
                        max_overlap = max(max_overlap, overlap)
                diversity = 1 - max_overlap
            else:
                diversity = 1.0
            
            mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
            
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        
        if best_idx >= 0:
            selected.append(candidates.pop(best_idx))
    
    return selected


def check_mmr_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "method": "embedding_based"
    }
