"""
Módulo de integração com o LLM (Phi-3.5 Mini) via LM Studio API.
"""
import time
import json
import logging
import requests
from typing import Optional, Generator

from src.config import LM_STUDIO_BASE_URL, LLM_MODEL


llm_logger = logging.getLogger("rag.llm")


def generate_response(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False,
    request_id: str = None
) -> str:
    """
    Gera uma resposta usando o modelo Phi-3.5 Mini.
    
    Args:
        prompt: Prompt completo (com contexto e pergunta)
        max_tokens: Número máximo de tokens na resposta
        temperature: Temperatura para geração (0.0 = determinístico, 1.0 = criativo)
        stream: Se True, retorna um generator para streaming
        
    Returns:
        Resposta gerada pelo modelo
    """
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream
    }
    
    request_id = request_id or "unknown"
    
    # Log início da requisição
    llm_logger.info("LLM Request Started | request_id=%s | model=%s | prompt_len=%d | max_tokens=%d | temperature=%s | stream=%s",
                   request_id, LLM_MODEL, len(prompt), max_tokens, temperature, stream)
    
    # Log da requisição (resumo)
    llm_logger.info("LLM Request | model=%s | prompt_len=%d | params=%s",
                   LLM_MODEL, len(prompt), {"max_tokens": max_tokens, "temperature": temperature, "stream": stream})
    
    # Log da requisição completa (detalhado)
    llm_logger.debug("LLM Full Request | url=%s | payload=%s",
                    LM_STUDIO_BASE_URL + "/chat/completions", payload)
    
    if stream:
        return _generate_stream(payload)
    
    start_time = time.time()
    
    response = requests.post(
        f"{LM_STUDIO_BASE_URL}/chat/completions",
        json=payload,
        timeout=120
    )
    
    response.raise_for_status()
    data = response.json()
    
    result = data["choices"][0]["message"]["content"]
    duration = time.time() - start_time
    
    llm_logger.info("LLM Response Received | request_id=%s | response_len=%d | duration=%s",
                   request_id, len(result), f"{duration:.3f}s")
    
    # Extrair tokens se disponível
    tokens = data.get("usage", {}).get("completion_tokens")
    
    # Log da resposta (resumo)
    llm_logger.info("LLM Response | response_len=%d | duration=%.3fs | tokens=%s",
                   len(result), duration, tokens)
    
    # Log da resposta completa (detalhado - JSON original)
    llm_logger.debug("LLM Full Response | response=%s", data)
    
    llm_logger.info("LLM Complete | request_id=%s | total_duration=%s | status=%s",
                   request_id, f"{duration:.3f}s", "success")
    
    return result


def _generate_stream(payload: dict) -> Generator[str, None, None]:
    """
    Gera resposta em streaming.
    
    Args:
        payload: Payload da requisição
        
    Yields:
        Tokens da resposta conforme são gerados
    """
    response = requests.post(
        f"{LM_STUDIO_BASE_URL}/chat/completions",
        json=payload,
        stream=True,
        timeout=120
    )
    
    try:
        response.raise_for_status()
        
        llm_logger.info("LLM Stream Started | request_id=%s | model=%s",
                       "unknown", payload.get("model"))
        
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        llm_logger.info("LLM Stream Complete | request_id=%s | status=%s",
                                       "unknown", "done")
                        break
                        
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        llm_logger.exception("LLM Stream Error | request_id=%s | model=%s | error_type=%s | error_message=%s",
                           "unknown", payload.get("model"), type(e).__name__, str(e))
        raise


def generate_with_system_prompt(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7
) -> str:
    """
    Gera uma resposta com system prompt separado.
    
    Args:
        system_prompt: Instruções do sistema
        user_prompt: Prompt do usuário
        max_tokens: Número máximo de tokens na resposta
        temperature: Temperatura para geração
        
    Returns:
        Resposta gerada pelo modelo
    """
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    # Log da requisição (resumo)
    full_prompt = f"[SYSTEM] {system_prompt}\n[USER] {user_prompt}"
    llm_logger.info("LLM Request | model=%s | prompt_len=%d | params=%s",
                   LLM_MODEL, len(full_prompt), {"max_tokens": max_tokens, "temperature": temperature})
    
    # Log da requisição completa (detalhado)
    llm_logger.debug("LLM Full Request | url=%s | payload=%s",
                    LM_STUDIO_BASE_URL + "/chat/completions", payload)
    
    start_time = time.time()
    
    response = requests.post(
        f"{LM_STUDIO_BASE_URL}/chat/completions",
        json=payload,
        timeout=120
    )
    
    response.raise_for_status()
    data = response.json()
    
    result = data["choices"][0]["message"]["content"]
    duration = time.time() - start_time
    
    # Log da resposta (resumo)
    tokens = data.get("usage", {}).get("completion_tokens")
    llm_logger.info("LLM Response | response_len=%d | duration=%.3fs | tokens=%s",
                   len(result), duration, tokens)
    
    # Log da resposta completa (detalhado - JSON original)
    llm_logger.debug("LLM Full Response | response=%s", data)
    
    return result


def check_llm_service() -> bool:
    """Verifica se o serviço LLM está disponível."""
    try:
        response = requests.get(
            f"{LM_STUDIO_BASE_URL}/models",
            timeout=10
        )
        response.raise_for_status()
        
        models = response.json()
        available_models = [m["id"] for m in models.get("data", [])]
        
        # Verificar se algum modelo phi está disponível
        phi_available = any("phi" in m.lower() for m in available_models)
        
        if phi_available:
            llm_logger.info("LLM service available. Models: %s", available_models)
            return True
        else:
            llm_logger.warning("No Phi model found. Available: %s", available_models)
            return False
            
    except Exception as e:
        llm_logger.error("LLM service error: %s", str(e))
        return False
