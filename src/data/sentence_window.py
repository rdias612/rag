"""
Módulo Sentence Window Retrieval.

Indexa sentenças individuais para busca precisa, mas retorna
janela expandida (sentença + vizinhos) para contexto ao LLM.

Benefícios:
- Busca mais precisa (sentenças pequenas)
- Contexto expandido para respostas melhores
- Usa spaCy para melhor detecção de sentenças em português
"""
import logging
import re
from typing import List, Optional, Tuple
import spacy

logger = logging.getLogger(__name__)

# Carregar modelo spaCy para português (mesmo usado no projeto)
try:
    nlp = spacy.load("pt_core_news_md")
    logger.info("spaCy model loaded successfully for Portuguese")
except OSError:
    logger.warning("pt_core_news_md model not found, falling back to en_core_web_sm")
    try:
        nlp = spacy.load("en_core_web_sm")
        logger.info("Using English spaCy model as fallback")
    except OSError:
        logger.error("No spaCy model found. Sentence splitting may be inaccurate.")
        nlp = None


def split_into_sentences(text: str) -> List[str]:
    """
    Divide texto em sentenças usando spaCy.
    
    Usa spaCy para detecção linguística de sentenças em português,
    muito mais precisa que regex simples.
    
    Args:
        text: Texto a dividir
        
    Returns:
        Lista de sentenças
    """
    if not text or not text.strip():
        return []
    
    if nlp is None:
        # Fallback para regex se spaCy não estiver disponível
        logger.warning("spaCy not available, using regex fallback")
        return split_into_sentences_regex(text)
    
    try:
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        logger.debug(f"Split text into {len(sentences)} sentences using spaCy")
        return sentences
    except Exception as e:
        logger.error(f"Error splitting sentences with spaCy: {e}")
        return split_into_sentences_regex(text)


def split_into_sentences_regex(text: str) -> List[str]:
    """
    Fallback: Divide texto em sentenças usando regex.
    
    Args:
        text: Texto a dividir
        
    Returns:
        Lista de sentenças
    """
    # Padrões de fim de sentença
    sentence_endings = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    
    # Dividir
    sentences = sentence_endings.split(text)
    
    # Limpar e filtrar vazios
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Fallback: se não encontrou quebras, dividir por ponto
    if len(sentences) <= 1 and len(text) > 200:
        sentences = [s.strip() + '.' for s in text.split('.') if s.strip()]
    
    return sentences


def create_sentence_index(
    text: str,
    metadata: dict = None
) -> List[dict]:
    """
    Cria índice de sentenças com posições e contexto.
    
    Args:
        text: Texto do documento
        metadata: Metadados base do documento
        
    Returns:
        Lista de dicts com sentença e metadados
    """
    sentences = split_into_sentences(text)
    
    if not sentences:
        return []
    
    index = []
    char_position = 0
    
    for i, sentence in enumerate(sentences):
        # Encontrar posição real no texto
        pos = text.find(sentence, char_position)
        if pos >= 0:
            char_position = pos
        
        entry = {
            "content": sentence,
            "metadata": {
                **(metadata or {}),
                "sentence_index": i,
                "total_sentences": len(sentences),
                "char_start": char_position,
                "char_end": char_position + len(sentence),
                "is_sentence_index": True
            }
        }
        
        index.append(entry)
        char_position += len(sentence)
    
    logger.info(f"Created sentence index with {len(index)} sentences")
    
    return index


def get_sentence_window(
    sentences: List[dict],
    target_index: int,
    window_size: int = 2
) -> Tuple[str, dict]:
    """
    Retorna janela de sentenças ao redor do índice alvo.
    
    Args:
        sentences: Lista de sentenças indexadas
        target_index: Índice da sentença encontrada
        window_size: Número de sentenças antes/depois
        
    Returns:
        Tupla (texto_janela, metadados)
    """
    if not sentences or target_index < 0:
        return "", {}
    
    total = len(sentences)
    
    # Calcular limites da janela
    start_idx = max(0, target_index - window_size)
    end_idx = min(total, target_index + window_size + 1)
    
    # Extrair sentenças da janela
    window_sentences = sentences[start_idx:end_idx]
    
    # Combinar textos
    window_text = " ".join([s.get("content", "") for s in window_sentences])
    
    # Metadados da janela
    window_metadata = {
        "target_sentence_index": target_index,
        "window_start": start_idx,
        "window_end": end_idx - 1,
        "window_size": end_idx - start_idx,
        "is_expanded_window": True
    }
    
    # Copiar metadados do documento original
    if window_sentences:
        base_meta = window_sentences[0].get("metadata", {})
        for key in ["source", "page", "document_id"]:
            if key in base_meta:
                window_metadata[key] = base_meta[key]
    
    return window_text, window_metadata


def expand_sentence_results(
    sentence_results: List[dict],
    all_sentences: List[dict],
    window_size: int = 2,
    deduplicate: bool = True
) -> List[dict]:
    """
    Expande resultados de busca por sentença para janelas.
    
    Args:
        sentence_results: Resultados da busca (sentenças individuais)
        all_sentences: Todas as sentenças do documento
        window_size: Tamanho da janela
        deduplicate: Se True, remove janelas sobrepostas
        
    Returns:
        Lista de janelas expandidas
    """
    if not sentence_results:
        return []
    
    expanded = []
    seen_ranges = set()
    
    for result in sentence_results:
        meta = result.get("metadata", {})
        sentence_idx = meta.get("sentence_index")
        
        if sentence_idx is None:
            # Não é resultado de sentence index, passar adiante
            expanded.append(result)
            continue
        
        # Calcular range da janela
        start = max(0, sentence_idx - window_size)
        end = min(len(all_sentences), sentence_idx + window_size + 1)
        range_key = (start, end)
        
        # Deduplicar janelas sobrepostas
        if deduplicate and range_key in seen_ranges:
            continue
        seen_ranges.add(range_key)
        
        # Criar janela expandida
        window_text, window_meta = get_sentence_window(
            all_sentences, sentence_idx, window_size
        )
        
        if window_text:
            expanded_result = {
                "content": window_text,
                "metadata": {**meta, **window_meta},
                "similarity": result.get("similarity", 0),
                "original_sentence": result.get("content", "")
            }
            expanded.append(expanded_result)
    
    logger.info(f"Expanded {len(sentence_results)} sentences to {len(expanded)} windows")
    
    return expanded


def check_sentence_window_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "version": "1.0",
        "note": "Requires sentence-indexed documents for full functionality"
    }
