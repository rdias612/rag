"""
Módulo Sentence Window Retrieval.

Indexa sentenças individuais para busca precisa, mas retorna
janela expandida (sentença + vizinhos) para contexto ao LLM.

Benefícios:
- Busca mais precisa (sentenças pequenas)
- Contexto expandido para respostas melhores
- Usa NLP centralizado para detecção de sentenças
"""
from typing import List, Tuple

from src.core.nlp import split_sentences
from src.core.logger import get_logger

logger = get_logger("data.sentence_window")


def split_into_sentences(text: str) -> List[str]:
    """
    Divide texto em sentenças usando o NLPManager centralizado.
    """
    return split_sentences(text, language="pt")


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
    
    logger.debug("Criado índice com %d sentenças", len(index))
    return index


def get_sentence_window(
    sentences: List[dict],
    target_index: int,
    window_size: int = 2
) -> Tuple[str, dict]:
    """
    Retorna janela de sentenças ao redor do índice alvo.
    """
    if not sentences or target_index < 0:
        return "", {}
    
    total = len(sentences)
    start_idx = max(0, target_index - window_size)
    end_idx = min(total, target_index + window_size + 1)
    
    window_sentences = sentences[start_idx:end_idx]
    window_text = " ".join([s.get("content", "") for s in window_sentences])
    
    window_metadata = {
        "target_sentence_index": target_index,
        "window_start": start_idx,
        "window_end": end_idx - 1,
        "window_size": end_idx - start_idx,
        "is_expanded_window": True
    }
    
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
    """
    if not sentence_results:
        return []
    
    expanded = []
    seen_ranges = set()
    
    for result in sentence_results:
        meta = result.get("metadata", {})
        sentence_idx = meta.get("sentence_index")
        
        if sentence_idx is None:
            expanded.append(result)
            continue
        
        start = max(0, sentence_idx - window_size)
        end = min(len(all_sentences), sentence_idx + window_size + 1)
        range_key = (start, end)
        
        if deduplicate and range_key in seen_ranges:
            continue
        seen_ranges.add(range_key)
        
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
    
    logger.debug("Expandidas %d sentenças para %d janelas", len(sentence_results), len(expanded))
    return expanded


def check_sentence_window_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "version": "1.1",
        "note": "Requires sentence-indexed documents for full functionality"
    }
