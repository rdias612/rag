"""
Testes de integração para question_classifier com banco de dados.
"""
import pytest
from src.core.question_classifier import classify_question, get_instructions_for_type


def test_get_instructions_from_db():
    """Testa que instruções são buscadas do BD."""
    question = "O que é uma API?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    # Verifica que veio do BD (contém exemplos few-shot)
    assert "EXEMPLOS DE COMO RESPONDER" in instructions
    assert "Exemplo 1:" in instructions
    assert "Exemplo 2:" in instructions


def test_get_instructions_fallback():
    """Testa fallback para instruções hardcoded."""
    # Tipo que não existe no BD
    instructions = get_instructions_for_type("nonexistent_type")
    
    # Deve retornar instruções general
    assert "INSTRUÇÕES GERAIS" in instructions


def test_classification_integration():
    """Testa integração completa."""
    question = "O que é Docker?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "definition"
    assert instructions  # Não está vazio
    assert "definição" in instructions.lower()


def test_comparison_instructions():
    """Testa instruções para perguntas comparativas."""
    question = "Qual a diferença entre SQL e NoSQL?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "comparison"
    assert "tabela comparativa" in instructions.lower()
    assert "lista contrastante" in instructions.lower()


def test_listing_instructions():
    """Testa instruções para perguntas de listagem."""
    question = "Quais são os tipos de testes?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "listing"
    assert "lista numerada" in instructions.lower() or "bullets" in instructions.lower()


def test_procedure_instructions():
    """Testa instruções para perguntas de procedimento."""
    question = "Como funciona o processo de autenticação?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "procedure"
    assert "passos" in instructions.lower()
    assert "pré-requisitos" in instructions.lower()


def test_factual_instructions():
    """Testa instruções para perguntas factuais."""
    question = "Quando foi lançado o PostgreSQL 15?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "factual"
    assert "direta" in instructions.lower()
    assert "fonte" in instructions.lower()


def test_reason_instructions():
    """Testa instruções para perguntas de causa/motivo."""
    question = "Por que usar Docker em desenvolvimento?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "reason"
    assert "causa" in instructions.lower() or "motivo" in instructions.lower()
    assert "conectivos" in instructions.lower()


def test_general_instructions():
    """Testa instruções para perguntas gerais."""
    question = "Como funciona o sistema de pagamentos?"
    question_type = classify_question(question)
    instructions = get_instructions_for_type(question_type)
    
    assert question_type == "general"
    assert "títulos" in instructions.lower() or "tópicos" in instructions.lower()
