"""
PromptManager - Sistema centralizado de gestão e seleção de prompts.

Suporta dois modos:
- 'category': Busca rápida por categoria + priority (Mode 1)
- 'llm_router': LLM escolhe entre múltiplos prompts (Mode 2)
"""
import logging
from typing import Optional
from src.data.database import get_prompts_by_category, get_prompt
from src.core.llm import generate_response
from src import config

logger = logging.getLogger(__name__)


class PromptManager:
    """Gerenciador centralizado de prompts com seleção inteligente."""
    
    def __init__(self):
        # Mapeamento de fallback (compatibilidade retroativa)
        self.fallback_map = {
            'rag_main': 'rag_prompt_enhanced',
            'rag_main_with_history': 'rag_prompt_enhanced_with_history',
            'hyde': 'hyde_prompt',
            'hyde_concise': 'hyde_prompt_concise',
            'query_expansion': 'query_expansion_prompt'
        }
    
    def get_prompt_for_category(
        self,
        category: str,
        mode: str = 'category',
        context: dict = None
    ) -> str:
        """
        Busca o melhor prompt para uma categoria.
        
        Args:
            category: Categoria do prompt ('rag_main', 'hyde', etc.)
            mode: 'category' (rápido) ou 'llm_router' (inteligente)
            context: {'user_query': str, 'question_type': str}
            
        Returns:
            Template do prompt
        """
        logger.debug(f"Getting prompt for category='{category}', mode='{mode}'")
        
        # 1️⃣ Buscar prompts da categoria
        prompts = get_prompts_by_category(category)
        
        if not prompts:
            logger.warning(f"No prompts found for category '{category}', using fallback")
            return self._get_fallback(category)
        
        # 2️⃣ Filtrar por tags (se context especificar question_type)
        if context and 'question_type' in context:
            question_type = context['question_type']
            filtered = [p for p in prompts if question_type in (p.get('tags') or [])]
            
            if filtered:
                prompts = filtered
                logger.debug(f"Filtered to {len(prompts)} prompts with tag '{question_type}'")
        
        # 3️⃣ Seleção baseada no modo
        if len(prompts) == 1:
            # Apenas 1 opção, retornar imediatamente
            return prompts[0]['template']
        
        if mode == 'llm_router' and len(prompts) > 1 and context and 'user_query' in context:
            # Usar LLM para escolher
            return self._llm_select(context['user_query'], prompts)
        else:
            # Modo categoria: pegar de maior priority (já vem ordenado do banco)
            return prompts[0]['template']
    
    def _llm_select(self, user_query: str, candidates: list[dict]) -> str:
        """
LLM escolhe o melhor prompt entre múltiplos candidatos."""
        logger.info(f"LLM Router selecting from {len(candidates)} prompts")
        
        # Formatar opções
        options_text = []
        for i, prompt in enumerate(candidates):
            tags = ', '.join(prompt.get('tags') or [])
            use_case = prompt.get('use_case', 'N/A')
            options_text.append(
                f"{i+1}. {prompt['name']}\n"
                f"   Priority: {prompt['priority']}\n"
                f"   Tags: {tags}\n"
                f"   Use case: {use_case}\n"
            )
        
        # Prompt de seleção
        selection_prompt = f"""Você é um roteador de prompts especializado.

PERGUNTA DO USUÁRIO:
"{user_query}"

PROMPTS DISPONÍVEIS:
{chr(10).join(options_text)}

Analise a pergunta e escolha o prompt mais adequado.
Responda APENAS com o número da opção (1, 2, 3, etc). Não adicione mais nada.
"""
        
        try:
            # LLM escolhe (temperatura baixa para consistência)
            response = generate_response(selection_prompt, temperature=0.1, max_tokens=5)
            choice_num = int(response.strip().split()[0]) - 1  # Pegar primeiro número
            
            if 0 <= choice_num < len(candidates):
                selected = candidates[choice_num]
                logger.info(f"LLM selected prompt: {selected['name']}")
                return selected['template']
            else:
                logger.warning(f"LLM returned invalid choice: {response}. Using fallback.")
                return candidates[0]['template']
                
        except Exception as e:
            logger.error(f"LLM Router failed: {e}. Using fallback (highest priority).")
            return candidates[0]['template']
    
    def _get_fallback(self, category: str) -> str:
        """Busca fallback hardcoded se banco falhar."""
        # Tentar buscar pelo nome fixo
        if category in self.fallback_map:
            fallback_name = self.fallback_map[category]
            prompt = get_prompt(fallback_name)
            if prompt:
                return prompt
        
        # Último recurso: constantes hardcoded
        if category == 'rag_main':
            return config.RAG_PROMPT_ENHANCED
        elif category == 'rag_main_with_history':
            return config.RAG_PROMPT_ENHANCED_WITH_HISTORY
        elif category == 'hyde':
            return getattr(config, 'HYDE_PROMPT', '')
        elif category == 'hyde_concise':
            return getattr(config, 'HYDE_PROMPT_CONCISE', '')
        elif category == 'query_expansion':
            return getattr(config, 'QUERY_EXPANSION_PROMPT', '')
        
        logger.error(f"No fallback found for category '{category}'")
        return ""
    
    def get_instruction_prompt(self, question_type: str) -> str:
        """
        Busca instruções específicas para um tipo de pergunta.
        
        Args:
            question_type: 'definition', 'comparison', 'listing', etc.
            
        Returns:
            Instruções formatadas ou string vazia
        """
        prompt_name = f"instruction_{question_type}"
        prompt = get_prompt(prompt_name)
        
        if prompt:
            return prompt
        
        # Fallback para question_classifier
        from src.core.question_classifier import get_instructions_for_type
        return get_instructions_for_type(question_type)


# Instância global
prompt_manager = PromptManager()
