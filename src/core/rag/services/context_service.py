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


class ContextService:
    """Gerencia montagem e otimização de contexto."""
    
    def __init__(self):
        self._compression_enabled = ENABLE_CONTEXT_COMPRESSION
        self._threshold = CONTEXT_COMPRESSION_THRESHOLD
        self._method = CONTEXT_COMPRESSION_METHOD
    
    def build_context(self, documents: List[Dict[str, Any]], max_chars: int = 12000) -> str:
        """
        Monta contexto a partir dos documentos.
        
        Args:
            documents: Lista de documentos recuperados
            max_chars: Limite de caracteres para o contexto bruto
            
        Returns:
            Texto formatado do contexto
        """
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
        
        return "\n\n---\n\n".join(context_parts)
    
    def compress_if_needed(
        self, 
        context: str, 
        question: str,
        enable_compression: bool = None
    ) -> Dict[str, Any]:
        """
        Comprime contexto se necessário.
        
        Returns:
            Dict com context, was_compressed, original_tokens, final_tokens
        """
        should_compress = enable_compression if enable_compression is not None else self._compression_enabled
        
        # Estimar tokens (~4 chars por token)
        original_tokens = len(context) // 4
        
        if not should_compress or original_tokens < self._threshold:
            return {
                "context": context,
                "was_compressed": False,
                "original_tokens": original_tokens,
                "final_tokens": original_tokens,
                "compression_ratio": 1.0
            }
        
        compressed = compress_context(
            context=context,
            question=question,
            method=self._method
        )
        
        final_tokens = len(compressed) // 4
        
        return {
            "context": compressed,
            "was_compressed": True,
            "original_tokens": original_tokens,
            "final_tokens": final_tokens,
            "compression_ratio": final_tokens / original_tokens if original_tokens > 0 else 1.0
        }
