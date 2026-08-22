"""
Serviço de montagem e compressão de contexto.
"""
from typing import List, Dict, Any
from src.core.context_compression import compress_context
from src.config import (
    ENABLE_CONTEXT_COMPRESSION,
    CONTEXT_COMPRESSION_THRESHOLD,
    CONTEXT_COMPRESSION_METHOD
)
from src.core.logger import get_logger

logger = get_logger("rag.context_service")


class ContextService:
    """Gerencia montagem e otimização de contexto."""
    
    def __init__(self):
        self._compression_enabled = ENABLE_CONTEXT_COMPRESSION
        self._threshold = CONTEXT_COMPRESSION_THRESHOLD
        self._method = CONTEXT_COMPRESSION_METHOD
    
    def build_context(self, documents: List[Dict[str, Any]], max_chars: int = 12000, request_id: str = None) -> str:
        """
        Monta contexto a partir dos documentos.
        """
        request_id = request_id or "unknown"
        logger.debug("Context Building Started | request_id=%s | docs=%d | max_chars=%d",
                     request_id, len(documents), max_chars)
        
        context_parts = []
        current_chars = 0
        
        for i, doc in enumerate(documents, 1):
            source = doc.get("metadata", {}).get("source", "desconhecido")
            content = doc.get("content", "")
            
            part = f"[Documento {i} - Fonte: {source}]\n{content}"
            if current_chars + len(part) > max_chars:
                break
                
            context_parts.append(part)
            current_chars += len(part) + 5
        
        final_context = "\n\n---\n\n".join(context_parts)
        logger.debug("Context Built | request_id=%s | docs_included=%d | chars=%d",
                     request_id, len(context_parts), len(final_context))
        return final_context
    
    def compress_if_needed(
        self, 
        context: str, 
        question: str,
        enable_compression: bool = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Comprime contexto se necessário.
        """
        request_id = request_id or "unknown"
        should_compress = enable_compression if enable_compression is not None else self._compression_enabled
        original_tokens = len(context) // 4
        
        if not should_compress or original_tokens < self._threshold:
            logger.debug("Compression Skipped | request_id=%s | tokens=%d", request_id, original_tokens)
            return {
                "context": context,
                "was_compressed": False,
                "original_tokens": original_tokens,
                "final_tokens": original_tokens,
                "compression_ratio": 1.0
            }
        
        logger.info("Compression Started | request_id=%s | method=%s | tokens=%d",
                    request_id, self._method, original_tokens)
        
        compressed = compress_context(
            context=context,
            question=question,
            method=self._method
        )
        
        final_tokens = len(compressed) // 4
        ratio = final_tokens / original_tokens if original_tokens > 0 else 1.0
        
        logger.info("Compression Complete | request_id=%s | ratio=%.2f", request_id, ratio)
        
        return {
            "context": compressed,
            "was_compressed": True,
            "original_tokens": original_tokens,
            "final_tokens": final_tokens,
            "compression_ratio": ratio
        }
