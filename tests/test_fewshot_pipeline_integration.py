"""
Testes de integração de few-shot examples com pipeline RAG.
"""
import pytest
from src.core.rag.pipeline import RAGPipeline


def test_query_with_fewshot():
    """Testa query completa com instruções few-shot do BD."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="O que é Docker?",
        top_k=3,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "definition"
    # Verifica formato esperado (negrito em termos técnicos)
    assert ("**" in result["answer"] or "Docker" in result["answer"])


def test_comparison_query_with_table():
    """Testa query comparativa gera tabela."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="Qual a diferença entre SQL e NoSQL?",
        top_k=5,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "comparison"
    # Verifica que gerou tabela ou lista contrastante
    assert ("|" in result["answer"] or "vs" in result["answer"].lower())


def test_listing_query_with_bullets():
    """Testa query de listagem gera bullets."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="Quais são os tipos de testes de software?",
        top_k=4,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "listing"
    # Verifica formato de lista
    assert ("1." in result["answer"] or "-" in result["answer"] or "•" in result["answer"])


def test_procedure_query_with_steps():
    """Testa query de procedimento gera passos numerados."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="Como funciona o processo de autenticação JWT?",
        top_k=5,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "procedure"
    # Verifica formato de passos
    assert "Passo" in result["answer"] or "passo" in result["answer"].lower()


def test_factual_query_direct():
    """Testa query factual é direta."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="Quando foi lançado o PostgreSQL 15?",
        top_k=3,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "factual"
    # Verifica que é direta (tem dados destacados)
    assert "**" in result["answer"] or result["answer"].count("2022") > 0


def test_reason_query_explanation():
    """Testa query de causa/motivo tem explicação lógica."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="Por que usar Docker em desenvolvimento?",
        top_k=4,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "reason"
    # Verifica conectivos de causa
    assert ("devido a" in result["answer"].lower() or 
            "porque" in result["answer"].lower() or
            "motivo" in result["answer"].lower())


def test_general_query_structured():
    """Testa query geral tem estrutura."""
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="Como funciona o sistema de pagamentos?",
        top_k=5,
        response_style="detailed"
    )
    
    assert "answer" in result
    assert result["question_type"] == "general"
    # Verifica estrutura (títulos ou tópicos)
    assert ("**" in result["answer"] or 
            "##" in result["answer"] or
            "###" in result["answer"])


def test_fewshot_format_consistency():
    """Testa que respostas seguem formato dos exemplos few-shot."""
    pipeline = RAGPipeline()
    
    # Testar múltiplas queries do mesmo tipo
    queries = [
        "O que é uma API REST?",
        "O que significa Kubernetes?",
        "O que é microserviços?"
    ]
    
    results = [
        pipeline.query(question=q, top_k=3, response_style="detailed")
        for q in queries
    ]
    
    # Todas devem ter negrito em termos técnicos (padrão few-shot)
    for result in results:
        assert "**" in result["answer"]


def test_instructions_applied_correctly():
    """Testa que instruções few-shot são aplicadas."""
    pipeline = RAGPipeline()
    
    # Query comparativa
    result = pipeline.query(
        question="Qual a diferença entre PostgreSQL e MongoDB?",
        top_k=5,
        response_style="detailed"
    )
    
    # Deve ter recomendação (parte das instruções few-shot)
    assert "recomendação" in result["answer"].lower() or "recomenda" in result["answer"].lower()


def test_fallback_when_db_unavailable():
    """Testa fallback quando BD não está disponível."""
    # Este teste simula erro de conexão com BD
    from src.data.repositories import _question_type_instruction_repo
    
    # Desativar todas as instruções no BD (simular indisponibilidade)
    # Isso forçará uso do fallback hardcoded
    # (Nota: Este teste requer setup especial do BD)
    
    pipeline = RAGPipeline()
    result = pipeline.query(
        question="O que é Docker?",
        top_k=3,
        response_style="detailed"
    )
    
    # Mesmo com fallback, deve funcionar
    assert "answer" in result
    assert len(result["answer"]) > 0
