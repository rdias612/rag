"""
Serviço de construção de prompts.
"""
from typing import Optional, Dict, Any
from src.core.prompts import get_active_prompt
from src.data.repositories import PromptRepository
from src.core.question_classifier import get_instructions_for_type
from src.config import (
    RAG_PROMPT_TEMPLATE, 
    RAG_PROMPT_TEMPLATE_WITH_HISTORY,
    USE_ENHANCED_PROMPTS
)


class PromptService:
    """Gerencia construção de prompts dinâmicos."""
    
    def __init__(self):
        self._prompt_repo = PromptRepository()
    
    def build_prompt(
        self,
        context: str,
        question: str,
        question_type: str = None,
        history: str = None,
        response_style: str = "detailed"
    ) -> str:
        """
        Constrói prompt final para o LLM.
        """
        with_history = bool(history)
        
        # 1. Tentar prompt aprimorado (Enhanced)
        prompt_name = "rag_prompt_enhanced_with_history" if with_history else "rag_prompt_enhanced"
        template = get_active_prompt(prompt_name)
        
        if template:
            try:
                return template.format(
                    contexto=context,
                    pergunta=question,
                    historico=history or ""
                )
            except KeyError:
                pass

        # 2. Tentar prompt padrão (Template)
        prompt_name = "rag_prompt_template_with_history" if with_history else "rag_prompt_template"
        template = get_active_prompt(prompt_name)
        
        if template:
            instructions = get_instructions_for_type(question_type) if question_type else ""
            try:
                return template.format(
                    contexto=context,
                    pergunta=question,
                    historico=history or "",
                    instrucoes_tipo=instructions
                )
            except KeyError:
                pass
        
        # 3. Fallback absoluto (hardcoded)
        return self._format_default_prompt(context, question, question_type, history)
    
    def _format_default_prompt(self, context: str, question: str, question_type: str, history: str) -> str:
        """Formata prompt padrão de config."""
        template = RAG_PROMPT_TEMPLATE_WITH_HISTORY if history else RAG_PROMPT_TEMPLATE
        instructions = get_instructions_for_type(question_type) if question_type else ""
        
        return template.format(
            contexto=context,
            pergunta=question,
            historico=history or "",
            instrucoes_tipo=instructions
        )
