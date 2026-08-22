"""
Módulo de geração de embeddings via LM Studio API (Nomic Embed v1.5 / BGE-M3).
"""
import time
import re
import requests
from typing import Optional, List

from src.config import LM_STUDIO_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSION, EMBEDDING_CACHE_ENABLED
from src.core.embedding_cache import embedding_cache
from src.core.logger import get_logger

logger = get_logger("core.embeddings")


def get_embedding(text: str, use_cache: bool = True, request_id: str = None) -> Optional[List[float]]:
    """
    Gera o embedding de um texto usando a API do LM Studio.
    
    Args:
        text: Texto para gerar embedding
        use_cache: Se True, usa cache para evitar recálculo
        request_id: ID da requisição para correlação
        
    Returns:
        Lista de floats representando o embedding ou None se o texto for inválido.
    """
    request_id = request_id or "unknown"
    
    if not text or not isinstance(text, str):
        return None
        
    # Verificar cache
    if use_cache and EMBEDDING_CACHE_ENABLED:
        cached = embedding_cache.get(text)
        if cached is not None:
            logger.debug("Embedding from Cache | request_id=%s | text_len=%d", request_id, len(text))
            return cached
    
    start_time = time.time()
    
    # Limpeza do texto
    text_clean = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    
    if len(text_clean) < 10:
        logger.debug("Texto muito pequeno (%d chars) após limpeza. Retornando None.", len(text_clean))
        return None
    
    if len(text_clean.strip(' \n\r\t.,!?;:()[]{}<>"/\'-=+*&^%$#@|~`_')) < 5:
        logger.debug("Texto composto principalmente de caracteres especiais. Retornando None.")
        return None

    try:
        response = requests.post(
            f"{LM_STUDIO_BASE_URL}/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "input": text_clean
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        embedding = data["data"][0]["embedding"]
        
        duration = time.time() - start_time
        
        # Validar integridade do vetor
        if not embedding or not isinstance(embedding, list) or any(v is None for v in embedding):
            logger.warning("Embedding com valores nulos retornado pelo modelo. Tentando retry único...")
            time.sleep(0.5)
            response = requests.post(
                f"{LM_STUDIO_BASE_URL}/embeddings",
                json={"model": EMBEDDING_MODEL, "input": text_clean},
                timeout=60
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
        
        logger.debug("Embedding Generated | request_id=%s | dim=%d | duration=%.3fs", request_id, len(embedding), duration)
        
        if use_cache and EMBEDDING_CACHE_ENABLED and embedding:
            embedding_cache.set(text, embedding)
            
        return embedding
        
    except Exception as e:
        logger.error("Erro na geração de embedding | request_id=%s | erro=%s", request_id, e)
        raise


def get_embeddings_batch(texts: List[str], batch_size: int = 32, document_name: str = None, request_id: str = None) -> List[List[float]]:
    """
    Gera embeddings para múltiplos textos em batch.
    """
    all_embeddings = []
    total_start = time.time()
    request_id = request_id or "unknown"
    
    logger.info("Batch Embedding Started | request_id=%s | doc=%s | count=%d | batch_size=%d",
                request_id, document_name or "unknown", len(texts), batch_size)
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_clean = ["".join(char for char in t if char.isprintable() or char in "\n\r\t").strip() for t in batch]
        
        try:
            response = requests.post(
                f"{LM_STUDIO_BASE_URL}/embeddings",
                json={"model": EMBEDDING_MODEL, "input": batch_clean},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            batch_embeddings = [item.get("embedding") for item in sorted_data]
            all_embeddings.extend(batch_embeddings)
            
        except Exception as e:
            logger.warning("Falha no batch de embeddings, tentando item a item: %s", e)
            for single_text in batch:
                try:
                    emb = get_embedding(single_text, use_cache=True, request_id=request_id)
                    all_embeddings.append(emb)
                except Exception:
                    all_embeddings.append(None)
                    
        logger.debug("Embeddings progresso: %d/%d chunks processados", min(i + batch_size, len(texts)), len(texts))
    
    total_duration = time.time() - total_start
    logger.info("Batch Embedding Complete | request_id=%s | total=%d | duration=%.2fs",
                request_id, len(all_embeddings), total_duration)
    return all_embeddings


def check_embedding_service() -> bool:
    """Verifica se o serviço de embeddings está disponível."""
    try:
        embedding = get_embedding("teste de conexao")
        return bool(embedding and len(embedding) > 0)
    except Exception as e:
        logger.error("Serviço de embedding indisponível: %s", e)
        return False
