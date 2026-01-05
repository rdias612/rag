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
from typing import Optional

from src.core.llm import generate_response
from src.core.embeddings import get_embedding

print(__name__)


def calculate_faithfulness(answer: str, context: str) -> float:
    """
    Avalia se a resposta é fiel (baseada) no contexto fornecido.
    
    Usa LLM para verificar se as afirmações da resposta estão no contexto.
    
    Args:
        answer: Resposta gerada pelo RAG
        context: Contexto usado para gerar a resposta
        
    Returns:
        Score de 0.0 a 1.0
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
        # Extrair número da resposta
        numbers = re.findall(r'\d+', response)
        if numbers:
            score = min(100, max(0, int(numbers[0]))) / 100.0
            return score
        return 0.5  # Fallback
    except Exception as e:
        print(f"Faithfulness calculation failed: {e}")
        return 0.5


def calculate_answer_relevancy(question: str, answer: str) -> float:
    """
    Avalia se a resposta é relevante para a pergunta.
    
    Args:
        question: Pergunta original
        answer: Resposta gerada
        
    Returns:
        Score de 0.0 a 1.0
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
            score = min(100, max(0, int(numbers[0]))) / 100.0
            return score
        return 0.5
    except Exception as e:
        print(f"Answer relevancy calculation failed: {e}")
        return 0.5


def calculate_context_precision(question: str, chunks: list[dict]) -> float:
    """
    Avalia se os chunks recuperados são relevantes para a pergunta.
    
    Usa similaridade entre embeddings.
    
    Args:
        question: Pergunta original
        chunks: Lista de chunks recuperados com 'content'
        
    Returns:
        Score de 0.0 a 1.0
    """
    if not chunks:
        return 0.0
    
    try:
        question_embedding = get_embedding(question)
        
        # Calcular similaridade média com os chunks
        similarities = []
        for chunk in chunks[:5]:  # Top 5 chunks
            if "similarity" in chunk:
                similarities.append(chunk["similarity"])
            else:
                # Calcular manualmente se não tiver
                chunk_embedding = get_embedding(chunk.get("content", "")[:500])
                sim = _cosine_similarity(question_embedding, chunk_embedding)
                similarities.append(sim)
        
        if similarities:
            return sum(similarities) / len(similarities)
        return 0.5
        
    except Exception as e:
        print(f"Context precision calculation failed: {e}")
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
    chunks: list[dict] = None
) -> dict:
    """
    Avalia uma resposta RAG usando múltiplas métricas.
    
    Args:
        question: Pergunta original
        answer: Resposta gerada
        context: Contexto usado
        chunks: Chunks recuperados (opcional, para context_precision)
        
    Returns:
        Dict com scores de cada métrica
    """
    print("Evaluating RAG response with RAGAS-inspired metrics...")
    
    # Calcular métricas
    faithfulness = calculate_faithfulness(answer, context)
    relevancy = calculate_answer_relevancy(question, answer)
    precision = calculate_context_precision(question, chunks) if chunks else None
    
    # Score geral (média ponderada)
    metrics_count = 2 + (1 if precision is not None else 0)
    overall = (faithfulness + relevancy + (precision or 0)) / metrics_count
    
    result = {
        "faithfulness": round(faithfulness, 3),
        "answer_relevancy": round(relevancy, 3),
        "overall_score": round(overall, 3)
    }
    
    if precision is not None:
        result["context_precision"] = round(precision, 3)
    
    print(f"RAGAS Evaluation: {result}")
    
    return result


def get_evaluation_summary(scores: dict) -> str:
    """
    Gera resumo textual da avaliação.
    
    Args:
        scores: Dict com scores das métricas
        
    Returns:
        Descrição textual dos scores
    """
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
