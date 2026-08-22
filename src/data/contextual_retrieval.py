"""
Módulo de Contextual Retrieval (Padrão Anthropic).

Enriquece chunks na ingestão gerando um resumo contextual curto (1 a 2 frases)
que situa o chunk dentro do documento global, prevenindo a perda de contexto
semântico e melhorando tanto a busca vetorial (dense) quanto BM25 (sparse).
"""
import time
from typing import List, Dict, Any, Optional

from src.core.llm import generate_response
from src.core.logger import get_logger
from src.config import (
    ENABLE_CONTEXTUAL_RETRIEVAL,
    CONTEXTUAL_RETRIEVAL_MODEL,
    CONTEXTUAL_RETRIEVAL_MAX_DOC_CHARS
)

logger = get_logger("data.contextual_retrieval")

ANTHROPIC_CONTEXTUAL_PROMPT = """<document>
{document_content}
</document>
Abaixo está um trecho (chunk) extraído deste documento que queremos situar no contexto geral:
<chunk>
{chunk_content}
</chunk>
Forneça um contexto curto e sucinto (1 a 2 frases em português) para situar este chunk dentro do documento geral, melhorando a recuperação em buscas.
Responda APENAS com o contexto explicativo. Não repita o texto do chunk e não adicione saudações."""


def generate_chunk_context(
    document_text: str,
    chunk_text: str,
    model: Optional[str] = None,
    max_doc_chars: int = CONTEXTUAL_RETRIEVAL_MAX_DOC_CHARS
) -> str:
    """
    Gera 1-2 frases situando o chunk no documento geral.
    
    Args:
        document_text: Texto completo ou resumo estruturado do documento
        chunk_text: Conteúdo textual do chunk
        model: Modelo LLM a ser utilizado (opcional)
        max_doc_chars: Limite de caracteres do documento enviado no prompt
        
    Returns:
        String com o contexto gerado (ou vazia em caso de falha/fallback)
    """
    if not document_text or not chunk_text or len(chunk_text.strip()) < 10:
        return ""
        
    doc_sample = document_text[:max_doc_chars]
    prompt = ANTHROPIC_CONTEXTUAL_PROMPT.format(
        document_content=doc_sample,
        chunk_content=chunk_text[:1500]
    )
    
    try:
        start_time = time.time()
        context = generate_response(
            prompt=prompt,
            max_tokens=150,
            temperature=0.1
        )
        duration = time.time() - start_time
        
        context_clean = context.strip().replace("\n", " ")
        logger.debug("Contextual summary gerado em %.2fs: %s", duration, context_clean[:80])
        return context_clean
    except Exception as e:
        logger.warning("Falha ao gerar contexto para o chunk: %s", e)
        return ""


def contextualize_chunk(
    document_text: str,
    chunk: Dict[str, Any],
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enriquece um chunk individual com o prefixo contextual.
    
    Salva o texto original nos metadados e prefixa o chunk com o resumo situacional.
    """
    original_text = chunk.get("content", "")
    context_prefix = generate_chunk_context(document_text, original_text, model=model)
    
    chunk_copy = dict(chunk)
    metadata = dict(chunk_copy.get("metadata", {}))
    
    if context_prefix:
        metadata["original_content"] = original_text
        metadata["context_summary"] = context_prefix
        metadata["is_contextualized"] = True
        
        # O novo conteúdo une o contexto ao conteúdo original
        chunk_copy["content"] = f"[Contexto: {context_prefix}]\n{original_text}"
        chunk_copy["metadata"] = metadata
    else:
        metadata["is_contextualized"] = False
        chunk_copy["metadata"] = metadata
        
    return chunk_copy


def contextualize_document_chunks(
    document_text: str,
    chunks: List[Dict[str, Any]],
    enabled: bool = True
) -> List[Dict[str, Any]]:
    """
    Enriquece uma lista de chunks de um mesmo documento.
    
    Args:
        document_text: Texto integral do documento
        chunks: Lista de chunks (filhos/individuais) gerados pelo chunker
        enabled: Se True, executa o enriquecimento
        
    Returns:
        Lista de chunks com metadados e conteúdo contextualizados
    """
    if not enabled or not chunks or not document_text:
        return chunks
        
    logger.info("Iniciando Contextual Retrieval para %d chunks...", len(chunks))
    start_time = time.time()
    
    enriched_chunks = []
    for i, chunk in enumerate(chunks, 1):
        # Apenas contextualizamos chunks que contêm texto e não são metadados pais brutos
        chunk_type = chunk.get("metadata", {}).get("chunk_type")
        if chunk_type == "parent":
            enriched_chunks.append(chunk)
            continue
            
        enriched = contextualize_chunk(document_text, chunk)
        enriched_chunks.append(enriched)
        
    duration = time.time() - start_time
    logger.info("Contextual Retrieval concluído para %d chunks em %.2fs", len(enriched_chunks), duration)
    return enriched_chunks


def check_contextual_retrieval_status() -> Dict[str, Any]:
    """Retorna o status da funcionalidade de Contextual Retrieval."""
    return {
        "enabled": ENABLE_CONTEXTUAL_RETRIEVAL,
        "model": CONTEXTUAL_RETRIEVAL_MODEL or "default",
        "max_doc_chars": CONTEXTUAL_RETRIEVAL_MAX_DOC_CHARS,
        "pattern": "Anthropic Contextual Retrieval (2024)"
    }
