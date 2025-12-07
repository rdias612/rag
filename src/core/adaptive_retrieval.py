"""
Módulo de Adaptive Retrieval.

Ajusta dinamicamente os parâmetros de busca (top_k, min_similarity)
baseado na complexidade e características da query.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def analyze_query_complexity(question: str) -> dict:
    """
    Analisa a complexidade de uma query.
    
    Args:
        question: Pergunta do usuário
        
    Returns:
        Dict com métricas de complexidade
    """
    words = question.split()
    word_count = len(words)
    
    # Detectar características
    has_technical_terms = bool(re.search(r'\b[A-Z]{2,}\b', question))  # Siglas
    has_numbers = bool(re.search(r'\d+', question))
    has_quotes = '"' in question or "'" in question
    is_compound = any(word in question.lower() for word in ['e', 'ou', 'versus', 'vs', 'comparar'])
    
    # Calcular score de complexidade (0-10)
    complexity_score = 0
    
    if word_count < 3:
        complexity_score += 1  # Query muito curta
    elif word_count > 15:
        complexity_score += 3  # Query detalhada
    else:
        complexity_score += 2
    
    if has_technical_terms:
        complexity_score += 2
    if has_numbers:
        complexity_score += 1
    if has_quotes:
        complexity_score += 1  # Busca específica
    if is_compound:
        complexity_score += 2  # Múltiplos conceitos
    
    return {
        "word_count": word_count,
        "complexity_score": min(10, complexity_score),
        "has_technical_terms": has_technical_terms,
        "has_numbers": has_numbers,
        "has_quotes": has_quotes,
        "is_compound": is_compound
    }


def get_adaptive_params(
    question: str,
    base_top_k: int = 5,
    base_min_similarity: float = 0.45
) -> dict:
    """
    Retorna parâmetros de busca adaptados à query.
    
    Args:
        question: Pergunta do usuário
        base_top_k: Valor base de top_k
        base_min_similarity: Valor base de min_similarity
        
    Returns:
        Dict com top_k e min_similarity ajustados
    """
    analysis = analyze_query_complexity(question)
    word_count = analysis["word_count"]
    complexity = analysis["complexity_score"]
    
    # Ajustar top_k
    if word_count < 5:
        # Query curta: buscar mais para compensar falta de contexto
        top_k = base_top_k + 5
        min_similarity = base_min_similarity + 0.05  # Mais restritivo
    elif word_count > 15:
        # Query detalhada: menos resultados, mais precisos
        top_k = max(3, base_top_k - 2)
        min_similarity = base_min_similarity - 0.1  # Menos restritivo
    else:
        # Query média
        top_k = base_top_k
        min_similarity = base_min_similarity
    
    # Ajustes por características especiais
    if analysis["is_compound"]:
        # Comparações precisam de mais chunks
        top_k = min(15, top_k + 3)
    
    if analysis["has_quotes"]:
        # Busca específica: ser mais restritivo
        min_similarity = min(0.7, min_similarity + 0.1)
    
    if analysis["has_technical_terms"]:
        # Termos técnicos: confiar mais nos resultados
        min_similarity = max(0.3, min_similarity - 0.05)
    
    result = {
        "top_k": top_k,
        "min_similarity": round(min_similarity, 2),
        "analysis": analysis,
        "adaptive_applied": True
    }
    
    logger.info(f"Adaptive params: top_k={top_k}, min_sim={min_similarity:.2f} for query ({word_count} words)")
    
    return result


def should_use_adaptive(question: str, min_words: int = 2) -> bool:
    """
    Verifica se deve usar adaptive retrieval.
    
    Args:
        question: Pergunta
        min_words: Mínimo de palavras para considerar
        
    Returns:
        True se deve usar adaptive
    """
    return len(question.split()) >= min_words


def check_adaptive_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "version": "1.0"
    }
