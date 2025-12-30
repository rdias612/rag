"""
Utilitário para recuperação de prompts.
Tenta buscar no banco de dados, com fallback para as constantes no código.
"""
from typing import Optional
from src.data.repositories import PromptRepository
from src import config

# Instância do repository
_prompt_repo = PromptRepository()


def get_active_prompt(name: str) -> str:
    """
    Retorna o template de um prompt.
    Tenta primeiro o banco de dados. Se falhar ou estiver vazio, usa a constante do config.
    
    Args:
        name: Nome do prompt (ex: 'rag_prompt_enhanced')
        
    Returns:
        Template do prompt
    """
    # 1. Tentar Banco de Dados
    db_prompt = _prompt_repo.find_by_name(name)
    if db_prompt:
        return db_prompt
    
    # 2. Fallback para Constantes em src.config
    # Mapeamento de nomes de DB para nomes de constantes no config
    fallback_map = {
        'rag_prompt_enhanced': config.RAG_PROMPT_ENHANCED,
        'rag_prompt_enhanced_with_history': config.RAG_PROMPT_ENHANCED_WITH_HISTORY,
        'rag_prompt_template': config.RAG_PROMPT_TEMPLATE,
        'rag_prompt_template_with_history': config.RAG_PROMPT_TEMPLATE_WITH_HISTORY,
        'hyde_prompt': getattr(config, 'HYDE_PROMPT', ''),
        'hyde_prompt_concise': getattr(config, 'HYDE_PROMPT_CONCISE', ''),
        'query_expansion_prompt': getattr(config, 'QUERY_EXPANSION_PROMPT', ''),
    }
    
    # Se for uma instrução de tipo de pergunta, buscar no question_classifier (será refatorado)
    if name.startswith('instruction_'):
        from src.core.question_classifier import QUESTION_TYPE_INSTRUCTIONS
        type_key = name.replace('instruction_', '')
        return QUESTION_TYPE_INSTRUCTIONS.get(type_key, QUESTION_TYPE_INSTRUCTIONS.get('general', ''))

    return fallback_map.get(name, "")

