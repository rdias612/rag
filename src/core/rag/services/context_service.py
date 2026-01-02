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
from src.core.logger import rag_logger, log_step


class ContextService:
    """Gerencia montagem e otimização de contexto."""
    
    def __init__(self):
        self._compression_enabled = ENABLE_CONTEXT_COMPRESSION
        self._threshold = CONTEXT_COMPRESSION_THRESHOLD
        self._method = CONTEXT_COMPRESSION_METHOD
    
    def build_context(self, documents: List[Dict[str, Any]], max_chars: int = 12000, request_id: str = None) -> str:
        """
        Monta contexto a partir dos documentos.
        
        Args:
            documents: Lista de documentos recuperados
            max_chars: Limite de caracteres para o contexto bruto
            request_id: ID da requisição para correlação de logs
            
        Returns:
            Texto formatado do contexto
        """
        request_id = request_id or "unknown"
        
        log_step(rag_logger, "Context Building Started",
                  request_id=request_id,
                  documents_count=len(documents),
                  max_chars=max_chars)
        
        context_parts = []
        current_chars = 0
        
        for i, doc in enumerate(documents, 1):
            source = doc.get("metadata", {}).get("source", "desconhecido")
            content = doc.get("content", "")
            
            part = f"[Documento {i} - Fonte: {source}]\n{content}"
            
            # Verificar limite básico de segurança para não explodir
            if current_chars + len(part) > max_chars:
                break
                
            context_parts.append(part)
            current_chars += len(part) + 5  # +5 para o separador
        
        final_context = "\n\n---\n\n".join(context_parts)
        
        log_step(rag_logger, "Context Built",
                  request_id=request_id,
                  documents_included=len(context_parts),
                  context_chars=len(final_context))
        
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
        
        Args:
            context: Contexto a ser comprimido
            question: Pergunta para orientar a compressão
            enable_compression: Força habilitar/desabilitar compressão
            request_id: ID da requisição para correlação de logs
            
        Returns:
            Dict com context, was_compressed, original_tokens, final_tokens
        """
        request_id = request_id or "unknown"
        
        should_compress = enable_compression if enable_compression is not None else self._compression_enabled
        
        # Estimar tokens (~4 chars por token)
        original_tokens = len(context) // 4
        
        log_step(rag_logger, "Compression Check",
                  request_id=request_id,
                  original_tokens=original_tokens,
                  compression_enabled=should_compress,
                  threshold=self._threshold)
        
        if not should_compress or original_tokens < self._threshold:
            log_step(rag_logger, "Compression Skipped",
                      request_id=request_id,
                      reason="disabled" if not should_compress else "below_threshold")
            
            return {
                "context": context,
                "was_compressed": False,
                "original_tokens": original_tokens,
                "final_tokens": original_tokens,
                "compression_ratio": 1.0
            }
        
        log_step(rag_logger, "Compression Started",
                  request_id=request_id,
                  method=self._method,
                  original_tokens=original_tokens)
        
        compressed = compress_context(
            context=context,
            question=question,
            method=self._method
        )
        
        final_tokens = len(compressed) // 4
        
        log_step(rag_logger, "Compression Complete",
                  request_id=request_id,
                  method=self._method,
                  original_tokens=original_tokens,
                  final_tokens=final_tokens,
                  compression_ratio=f"{(final_tokens/original_tokens if original_tokens > 0 else 1.0):.2f}")
        
        return {
            "context": compressed,
            "was_compressed": True,
            "original_tokens": original_tokens,
            "final_tokens": final_tokens,
            "compression_ratio": final_tokens / original_tokens if original_tokens > 0 else 1.0
        }
