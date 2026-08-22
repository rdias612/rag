"""
Módulo de Avaliação RAGAS.

Implementa métricas inspiradas no framework RAGAS para avaliar
qualidade das respostas do RAG de forma automatizada.

Métricas:
- Faithfulness: resposta é fiel ao contexto?
- Answer Relevancy: resposta é relevante à pergunta?
- Context Precision: chunks recuperados são relevantes?
"""
import re
import math
from typing import Optional, List, Dict

from src.core.llm import generate_response
from src.core.embeddings import get_embedding
from src.core.logger import get_logger

logger = get_logger("core.evaluation")


def calculate_faithfulness(answer: str, context: str) -> float:
    """
    Avalia se a resposta é fiel ao contexto fornecido.
    """
    prompt = f"""Avalie se a resposta abaixo é baseada APENAS no contexto fornecido.

CONTEXTO:
{context[:3000]}

RESPOSTA:
{answer}

Instruções:
1. Identifique cada afirmação factual na resposta
2. Verifique se cada afirmação está presente ou pode ser inferida do contexto
3. Calcule a porcentagem de afirmações suportadas pelo contexto

Responda APENAS com um número de 0 a 100 representando a porcentagem de afirmações fiéis ao contexto.
Exemplo: 85

Score:"""

    try:
        response = generate_response(prompt, temperature=0.1, max_tokens=10)
        numbers = re.findall(r'\d+', response)
        if numbers:
            return min(100, max(0, int(numbers[0]))) / 100.0
        return 0.5
    except Exception as e:
        logger.warning("Faithfulness calculation failed: %s", e)
        return 0.5


def calculate_answer_relevancy(question: str, answer: str) -> float:
    """
    Avalia se a resposta é relevante para a pergunta.
    """
    prompt = f"""Avalie se a resposta abaixo responde adequadamente à pergunta.

PERGUNTA:
{question}

RESPOSTA:
{answer}

Critérios:
- A resposta aborda diretamente o que foi perguntado?
- A resposta é completa e suficiente?
- A resposta é clara e bem estruturada?

Responda APENAS com um número de 0 a 100 representando o quão relevante é a resposta.
Exemplo: 75

Score:"""

    try:
        response = generate_response(prompt, temperature=0.1, max_tokens=10)
        numbers = re.findall(r'\d+', response)
        if numbers:
            return min(100, max(0, int(numbers[0]))) / 100.0
        return 0.5
    except Exception as e:
        logger.warning("Answer relevancy calculation failed: %s", e)
        return 0.5


def calculate_context_precision(question: str, chunks: List[dict]) -> float:
    """
    Avalia se os chunks recuperados são relevantes para a pergunta via similaridade de cosseno.
    """
    if not chunks:
        return 0.0
    
    try:
        question_embedding = get_embedding(question)
        if not question_embedding:
            return 0.5
            
        similarities = []
        for chunk in chunks[:5]:
            if "similarity" in chunk:
                similarities.append(chunk["similarity"])
            else:
                chunk_embedding = get_embedding(chunk.get("content", "")[:500])
                if chunk_embedding:
                    sim = _cosine_similarity(question_embedding, chunk_embedding)
                    similarities.append(sim)
        
        if similarities:
            return sum(similarities) / len(similarities)
        return 0.5
        
    except Exception as e:
        logger.warning("Context precision calculation failed: %s", e)
        return 0.5


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calcula similaridade de cosseno."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)


def evaluate_rag_response(
    question: str,
    answer: str,
    context: str,
    chunks: List[dict] = None
) -> dict:
    """
    Avalia uma resposta RAG usando métricas RAGAS.
    """
    logger.debug("Iniciando avaliação da resposta RAG...")
    
    faithfulness = calculate_faithfulness(answer, context)
    relevancy = calculate_answer_relevancy(question, answer)
    precision = calculate_context_precision(question, chunks) if chunks else None
    
    metrics_count = 2 + (1 if precision is not None else 0)
    overall = (faithfulness + relevancy + (precision or 0)) / metrics_count
    
    result = {
        "faithfulness": round(faithfulness, 3),
        "answer_relevancy": round(relevancy, 3),
        "overall_score": round(overall, 3)
    }
    
    if precision is not None:
        result["context_precision"] = round(precision, 3)
    
    logger.debug("Resultado da Avaliação: %s", result)
    return result


def get_evaluation_summary(scores: dict) -> str:
    """Gera resumo textual da avaliação."""
    overall = scores.get("overall_score", 0)
    if overall >= 0.8:
        quality = "Excelente"
    elif overall >= 0.6:
        quality = "Boa"
    elif overall >= 0.4:
        quality = "Moderada"
    else:
        quality = "Precisa melhorar"
    return f"Qualidade: {quality} (Score: {overall:.1%})"


def check_evaluation_available() -> dict:
    """Verifica status do módulo de avaliação."""
    return {
        "available": True,
        "metrics": ["faithfulness", "answer_relevancy", "context_precision"]
    }
