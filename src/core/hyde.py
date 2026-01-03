"""
Módulo HyDE (Hypothetical Document Embeddings).

Gera respostas hipotéticas para queries, usa o embedding dessa resposta
para buscar documentos, melhorando significativamente o recall.
"""

import time
from typing import Optional

from src.core.llm import generate_response
from src.core.embeddings import get_embedding
from src.core.prompts import get_active_prompt

# Prompt para gerar documento hipotético
HYDE_PROMPT = """Como um redator técnico sênior, escreva um parágrafo detalhado que seria a resposta técnica ideal para a pergunta abaixo. 
Não use frases como "Eu acho que" ou "Este documento descreve". Escreva como se fosse o próprio conteúdo original de um manual ou documentação técnica oficial. 

Pergunta: "{question}"

Conteúdo Técnico Esperado:"""


HYDE_PROMPT_CONCISE = """Escreva uma resposta direta, técnica e factual para a pergunta abaixo, como se estivesse em uma documentação técnica:

Pergunta: "{question}"

Resposta:"""


def generate_hypothetical_document(
    question: str,
    temperature: float = 0.3,
    max_tokens: int = 256,
    concise: bool = True
) -> str:
    """
    Gera um documento/resposta hipotética para a pergunta.
    
    A ideia é que a resposta hipotética terá embedding mais similar
    aos chunks relevantes do que a query original.
    
    Args:
        question: Pergunta do usuário
        temperature: Temperatura baixa para resposta mais determinística
        max_tokens: Máximo de tokens na resposta
        concise: Se True, usa prompt conciso
        
    Returns:
        Documento hipotético gerado
    """
    start_time = time.time()
    
    prompt_template = get_active_prompt('hyde_prompt_concise' if concise else 'hyde_prompt')
    prompt = prompt_template.format(question=question)
    
    try:
        hypothetical_doc = generate_response(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        duration = time.time() - start_time
        print("HyDE: Generated hypothetical doc (%d chars) in %.2fs",
                     len(hypothetical_doc), duration)
        
        return hypothetical_doc.strip()
        
    except Exception as e:
        print("HyDE generation failed: %s", str(e))
        # Fallback: retornar a própria pergunta
        return question


def get_hyde_embedding(
    question: str,
    temperature: float = 0.3
) -> tuple[list[float], str]:
    """
    Gera embedding do documento hipotético.
    
    Args:
        question: Pergunta do usuário
        temperature: Temperatura para geração
        
    Returns:
        Tupla (embedding, documento_hipotético)
    """
    # Gerar documento hipotético
    hypothetical_doc = generate_hypothetical_document(question, temperature)
    
    # Gerar embedding do documento hipotético
    embedding = get_embedding(hypothetical_doc)
    
    return embedding, hypothetical_doc

def generate_hyde_embedding(
    question: str,
    temperature: float = 0.3
) -> list[float]:
    """Convenience wrapper that returns only HyDE embedding."""
    embedding, _ = get_hyde_embedding(question, temperature)
    return embedding

def hyde_enhanced_query(
    question: str,
    original_embedding: list[float],
    hyde_weight: float = 0.5
) -> tuple[list[float], dict]:
    """
    Combina embedding original com HyDE para busca melhorada.
    
    Args:
        question: Pergunta do usuário
        original_embedding: Embedding da pergunta original
        hyde_weight: Peso do embedding HyDE (0.0 = só original, 1.0 = só HyDE)
        
    Returns:
        Tupla (embedding_combinado, métricas)
    """
    start_time = time.time()
    
    # Gerar embedding HyDE
    hyde_embedding, hypothetical_doc = get_hyde_embedding(question)
    
    # Combinar embeddings (interpolação linear)
    combined_embedding = []
    for orig, hyde in zip(original_embedding, hyde_embedding):
        combined = (1 - hyde_weight) * orig + hyde_weight * hyde
        combined_embedding.append(combined)
    
    duration = time.time() - start_time
    
    metrics = {
        "hyde_applied": True,
        "hyde_weight": hyde_weight,
        "hypothetical_doc_length": len(hypothetical_doc),
        "hyde_time_ms": round(duration * 1000, 2)
    }
    
    print("HyDE: Combined embedding with weight %s in %.2fs", hyde_weight, duration)
    
    return combined_embedding, metrics

def check_hyde_available() -> dict:
    """Verifica status do módulo HyDE."""
    return {
        "available": True,
        "method": "llm_hypothetical"
    }
