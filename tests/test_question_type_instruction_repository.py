"""
Testes unitários para QuestionTypeInstructionRepository.
"""
import pytest
from src.data.repositories import QuestionTypeInstructionRepository, _question_type_instruction_repo


def test_create_instruction():
    """Testa criação de nova instrução."""
    success, instruction_id, error = _question_type_instruction_repo.create(
        question_type="test_type",
        template="Test template with examples",
        description="Test description"
    )
    
    assert success is True
    assert instruction_id > 0
    assert error == ""


def test_find_instruction():
    """Testa busca de instrução."""
    template = _question_type_instruction_repo.find_by_question_type("definition")
    
    assert template is not None
    assert "INSTRUÇÕES DE DEFINIÇÃO" in template
    assert "EXEMPLOS DE COMO RESPONDER" in template


def test_cache_functionality():
    """Testa cache em memória."""
    # Primeira busca (do BD)
    template1 = _question_type_instruction_repo.find_by_question_type("definition", use_cache=False)
    
    # Segunda busca (do cache)
    template2 = _question_type_instruction_repo.find_by_question_type("definition", use_cache=True)
    
    assert template1 == template2


def test_update_instruction():
    """Testa atualização de instrução."""
    success, error = _question_type_instruction_repo.update(
        question_type="test_type",
        template="Updated template",
        is_active=False
    )
    
    assert success is True
    assert error == ""


def test_list_all_instructions():
    """Testa listagem de todas as instruções."""
    instructions = _question_type_instruction_repo.list_all()
    
    assert len(instructions) > 0
    assert all("question_type" in instr for instr in instructions)
    assert all("template" in instr for instr in instructions)
    assert all("version" in instr for instr in instructions)
