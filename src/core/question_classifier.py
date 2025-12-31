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
### INSTRUÇÕES DE DEFINIÇÃO:
- Forneça uma definição clara e concisa no primeiro parágrafo.
- Explique o conceito de forma progressiva (do básico ao avançado).
- Use **negrito** para termos técnicos importantes.
- Inclua exemplos práticos extraídos do contexto para ilustrar o conceito.""",
    
    "comparison": """
### INSTRUÇÕES DE COMPARAÇÃO:
- **Obrigatoriamente** apresente uma tabela comparativa ou uma lista contrastante (Lado A vs Lado B).
- Destaque semelhanças E diferenças fundamentais.
- Ao final, forneça uma recomendação de uso para cada opção baseada no contexto.
- Seja objetivo e cite fontes para cada característica comparada.""",
    
    "listing": """
### INSTRUÇÕES DE LISTAGEM:
- Use uma lista numerada ou com bullets para organizar os itens.
- Forneça uma breve descrição (1-2 frases) para cada item listado.
- Agrupe itens por categorias lógicas se a lista for longa (>5 itens).
- Indique claramente se a lista apresentada é exaustiva ou apenas exemplificativa.""",
    
    "procedure": """
### INSTRUÇÕES DE PROCEDIMENTO:
- Apresente os passos em ordem sequencial estritamente numerada.
- Adicione uma seção de **"Pré-requisitos"** antes de iniciar os passos.
- Utilize o formato `Passo X: [Ação]` para cada etapa.
- Se houver alertas no contexto, inclua uma seção **"⚠️ IMPORTANTE"** para avisos de segurança ou erros comuns.""",
    
    "factual": """
### INSTRUÇÕES FACTUAIS:
- Responda de forma direta, sem introduções desnecessárias.
- **Destaque o dado principal** (data, nome, valor) em negrito.
- Cite exatamente a fonte e página de onde a informação foi extraída.
- Se houver ambiguidade no contexto, mencione todas as versões encontradas.""",
    
    "reason": """
### INSTRUÇÕES DE CAUSA/MOTIVO:
- Explique a relação de causa e efeito de forma lógica e encadeada.
- Use conectivos como "devido a", "consequentemente" e "visto que".
- Se houver múltiplos fatores, organize-os por ordem de impacto.
- Conecte a explicação a cenários reais mencionados no contexto.""",
    
    "general": """
### INSTRUÇÕES GERAIS:
- Estruture a resposta com títulos ou tópicos para facilitar a leitura.
- Use exemplos do contexto para validar suas afirmações.
- Se o tema for complexo, adicione um breve "Resumo Executivo" ao final.
- Garanta que todas as afirmações técnicas tenham uma fonte citada."""
}


def get_instructions_for_type(question_type: str) -> str:
    """
    Retorna instruções específicas para o tipo de pergunta.
    Tenta buscar do banco de dados (com exemplos few-shot),
    com fallback para instruções hardcoded.
    
    Args:
        question_type: Tipo da pergunta (definition, comparison, etc.)
        
    Returns:
        Instruções para incluir no prompt
    """
    # 1. Tentar buscar do banco de dados (com exemplos few-shot)
    try:
        from src.data.repositories import _question_type_instruction_repo
        db_instructions = _question_type_instruction_repo.find_by_question_type(question_type)
        
        if db_instructions:
            logger.debug(f"Using DB instructions (few-shot) for type '{question_type}'")
            return db_instructions
    except Exception as e:
        logger.warning(f"Failed to fetch instructions from DB: {e}")
    
    # 2. Fallback para instruções hardcoded
    logger.debug(f"Using fallback instructions for type '{question_type}'")
    return QUESTION_TYPE_INSTRUCTIONS.get(question_type, QUESTION_TYPE_INSTRUCTIONS["general"])


def get_all_question_types() -> list[str]:
    """Retorna lista de todos os tipos de perguntas suportados."""
    return list(QUESTION_PATTERNS.keys()) + ["general"]
