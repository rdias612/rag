"""
Módulo Self-RAG (Retrieval-Augmented Generation com Reflexão).

Após gerar uma resposta, avalia se ela está completa e correta.
Se necessário, busca mais informações e regenera.
"""

import time
from typing import Optional, Tuple

from src.core.llm import generate_response

# Prompt para avaliar completude da resposta
EVALUATION_PROMPT = """Avalie se a resposta abaixo responde adequadamente à pergunta do usuário.

PERGUNTA:
{question}

CONTEXTO DISPONÍVEL:
{context}

RESPOSTA GERADA:
{answer}

Avalie os seguintes critérios:
1. A resposta usa informações do contexto?
2. A resposta responde diretamente à pergunta?
3. Há informações importantes no contexto que não foram mencionadas?
4. A resposta está completa?

Responda no formato:
SCORE: [0-100]
COMPLETA: [SIM/NAO]
MOTIVO: [breve explicação se incompleta]"""


REFINEMENT_PROMPT = """A resposta anterior foi considerada incompleta.

PERGUNTA ORIGINAL:
{question}

RESPOSTA ANTERIOR:
{previous_answer}

MOTIVO DA INCOMPLETUDE:
{reason}

CONTEXTO ADICIONAL:
{additional_context}

Por favor, gere uma resposta melhorada e mais completa, incorporando as informações adicionais.
Mantenha as informações corretas da resposta anterior e complemente com o novo contexto.

RESPOSTA MELHORADA:"""


def evaluate_response(
    question: str,
    answer: str,
    context: str,
    temperature: float = 0.1
) -> dict:
    """
    Avalia se a resposta está completa e correta.
    
    Args:
        question: Pergunta original
        answer: Resposta gerada
        context: Contexto usado
        temperature: Temperatura para avaliação (baixa para consistência)
        
    Returns:
        Dict com score, is_complete, e reason
    """
    start_time = time.time()
    
    prompt = EVALUATION_PROMPT.format(
        question=question,
        context=context[:3000],  # Limitar contexto
        answer=answer
    )
    
    try:
        response = generate_response(prompt, temperature=temperature, max_tokens=200)
        
        # Parsear resposta
        result = {
            "score": 70,  # Default
            "is_complete": True,
            "reason": "",
            "evaluation_time_ms": 0
        }
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SCORE:'):
                try:
                    score_str = line.replace('SCORE:', '').strip()
                    result["score"] = int(''.join(filter(str.isdigit, score_str[:3])))
                except:
                    pass
            elif line.startswith('COMPLETA:'):
                is_complete = 'SIM' in line.upper()
                result["is_complete"] = is_complete
            elif line.startswith('MOTIVO:'):
                result["reason"] = line.replace('MOTIVO:', '').strip()
        
        result["evaluation_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        print("Self-RAG evaluation: score=%d, complete=%s",
                     result['score'], result['is_complete'])
        
        return result
        
    except Exception as e:
        print("Self-RAG evaluation failed: %s", str(e))
        return {
            "score": 70,
            "is_complete": True,
            "reason": f"Evaluation failed: {e}",
            "evaluation_time_ms": 0
        }


def refine_response(
    question: str,
    previous_answer: str,
    reason: str,
    additional_context: str,
    temperature: float = 0.7
) -> str:
    """
    Refina uma resposta incompleta usando contexto adicional.
    
    Args:
        question: Pergunta original
        previous_answer: Resposta anterior (incompleta)
        reason: Motivo da incompletude
        additional_context: Novo contexto para usar
        temperature: Temperatura para geração
        
    Returns:
        Resposta refinada
    """
    prompt = REFINEMENT_PROMPT.format(
        question=question,
        previous_answer=previous_answer,
        reason=reason,
        additional_context=additional_context[:2000]
    )
    
    try:
        refined = generate_response(prompt, temperature=temperature, max_tokens=1024)
        print("Self-RAG: Response refined with additional context")
        return refined.strip()
        
    except Exception as e:
        print("Self-RAG refinement failed: %s", str(e))
        return previous_answer

def self_rag_pipeline(
    question: str,
    answer: str,
    context: str,
    search_function: callable = None,
    min_score: int = 60,
    max_iterations: int = 1
) -> Tuple[str, dict]:
    """
    Pipeline completo de Self-RAG.
    
    1. Avalia resposta
    2. Se incompleta, busca mais contexto e refina
    
    Args:
        question: Pergunta original
        answer: Resposta inicial
        context: Contexto usado
        search_function: Função para buscar mais contexto (opcional)
        min_score: Score mínimo para considerar completa
        max_iterations: Máximo de refinamentos
        
    Returns:
        Tupla (resposta_final, métricas)
    """
    metrics = {
        "iterations": 0,
        "initial_score": 0,
        "final_score": 0,
        "was_refined": False,
        "total_time_ms": 0
    }
    
    start_time = time.time()
    current_answer = answer
    
    for i in range(max_iterations + 1):
        # Avaliar resposta atual
        evaluation = evaluate_response(question, current_answer, context)
        
        if i == 0:
            metrics["initial_score"] = evaluation["score"]
        
        metrics["iterations"] = i + 1
        metrics["final_score"] = evaluation["score"]
        
        # Se completa ou atingiu limite, retornar
        if evaluation["is_complete"] and evaluation["score"] >= min_score:
            break
        
        if i >= max_iterations:
            break
        
        # Tentar refinar
        if search_function and not evaluation["is_complete"]:
            try:
                # Buscar mais contexto
                additional_results = search_function(question, top_k=3)
                if additional_results:
                    additional_context = "\n\n".join([
                        r.get("content", "") for r in additional_results
                    ])
                    
                    current_answer = refine_response(
                        question=question,
                        previous_answer=current_answer,
                        reason=evaluation.get("reason", "Resposta incompleta"),
                        additional_context=additional_context
                    )
                    metrics["was_refined"] = True
                    
            except Exception as e:
                print("Self-RAG search/refine failed: %s", str(e))
                break
    
    metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return current_answer, metrics

def check_self_rag_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "version": "1.0"
    }
