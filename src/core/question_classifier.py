"""
Módulo de classificação de tipos de perguntas.

Classifica perguntas em categorias para selecionar prompts especializados
e otimizar a qualidade das respostas.
"""
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Tipos de perguntas e seus padrões
QUESTION_PATTERNS = {
    "definition": [
        r"\bo que [ée]\b",
        r"\bo que significa\b",
        r"\bdefin[aei]\b",
        r"\bexplique o que\b",
        r"\bconceito de\b",
        r"\bsignificado de\b",
    ],
    "comparison": [
        r"\bdiferen[çc]a entre\b",
        r"\bcompare\b",
        r"\bcompara[çc][ãa]o\b",
        r"\bversus\b",
        r"\bvs\.?\b",
        r"\bmelhor.+ou\b",
        r"\bqual a diferen[çc]a\b",
    ],
    "listing": [
        r"\bquais s[ãa]o\b",
        r"\bliste\b",
        r"\benumere\b",
        r"\bcite\b",
        r"\bexemplos de\b",
        r"\btipos de\b",
        r"\bprincipais\b",
    ],
    "procedure": [
        r"\bcomo fazer\b",
        r"\bcomo funciona\b",
        r"\bcomo [ée] feito\b",
        r"\bpassos para\b",
        r"\bprocedimento\b",
        r"\bpasso a passo\b",
        r"\bcomo implement\b",
        r"\bcomo configur\b",
    ],
    "factual": [
        r"\bquando\b",
        r"\bonde\b",
        r"\bquem\b",
        r"\bquanto[s]?\b",
        r"\bqual [ée]\b",
        r"\bem que ano\b",
    ],
    "reason": [
        r"\bpor que\b",
        r"\bporque\b",
        r"\bqual [oa] motivo\b",
        r"\bqual a raz[ãa]o\b",
        r"\bpor qual raz[ãa]o\b",
    ]
}


def classify_question(question: str) -> str:
    """
    Classifica uma pergunta em uma categoria.
    
    Args:
        question: Pergunta do usuário
        
    Returns:
        Tipo da pergunta: "definition", "comparison", "listing", 
        "procedure", "factual", "reason", ou "general"
    """
    question_lower = question.lower().strip()
    
    # Verificar cada tipo de pergunta
    for question_type, patterns in QUESTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, question_lower):
                logger.debug(f"Question classified as '{question_type}': {question[:50]}...")
                return question_type
    
    logger.debug(f"Question classified as 'general': {question[:50]}...")
    return "general"


def get_question_type_description(question_type: str) -> str:
    """
    Retorna descrição do tipo de pergunta.
    
    Args:
        question_type: Tipo da pergunta
        
    Returns:
        Descrição em português
    """
    descriptions = {
        "definition": "Pergunta de definição/explicação",
        "comparison": "Pergunta comparativa",
        "listing": "Pergunta de listagem/enumeração",
        "procedure": "Pergunta de procedimento/processo",
        "factual": "Pergunta factual",
        "reason": "Pergunta de causa/motivo",
        "general": "Pergunta geral"
    }
    return descriptions.get(question_type, "Pergunta geral")


# Mapeamento de tipos para instruções específicas no prompt
QUESTION_TYPE_INSTRUCTIONS = {
    "definition": """
- Forneça uma definição clara e concisa
- Explique o conceito de forma progressiva (do básico ao avançado)
- Inclua exemplos práticos quando possível
- Mencione contexto de uso se relevante""",
    
    "comparison": """
- Organize a comparação em formato estruturado (tabela ou tópicos)
- Destaque semelhanças E diferenças
- Se possível, indique quando usar cada opção
- Seja objetivo e imparcial na comparação""",
    
    "listing": """
- Apresente os itens em lista numerada ou com bullets
- Forneça breve descrição de cada item
- Organize por relevância ou categoria lógica
- Indique se a lista é exaustiva ou exemplificativa""",
    
    "procedure": """
- Apresente os passos em ordem sequencial numerada
- Seja específico em cada etapa
- Mencione pré-requisitos se houver
- Alerte sobre possíveis erros ou armadilhas""",
    
    "factual": """
- Responda de forma direta e objetiva
- Cite a fonte específica do contexto quando possível
- Se houver múltiplas respostas possíveis, liste-as
- Indique incerteza se a informação não for clara""",
    
    "reason": """
- Explique a causa ou motivo de forma clara
- Forneça contexto que ajude a entender o "porquê"
- Se houver múltiplas causas, organize por relevância
- Conecte causa e efeito de forma lógica""",
    
    "general": """
- Responda de forma clara e organizada
- Use exemplos do contexto quando apropriado
- Estruture a resposta em tópicos se for complexa
- Seja conciso mas completo"""
}


def get_instructions_for_type(question_type: str) -> str:
    """
    Retorna instruções específicas para o tipo de pergunta.
    
    Args:
        question_type: Tipo da pergunta
        
    Returns:
        Instruções para incluir no prompt
    """
    return QUESTION_TYPE_INSTRUCTIONS.get(question_type, QUESTION_TYPE_INSTRUCTIONS["general"])


def get_all_question_types() -> list[str]:
    """Retorna lista de todos os tipos de perguntas suportados."""
    return list(QUESTION_PATTERNS.keys()) + ["general"]
