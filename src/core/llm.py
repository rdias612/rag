"""
Módulo de integração com o LLM (Phi-3.5 Mini) via LM Studio API.
"""
import time
import json
import requests
from typing import Generator

from src.config import LM_STUDIO_BASE_URL, LLM_MODEL
from src.core.logger import get_logger

logger = get_logger("core.llm")


def generate_response(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False,
    request_id: str = None
) -> str:
    """
    Gera uma resposta usando o modelo de LLM configurado.
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
    logger.debug("LLM Request Started | request_id=%s | model=%s | prompt_len=%d",
                 request_id, LLM_MODEL, len(prompt))
    
    if stream:
        return _generate_stream(payload, request_id)
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{LM_STUDIO_BASE_URL}/chat/completions",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        
        result = data["choices"][0]["message"]["content"]
        duration = time.time() - start_time
        
        logger.info("LLM Complete | request_id=%s | response_len=%d | duration=%.3fs",
                    request_id, len(result), duration)
        return result
    except Exception as e:
        logger.error("Erro na chamada LLM | request_id=%s | error=%s", request_id, e)
        raise


def _generate_stream(payload: dict, request_id: str = "unknown") -> Generator[str, None, None]:
    """
    Gera resposta em streaming.
    """
    logger.debug("LLM Stream Started | request_id=%s | model=%s", request_id, payload.get("model"))
    try:
        response = requests.post(
            f"{LM_STUDIO_BASE_URL}/chat/completions",
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        logger.debug("LLM Stream Finished | request_id=%s", request_id)
    except Exception as e:
        logger.error("LLM Stream Error | request_id=%s | error=%s", request_id, e)
        raise


def generate_with_system_prompt(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7
) -> str:
    """
    Gera uma resposta com system prompt separado.
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
        "temperature": temperature,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{LM_STUDIO_BASE_URL}/chat/completions",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Erro na geração com system prompt: %s", e)
        raise


def check_llm_service() -> bool:
    """Verifica se o serviço LLM está disponível."""
    try:
        response = generate_response("Diga olá em uma palavra", max_tokens=10)
        return bool(response and len(response.strip()) > 0)
    except Exception as e:
        logger.error("Serviço LLM indisponível: %s", e)
        return False
