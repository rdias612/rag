"""
Módulo de geração de embeddings via LM Studio API (Nomic Embed v1.5).
"""
import time
import requests
from typing import Union

from src.config import LM_STUDIO_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSION
from src.core.logger import (
    embedding_logger,
    log_embedding_request,
    log_embedding_response,
    log_embedding_batch_request,
    log_embedding_batch_response
)


def get_embedding(text: str, use_cache: bool = True) -> list[float]:
    """
    Gera o embedding de um texto usando o modelo Nomic Embed v1.5.
    
    Args:
        text: Texto para gerar embedding
        use_cache: Se True, usa cache para evitar recálculo (default: True)
        
    Returns:
        Lista de floats representando o embedding
    """
    from src.config import EMBEDDING_CACHE_ENABLED
    from src.core.embedding_cache import embedding_cache
    
    # Verificar cache primeiro (se habilitado)
    if use_cache and EMBEDDING_CACHE_ENABLED:
        cached = embedding_cache.get(text)
        if cached is not None:
            embedding_logger.debug(f"Embedding retrieved from cache")
            return cached
    
    start_time = time.time()
    
    # Log do texto enviado para embedding
    log_embedding_request(text, EMBEDDING_MODEL)
    
    response = requests.post(
        f"{LM_STUDIO_BASE_URL}/embeddings",
        json={
            "model": EMBEDDING_MODEL,
            "input": text
        },
        timeout=60
    )
    
    response.raise_for_status()
    data = response.json()
    
    embedding = data["data"][0]["embedding"]
    duration = time.time() - start_time
    
    # Log do embedding gerado
    log_embedding_response(embedding, duration)
    
    # Armazenar no cache (se habilitado)
    if use_cache and EMBEDDING_CACHE_ENABLED:
        embedding_cache.set(text, embedding)
    
    return embedding


def get_embeddings_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Gera embeddings para múltiplos textos em batch.
    
    Args:
        texts: Lista de textos para gerar embeddings
        batch_size: Tamanho do batch para cada requisição
        
    Returns:
        Lista de embeddings (cada um é uma lista de floats)
    """
    all_embeddings = []
    total_start = time.time()
    
    embedding_logger.info(f"Starting batch embedding: {len(texts)} texts, batch_size={batch_size}")
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_start = time.time()
        
        log_embedding_batch_request(len(batch), EMBEDDING_MODEL)
        
        response = requests.post(
            f"{LM_STUDIO_BASE_URL}/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "input": batch
            },
            timeout=120
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Ordenar por índice para garantir ordem correta
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        batch_embeddings = [item.get("embedding") for item in sorted_data]
        
        # Validar se algum embedding veio nulo ou malformado
        for idx, emb in enumerate(batch_embeddings):
            is_invalid = False
            error_reason = ""
            
            if emb is None:
                is_invalid = True
                error_reason = "Embedding is None (null from model)"
            elif not isinstance(emb, list):
                is_invalid = True
                error_reason = f"Embedding is not a list (type: {type(emb)})"
            elif any(v is None for v in emb):
                is_invalid = True
                error_reason = "Embedding contains NULL values"
                
            if is_invalid:
                orig_idx = i + idx
                problematic_text = texts[orig_idx]
                text_len = len(problematic_text)
                sample_text = problematic_text[:100] + "..." if text_len > 100 else problematic_text
                
                embedding_logger.error(f"ERRO: {error_reason}")
                embedding_logger.error(f"Texto (index {orig_idx}, len {text_len}): '{sample_text}'")
                
                # Opcional: Logar o objeto retornado pelo LM Studio para debug profundo
                embedding_logger.debug(f"Data from LM Studio for this index: {sorted_data[idx]}")
                
                raise ValueError(f"O modelo de embeddings retornou um valor inválido ({error_reason}) para o texto {orig_idx}. "
                                 f"Verifique se o texto está vazio ou se o modelo no LM Studio parou de responder.")

        all_embeddings.extend(batch_embeddings)
        
        batch_duration = time.time() - batch_start
        log_embedding_batch_response(len(batch), batch_duration, EMBEDDING_DIMENSION)
        
        embedding_logger.info(f"Processados {min(i + batch_size, len(texts))}/{len(texts)} embeddings")
    
    total_duration = time.time() - total_start
    embedding_logger.info(f"Batch embedding complete: {len(all_embeddings)} embeddings in {total_duration:.2f}s")
    
    return all_embeddings


def check_embedding_service() -> bool:
    """Verifica se o serviço de embeddings está disponível."""
    try:
        # Testar com um texto simples
        embedding = get_embedding("teste")
        embedding_logger.info(f"Embedding service available. Dimension: {len(embedding)}")
        return len(embedding) > 0
    except Exception as e:
        embedding_logger.error(f"Embedding service error: {e}")
        return False
