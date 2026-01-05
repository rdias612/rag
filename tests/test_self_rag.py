"""
Testes unitários para o módulo Self-RAG.
"""
import pytest
from src.core.self_rag import evaluate_response, refine_response


def test_evaluate_response_complete():
    """Testa avaliação de resposta completa."""
    question = "Qual é a capital do Brasil?"
    answer = "A capital do Brasil é Brasília, fundada em 1960."
    context = "Brasília é a capital federal do Brasil, inaugurada em 21 de abril de 1960."
    
    result = evaluate_response(question, answer, context)
    
    assert "score" in result
    assert "is_complete" in result
    assert "reason" in result
    assert "evaluation_time_ms" in result
    assert 0 <= result["score"] <= 100
    assert isinstance(result["is_complete"], bool)
    assert isinstance(result["reason"], str)


def test_evaluate_response_incomplete():
    """Testa avaliação de resposta incompleta."""
    question = "Quais são os benefícios do uso de RAG?"
    answer = "RAG é útil."
    context = "RAG (Retrieval-Augmented Generation) oferece vários benefícios: 1) Reduz alucinações, 2) Permite acesso a dados atualizados, 3) Melhora a precisão das respostas, 4) Permite citar fontes, 5) Reduz custos de treinamento."
    
    result = evaluate_response(question, answer, context)
    
    assert "score" in result
    # Uma resposta tão breve deve ter score baixo
    assert result["score"] < 80


def test_refine_response():
    """Testa refinamento de resposta."""
    question = "Quem foi o primeiro presidente dos EUA?"
    previous_answer = "George Washington"
    reason = "Falta informação sobre o período de mandato"
    additional_context = "George Washington foi presidente dos Estados Unidos de 1789 a 1797."
    
    refined = refine_response(question, previous_answer, reason, additional_context)
    
    assert isinstance(refined, str)
    assert len(refined) > len(previous_answer)
    # A resposta refinada deve incluir o contexto adicional
    assert "1789" in refined or "1797" in refined or "mandato" in refined.lower()


def test_refine_response_empty_additional():
    """Testa refinamento com contexto adicional vazio."""
    question = "Qual é a capital da França?"
    previous_answer = "Paris"
    reason = "Teste com contexto vazio"
    additional_context = ""
    
    refined = refine_response(question, previous_answer, reason, additional_context)
    
    # Deve retornar a resposta anterior se não houver contexto adicional
    assert refined == previous_answer or len(refined) >= len(previous_answer)


def test_self_rag_pipeline_no_refinement():
    """Testa pipeline Self-RAG sem necessidade de refinamento."""
    from src.core.self_rag import self_rag_pipeline
    
    question = "Qual é a cor do céu em um dia claro?"
    answer = "A cor do céu em um dia claro é azul devido ao espalhamento Rayleigh."
    context = "O céu aparece azul durante o dia devido ao espalhamento Rayleigh da luz solar pela atmosfera."
    
    # Sem função de busca adicional e resposta completa
    result, metrics = self_rag_pipeline(
        question=question,
        answer=answer,
        context=context,
        search_function=None,
        min_score=50,
        max_iterations=0
    )
    
    assert isinstance(result, str)
    assert "iterations" in metrics
    assert "initial_score" in metrics
    assert "final_score" in metrics
    assert metrics["iterations"] == 1


def test_evaluate_response_edge_cases():
    """Testa casos extremos de avaliação."""
    question = "Pergunta de teste"
    
    # Caso 1: Resposta vazia
    result1 = evaluate_response(question, "", "Contexto de teste")
    assert result1["score"] < 30  # Score muito baixo para resposta vazia
    
    # Caso 2: Contexto vazio
    result2 = evaluate_response(question, "Resposta de teste", "")
    assert "is_complete" in result2  # Deve ainda ter campos básicos
    
    # Caso 3: Contexto muito longo (deve ser truncado)
    long_context = "Texto " * 1000  # Contexto muito longo
    result3 = evaluate_response(question, "Resposta", long_context)
    assert result3["score"] >= 0  # Deve processar sem erro
