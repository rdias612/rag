"""
Serviço de construção de respostas e fallbacks.
"""
from typing import Dict, Any, Optional
from src.core.question_classifier import get_question_type_description


class ResponseService:
    """Gerencia formatação de respostas e comportamentos de fallback."""
    
    def build_no_results_response(
        self,
        question: str,
        question_type: str,
        search_metrics: dict
    ) -> Dict[str, Any]:
        """
        Constrói resposta inteligente quando não há documentos relevantes.
        
        Args:
            question: Pergunta original do usuário
            question_type: Tipo da pergunta classificada
            search_metrics: Métricas da busca realizada
            
        Returns:
            Dict com resposta de fallback e metadata
        """
        type_desc = get_question_type_description(question_type)
        
        # Respostas personalizadas por tipo
        if question_type == "greeting":
            answer = "Olá! Como posso ajudar você hoje com as informações da base de conhecimento?"
        elif question_type == "general":
            answer = "Infelizmente não encontrei informações específicas sobre isso nos documentos fornecidos. Você poderia reformular a pergunta ou ser mais específico?"
        elif question_type == "technical":
            answer = f"Apesar de ser uma pergunta técnica ({type_desc}), não localizei dados precisos nos manuais disponíveis para responder com segurança."
        else:
            answer = "Não encontrei informações suficientes nos documentos para responder à sua pergunta."
            
        return {
            "answer": answer,
            "sources": [],
            "question_type": question_type,
            "search_metrics": search_metrics,
            "status": "no_results"
        }
    
    def format_response(
        self,
        answer: str,
        documents: list,
        question_type: str,
        was_compressed: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Formata o retorno padrão da API."""
        return {
            "answer": answer,
            "sources": documents,
            "question_type": question_type,
            "context_compressed": was_compressed,
            "status": "success",
            **kwargs
        }
