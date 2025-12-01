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
    log_embedding_response
)


def get_embedding(text: str) -> list[float]:
    """
    Gera o embedding de um texto usando o modelo Nomic Embed v1.5.
    
    Args:
        text: Texto para gerar embedding
        
    Returns:
        Lista de floats representando o embedding
    """
    start_time = time.time()
    
    log_embedding_request(1, EMBEDDING_MODEL)
    
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
    
    log_embedding_response(1, duration, len(embedding))
    
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
        
        log_embedding_request(len(batch), EMBEDDING_MODEL)
        
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
        batch_embeddings = [item["embedding"] for item in sorted_data]
        all_embeddings.extend(batch_embeddings)
        
        batch_duration = time.time() - batch_start
        log_embedding_response(len(batch), batch_duration, EMBEDDING_DIMENSION)
        
        print(f"  📊 Processados {min(i + batch_size, len(texts))}/{len(texts)} embeddings")
    
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
