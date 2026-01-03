"""
Módulo de geração de embeddings via LM Studio API (Nomic Embed v1.5).
"""
import time
import re
import logging
import requests
from typing import Union

from src.config import LM_STUDIO_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSION
from src.config import EMBEDDING_CACHE_ENABLED
from src.core.embedding_cache import embedding_cache


embedding_logger = logging.getLogger("rag.embeddings")


def get_embedding(text: str, use_cache: bool = True, request_id: str = None) -> list[float]:
    """
    Gera o embedding de um texto usando o modelo Nomic Embed v1.5.
    
    Args:
        text: Texto para gerar embedding
        use_cache: Se True, usa cache para evitar recálculo (default: True)
        
    Returns:
        Lista de floats representando o embedding
    """
    request_id = request_id or "unknown"
    
    # Verificar cache primeiro (se habilitado)
    if use_cache and EMBEDDING_CACHE_ENABLED:
        cached = embedding_cache.get(text)
        if cached is not None:
            embedding_logger.info("Embedding from Cache | request_id=%s | text_len=%d",
                                 request_id, len(text))
            return cached
    
    start_time = time.time()
    
    embedding_logger.info("Embedding Generation Started | request_id=%s | text_len=%d",
                         request_id, len(text))
    
    # Limpeza robusta do texto para evitar erros no modelo/LM Studio
    # 1. Remover caracteres não imprimíveis e de controle (exceto \n, \r, \t)
    text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
    # 2. Normalizar espaços (múltiplos espaços viram um único)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # 3. Validar tamanho mínimo do texto (chunks muito pequenos causam problemas)
    if len(text) < 10:
        embedding_logger.warning("Texto muito pequeno (%d chars) após limpeza. Retornando None.", len(text))
        return None
    
    # 4. Validar conteúdo do texto (evitar chunks só com caracteres especiais)
    if len(text.strip(' \n\r\t.,!?;:()[]{}<>"/\'-=+*&^%$#@|~`_')) < 5:
        embedding_logger.warning("Texto composto principalmente de caracteres especiais. Retornando None.")
        return None

    # Log do texto enviado para embedding
    embedding_logger.info("Embedding Request | model=%s | text_len=%d", EMBEDDING_MODEL, len(text))
    
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
    
    # Validar embedding de forma mais detalhada
    null_count = sum(1 for v in embedding if v is None)
    nan_count = sum(1 for v in embedding if isinstance(v, float) and (v != v))  # NaN check
    inf_count = sum(1 for v in embedding if isinstance(v, float) and (v == float('inf') or v == float('-inf')))
    
    is_valid = (
        embedding is not None and 
        isinstance(embedding, list) and 
        len(embedding) > 0 and 
        null_count == 0 and
        nan_count == 0 and
        inf_count == 0
    )

    if not is_valid:
        error_details = []
        if embedding is None:
            error_details.append("embedding is None")
        if not isinstance(embedding, list):
            error_details.append("not a list")
        if null_count > 0:
            error_details.append(f"{null_count} NULLs")
        if nan_count > 0:
            error_details.append(f"{nan_count} NaNs")
        if inf_count > 0:
            error_details.append(f"{inf_count} Infs")
        
        error_reason = ", ".join(error_details)
        
        # Logar o texto que causou problema para análise
        text_sample = text[:150] + "..." if len(text) > 150 else text
        embedding_logger.warning(
            "Embedding inválido retornado para '%s'. Texto: %d chars, Embedding: %d dims. Erro: %s. Tentando retry único...",
            text_sample, len(text), len(embedding) if embedding else 0, error_reason
        )
        
        # Um pequeno sleep antes de tentar de novo
        time.sleep(1.0)
        
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
        
        # Validar novamente após retry
        null_count = sum(1 for v in embedding if v is None)
        nan_count = sum(1 for v in embedding if isinstance(v, float) and (v != v))
        inf_count = sum(1 for v in embedding if isinstance(v, float) and (v == float('inf') or v == float('-inf')))
        
        is_valid = (
            embedding is not None and 
            isinstance(embedding, list) and 
            len(embedding) > 0 and 
            null_count == 0 and
            nan_count == 0 and
            inf_count == 0
        )
        
        if not is_valid:
            error_details = []
            if embedding is None:
                error_details.append("embedding is None")
            if not isinstance(embedding, list):
                error_details.append("not a list")
            if null_count > 0:
                error_details.append(f"{null_count} NULLs")
            if nan_count > 0:
                error_details.append(f"{nan_count} NaNs")
            if inf_count > 0:
                error_details.append(f"{inf_count} Infs")
            
            error_reason = ", ".join(error_details)
            
            # Log mais detalhado para debug
            text_sample = text[:150] + "..." if len(text) > 150 else text
            embedding_logger.error(
                "ERRO: Embedding inválido após retry. Texto: '%s' (%d chars). Erro: %s",
                text_sample, len(text), error_reason
            )
            raise ValueError(f"O modelo de embeddings retornou um valor inválido ({error_reason}) após retry para o texto: '{text[:50]}...'")

    # Log do embedding gerado
    embedding_logger.info("Embedding Response | dim=%d | duration=%.3fs", len(embedding), duration)
    
    embedding_logger.info("Embedding Generated | request_id=%s | dimension=%d | duration=%s | was_cached=%s",
                         request_id, len(embedding), f"{duration:.3f}s", False)
    
    # Armazenar no cache (se habilitado)
    if use_cache and EMBEDDING_CACHE_ENABLED:
        embedding_cache.set(text, embedding)
        embedding_logger.info("Embedding Cached | request_id=%s", request_id)
    
    return embedding


def get_embeddings_batch(texts: list[str], batch_size: int = 32, document_name: str = None, request_id: str = None) -> list[list[float]]:
    """
    Gera embeddings para múltiplos textos em batch.
    
    Args:
        texts: Lista de textos para gerar embeddings
        batch_size: Tamanho do batch para cada requisição
        document_name: Nome do documento sendo processado (para log)
        
    Returns:
        Lista de embeddings (cada um é uma lista de floats)
    """
    all_embeddings = []
    total_start = time.time()
    request_id = request_id or "unknown"
    
    doc_info = f" [{document_name}]" if document_name else ""
    embedding_logger.info("Batch Embedding Started | request_id=%s | document_name=%s | texts_count=%d | batch_size=%d",
                         request_id, document_name or "unknown", len(texts), batch_size)
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Limpar textos do batch para evitar que um caracter estranho derrube o batch todo
        batch = ["".join(char for char in t if char.isprintable() or char in "\n\r\t").strip() for t in batch]
        
        batch_start = time.time()
        
        embedding_logger.info("Embedding Batch Request | model=%s | texts_count=%d", EMBEDDING_MODEL, len(batch))
        
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
        
        # Validar e retentar individualmente se necessário
        validated_embeddings = []
        for idx, emb in enumerate(batch_embeddings):
            # Validação robusta igual à função individual
            null_count = sum(1 for v in emb if v is None) if emb else 0
            nan_count = sum(1 for v in emb if isinstance(v, float) and (v != v)) if emb else 0
            inf_count = sum(1 for v in emb if isinstance(v, float) and (v == float('inf') or v == float('-inf'))) if emb else 0
            
            is_valid = (
                emb is not None and 
                isinstance(emb, list) and 
                len(emb) > 0 and 
                null_count == 0 and
                nan_count == 0 and
                inf_count == 0
            )
            
            if is_valid:
                validated_embeddings.append(emb)
            else:
                # Tentar recuperar individualmente
                orig_idx = i + idx
                problematic_text = texts[orig_idx]
                
                error_details = []
                if emb is None:
                    error_details.append("embedding is None")
                if not isinstance(emb, list):
                    error_details.append("not a list")
                if null_count > 0:
                    error_details.append(f"{null_count} NULLs")
                if nan_count > 0:
                    error_details.append(f"{nan_count} NaNs")
                if inf_count > 0:
                    error_details.append(f"{inf_count} Infs")
                
                error_reason = ", ".join(error_details)
                text_sample = problematic_text[:100] + "..." if len(problematic_text) > 100 else problematic_text
                
                embedding_logger.warning(
                    "Embedding inválido no batch (index %d). Texto: '%s' (%d chars). Erro: %s. Tentando recuperação individual...",
                    orig_idx, text_sample, len(problematic_text), error_reason
                )
                
                try:
                    # Retry individualmente (sem cache para garantir nova tentativa)
                    # Adicionamos um pequeno delay preventivo
                    time.sleep(0.5)
                    recovered_emb = get_embedding(problematic_text, use_cache=False)
                    
                    # Log de sucesso na recuperação
                    embedding_logger.info("Sucesso ao recuperar embedding individual para index %d", orig_idx)
                    validated_embeddings.append(recovered_emb)
                except Exception as e:
                    # Se falhar mesmo individualmente, colocamos None e o banco lidará com isso
                    validated_embeddings.append(None)
                    
                    # Log mais informativo e menos assustador, pois o sistema irá ignorar este trecho
                    embedding_logger.warning(
                        "CHUNK IGNORADO (Falha persistente no modelo) no index %d: '%s'. Motivo: %s",
                        orig_idx, text_sample, str(e)
                    )

        all_embeddings.extend(validated_embeddings)
        
        batch_duration = time.time() - batch_start
        embedding_logger.info("Embedding Batch Response | count=%d | duration=%.3fs | dim=%d",
                             len(batch), batch_duration, EMBEDDING_DIMENSION)
        
        embedding_logger.info("Embeddings progress%s: %d/%d chunks", doc_info, min(i + batch_size, len(texts)), len(texts))
    
    total_duration = time.time() - total_start
    embedding_logger.info("Batch Embedding Complete | request_id=%s | document_name=%s | total_embeddings=%d | total_duration=%s",
                         request_id, document_name or "unknown", len(all_embeddings), f"{total_duration:.2f}s")
    
    return all_embeddings


def check_embedding_service() -> bool:
    """Verifica se o serviço de embeddings está disponível."""
    try:
        # Testar com um texto simples
        embedding = get_embedding("teste")
        embedding_logger.info("Embedding service available. Dimension: %d", len(embedding))
        return len(embedding) > 0
    except Exception as e:
        embedding_logger.error("Embedding service error: %s", str(e))
        return False
