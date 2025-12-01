"""
Módulo de integração com o LLM (Phi-3.5 Mini) via LM Studio API.
"""
import requests
from typing import Optional, Generator

from src.config import LM_STUDIO_BASE_URL, LLM_MODEL


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
    
    if stream:
        return _generate_stream(payload)
    
    response = requests.post(
        f"{LM_STUDIO_BASE_URL}/chat/completions",
        json=payload,
        timeout=120
    )
    
    response.raise_for_status()
    data = response.json()
    
    return data["choices"][0]["message"]["content"]


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
    
    response = requests.post(
        f"{LM_STUDIO_BASE_URL}/chat/completions",
        json=payload,
        timeout=120
    )
    
    response.raise_for_status()
    data = response.json()
    
    return data["choices"][0]["message"]["content"]


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
            print(f"✅ LLM disponível. Modelos: {available_models}")
            return True
        else:
            print(f"⚠️ Nenhum modelo Phi encontrado. Disponíveis: {available_models}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no serviço LLM: {e}")
        return False
