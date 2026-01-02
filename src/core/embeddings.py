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
    
    # Limpeza robusta do texto para evitar erros no modelo/LM Studio
    # 1. Remover caracteres não imprimíveis e de controle (exceto \n, \r, \t)
    text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
    # 2. Normalizar espaços (múltiplos espaços viram um único)
    import re
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # 3. Validar tamanho mínimo do texto (chunks muito pequenos causam problemas)
    if len(text) < 10:
        embedding_logger.warning(f"Texto muito pequeno ({len(text)} chars) após limpeza. Retornando None.")
        return None
    
    # 4. Validar conteúdo do texto (evitar chunks só com caracteres especiais)
    if len(text.strip(' \n\r\t.,!?;:()[]{}<>"/\'-=+*&^%$#@|~`_')) < 5:
        embedding_logger.warning("Texto composto principalmente de caracteres especiais. Retornando None.")
        return None

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
            f"Embedding inválido retornado para '{text_sample}'. "
            f"Texto: {len(text)} chars, Embedding: {len(embedding) if embedding else 0} dims. "
            f"Erro: {error_reason}. Tentando retry único..."
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
                f"ERRO: Embedding inválido após retry. "
                f"Texto: '{text_sample}' ({len(text)} chars). "
                f"Erro: {error_reason}"
            )
            raise ValueError(f"O modelo de embeddings retornou um valor inválido ({error_reason}) após retry para o texto: '{text[:50]}...'")

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
        
        # Limpar textos do batch para evitar que um caracter estranho derrube o batch todo
        batch = ["".join(char for char in t if char.isprintable() or char in "\n\r\t").strip() for t in batch]
        
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
                    f"Embedding inválido no batch (index {orig_idx}). "
                    f"Texto: '{text_sample}' ({len(problematic_text)} chars). "
                    f"Erro: {error_reason}. Tentando recuperação individual..."
                )
                
                try:
                    # Retry individualmente (sem cache para garantir nova tentativa)
                    # Adicionamos um pequeno delay preventivo
                    time.sleep(0.5)
                    recovered_emb = get_embedding(problematic_text, use_cache=False)
                    
                    # Log de sucesso na recuperação
                    embedding_logger.info(f"Sucesso ao recuperar embedding individual para index {orig_idx}")
                    validated_embeddings.append(recovered_emb)
                except Exception as e:
                    # Se falhar mesmo individualmente, colocamos None e o banco lidará com isso
                    validated_embeddings.append(None)
                    
                    # Log mais informativo e menos assustador, pois o sistema irá ignorar este trecho
                    embedding_logger.warning(
                        f"CHUNK IGNORADO (Falha persistente no modelo) no index {orig_idx}: '{text_sample}'. "
                        f"Motivo: {str(e)}"
                    )

        all_embeddings.extend(validated_embeddings)
        
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
