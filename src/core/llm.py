"""
Módulo de integração com o LLM (Phi-3.5 Mini) via LM Studio API.
"""
import time
import requests
from typing import Optional, Generator

from src.config import LM_STUDIO_BASE_URL, LLM_MODEL
from src.core.logger import (
    llm_logger,
    log_llm_request,
    log_llm_response
)


def generate_response(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False
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
    
    # Log da requisição
    log_llm_request(prompt, LLM_MODEL, {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream
    })
    
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
    
    # Extrair tokens se disponível
    tokens = data.get("usage", {}).get("completion_tokens")
    
    # Log da resposta
    log_llm_response(result, duration, tokens)
    
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
    
    response.raise_for_status()
    
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                    
                import json
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue


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
    
    # Log da requisição
    full_prompt = f"[SYSTEM] {system_prompt}\n[USER] {user_prompt}"
    log_llm_request(full_prompt, LLM_MODEL, {
        "max_tokens": max_tokens,
        "temperature": temperature
    })
    
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
    
    # Log da resposta
    tokens = data.get("usage", {}).get("completion_tokens")
    log_llm_response(result, duration, tokens)
    
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
            llm_logger.info(f"LLM service available. Models: {available_models}")
            return True
        else:
            llm_logger.warning(f"No Phi model found. Available: {available_models}")
            return False
            
    except Exception as e:
        llm_logger.error(f"LLM service error: {e}")
        return False
