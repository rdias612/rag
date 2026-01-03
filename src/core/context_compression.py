"""
Módulo de compressão de contexto.

Quando o contexto recuperado é muito grande, este módulo resume
os chunks antes de enviá-los ao LLM, mantendo as informações essenciais
e reduzindo custos de tokens.
"""
import time
import re
import logging
from typing import Optional

from src.core.llm import generate_response


rag_logger = logging.getLogger("rag.pipeline")

logger = logging.getLogger("rag.context_compression")


# Template para compressão de contexto
COMPRESSION_PROMPT_TEMPLATE = """Você é um assistente especializado em resumir textos mantendo as informações mais relevantes.

Dado o contexto abaixo e a pergunta do usuário, extraia e resuma APENAS as informações mais relevantes para responder a pergunta.
Mantenha fatos, números, nomes e detalhes técnicos importantes.
Seja conciso mas não perca informações cruciais.

[PERGUNTA DO USUÁRIO]
{pergunta}

[CONTEXTO ORIGINAL]
{contexto}

[INSTRUÇÕES]
- Resuma o contexto mantendo apenas o que é relevante para a pergunta
- Mantenha dados específicos (números, datas, nomes)
- Remova informações redundantes ou irrelevantes
- O resumo deve ter no máximo {max_chars} caracteres

Resumo relevante:"""


def should_compress(context: str, threshold: int) -> bool:
    """
    Verifica se o contexto deve ser comprimido.
    
    Args:
        context: Texto do contexto
        threshold: Limite de caracteres para ativar compressão
        
    Returns:
        True se o contexto excede o threshold
    """
    return len(context) > threshold

def compress_context(
    context: str,
    question: str,
    target_size: int,
    temperature: float = 0.3
) -> dict:
    """
    Comprime o contexto usando o LLM para extrair informações relevantes.
    
    Args:
        context: Contexto original (chunks concatenados)
        question: Pergunta do usuário (para compressão direcionada)
        target_size: Tamanho alvo do contexto comprimido em caracteres
        temperature: Temperatura baixa para resumo mais factual
        
    Returns:
        Dict com contexto comprimido e métricas
    """
    original_size = len(context)
    start_time = time.time()
    
    rag_logger.info("Compressing context: %d chars -> target %d chars", original_size, target_size)
    
    # Montar prompt de compressão
    prompt = COMPRESSION_PROMPT_TEMPLATE.format(
        pergunta=question,
        contexto=context,
        max_chars=target_size
    )
    
    # Gerar resumo com temperatura baixa para ser mais factual
    compressed = generate_response(
        prompt,
        max_tokens=target_size // 3,  # Aproximadamente 3 chars por token
        temperature=temperature
    )
    
    compression_time = time.time() - start_time
    compressed_size = len(compressed)
    compression_ratio = (1 - compressed_size / original_size) * 100
    
    rag_logger.info(
        "Context compressed: %d -> %d chars (%.1f%% reduction) in %.2fs",
        original_size, compressed_size, compression_ratio, compression_time
    )
    
    return {
        "compressed_context": compressed,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "compression_ratio": compression_ratio,
        "compression_time_ms": int(compression_time * 1000)
    }

def smart_compress(
    context: str,
    question: str,
    compression_threshold: int,
    target_ratio: float = 0.5,
    temperature: float = 0.3
) -> dict:
    """
    Comprime o contexto de forma inteligente, apenas se necessário.
    
    Args:
        context: Contexto original
        question: Pergunta do usuário
        compression_threshold: Limite para ativar compressão
        target_ratio: Proporção alvo (0.5 = reduzir pela metade)
        temperature: Temperatura para geração do resumo
        
    Returns:
        Dict com contexto (comprimido ou original) e métricas
    """
    original_size = len(context)
    
    if not should_compress(context, compression_threshold):
        rag_logger.debug("Context size (%d) below threshold (%d), skipping compression",
                      original_size, compression_threshold)
        return {
            "context": context,
            "was_compressed": False,
            "original_size": original_size,
            "final_size": original_size,
            "compression_ratio": 0.0,
            "compression_time_ms": 0
        }
    
    # Calcular tamanho alvo
    target_size = int(original_size * target_ratio)
    
    # Garantir um mínimo razoável
    target_size = max(target_size, 500)
    
    # Comprimir
    result = compress_context(context, question, target_size, temperature)
    
    return {
        "context": result["compressed_context"],
        "was_compressed": True,
        "original_size": result["original_size"],
        "final_size": result["compressed_size"],
        "compression_ratio": result["compression_ratio"],
        "compression_time_ms": result["compression_time_ms"]
    }

def extract_key_sentences(
    context: str,
    question: str,
    max_sentences: int = 10
) -> str:
    """
    Extrai as sentenças mais relevantes do contexto sem usar o LLM.
    
    Método mais rápido e barato, mas menos preciso que a compressão via LLM.
    Usa heurísticas baseadas em sobreposição de palavras com a pergunta.
    
    Args:
        context: Contexto original
        question: Pergunta do usuário
        max_sentences: Número máximo de sentenças a manter
        
    Returns:
        Contexto com apenas as sentenças mais relevantes
    """
    # Dividir em sentenças
    sentences = re.split(r'(?<=[.!?])\s+', context)
    
    if len(sentences) <= max_sentences:
        return context
    
    # Tokenizar pergunta (simples)
    question_words = set(question.lower().split())
    
    # Calcular score de relevância para cada sentença
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        sentence_words = set(sentence.lower().split())
        
        # Score baseado em:
        # 1. Sobreposição de palavras com a pergunta
        overlap = len(question_words & sentence_words)
        
        # 2. Posição (sentenças no início podem ser mais importantes)
        position_score = 1.0 / (1 + i * 0.1)
        
        # 3. Presença de números (geralmente informação factual)
        has_numbers = 1.5 if any(c.isdigit() for c in sentence) else 1.0
        
        score = overlap * position_score * has_numbers
        scored_sentences.append((score, i, sentence))
    
    # Ordenar por score e pegar as top
    scored_sentences.sort(reverse=True)
    top_sentences = scored_sentences[:max_sentences]
    
    # Reordenar pela posição original para manter coerência
    top_sentences.sort(key=lambda x: x[1])
    
    result = ' '.join(s[2] for s in top_sentences)
    
    rag_logger.debug(
        "Key sentence extraction: %d sentences -> %d (%d chars -> %d chars)",
        len(sentences), len(top_sentences), len(context), len(result)
    )
    
    return result
