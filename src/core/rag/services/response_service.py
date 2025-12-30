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
            "search": search_metrics,
            "status": "no_results"
        }
    
    def format_response(
        self,
        answer: str,
        documents: list,
        question_type: str,
        was_compressed: bool = False,
        search_metrics: dict = None,
        self_rag_metrics: dict = None,
        duration: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """Formata o retorno padrão da API."""
        result = {
            "answer": answer,
            "sources": documents,
            "question_type": question_type,
            "was_compressed": was_compressed,
            "search": search_metrics or {},
            "duration": duration,
            "status": "success"
        }
        
        # Adicionar métricas de Self-RAG se disponíveis
        if self_rag_metrics:
            result["self_rag"] = self_rag_metrics
        
        # Incluir kwargs adicionais
        result.update(kwargs)
        
        return result
