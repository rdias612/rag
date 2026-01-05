"""
RAG Explainer - Gera explicações detalhadas do processo RAG em formato amigável.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class RAGExplainer:
    """Gera explicação detalhada do processo RAG para o usuário."""
    
    def __init__(self):
        """Inicializa o explicador."""
        pass
    
    def explain_rag_pipeline(
        self,
        question: str,
        debug_info: Dict[str, Any],
        search_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Converte dados técnicos de debug em explicação amigável.
        
        Args:
            question: Pergunta do usuário
            debug_info: Dados do _debug do query_rag
            search_metrics: Dados do search (vector, fts, hybrid)
            
        Returns:
            Dict com timeline formatada para o frontend
        """
        steps = []
        
        # 1. Pergunta original
        steps.append({
            "id": "question",
            "title": "Sua pergunta",
            "description": question,
            "icon": "message-circle",
            "status": "completed"
        })
        
        # 2. HyDE (se aplicado)
        hyde_applied = debug_info.get("hyde_applied", False)
        if hyde_applied:
            hyde_doc = debug_info.get("hyde_document", "")
            hyde_preview = self._truncate_text(hyde_doc, 200)
            
            steps.append({
                "id": "hyde",
                "title": "Geração de documento hipotético (HyDE)",
                "description": (
                    "Geramos um documento ideal para encontrar melhor correspondência "
                    "com sua pergunta no banco de dados."
                ),
                "icon": "sparkles",
                "status": "completed",
                "duration_ms": self._estimate_time("hyde"),
                "metadata": {
                    "hypothetical_document_preview": hyde_preview,
                    "full_document": hyde_doc if hyde_doc else None
                }
            })
        
        # 3. Embedding
        steps.append({
            "id": "embedding",
            "title": "Geração de embedding",
            "description": "Convertendo sua pergunta em representação numérica.",
            "icon": "cpu",
            "status": "completed",
            "duration_ms": debug_info.get("embedding_time_ms"),
            "metadata": {
                "dimension": debug_info.get("embedding_dimension", 768)
            }
        })
        
        # 4. Busca
        search_type = self._get_search_type(search_metrics)
        initial_chunks = debug_info.get("initial_chunks_found", 0)
        search_time = debug_info.get("search_time_ms")
        
        search_metadata = {
            "chunks_found": initial_chunks,
            "search_type": search_type
        }
        
        # Adicionar métricas específicas do tipo de busca
        if search_type == "hybrid":
            vector_metrics = search_metrics.get("vector", {})
            fts_metrics = search_metrics.get("fts", {})
            hybrid_metrics = search_metrics.get("hybrid", {})
            
            search_metadata.update({
                "vector_results": vector_metrics.get("count", 0),
                "fts_results": fts_metrics.get("count", 0),
                "hybrid_alpha": hybrid_metrics.get("alpha", 0.5),
                "avg_similarity": vector_metrics.get("avg_similarity", 0)
            })
        elif search_type == "vector":
            vector_metrics = search_metrics.get("vector", {})
            search_metadata.update({
                "avg_similarity": vector_metrics.get("avg_similarity", 0),
                "max_similarity": vector_metrics.get("max_similarity", 0)
            })
        
        steps.append({
            "id": "search",
            "title": "Busca vetorial" if search_type == "vector" else "Busca híbrida",
            "description": f"Encontrados {initial_chunks} chunks similares",
            "icon": "search",
            "status": "completed",
            "duration_ms": search_time,
            "metadata": search_metadata
        })
        
        # 5. Query Expansion (se aplicado)
        phase2 = search_metrics.get("phase2", {})
        if phase2.get("query_expanded"):
            query_variations = phase2.get("query_variations", 0)
            expansions = phase2.get("expansions", [])
            expansions_preview = self._format_expansions(expansions)
            
            steps.append({
                "id": "query_expansion",
                "title": "Expansão de query",
                "description": (
                    f"Geramos variações da pergunta para encontrar mais documentos "
                    f"({query_variations} variações)."
                ),
                "icon": "branch",
                "status": "completed",
                "metadata": {
                    "query_variations": query_variations,
                    "expansions": expansions_preview
                }
            })
        
        # 6. MMR (se aplicado)
        if phase2.get("mmr_applied"):
            mmr_lambda = phase2.get("mmr_lambda", 0.5)
            steps.append({
                "id": "mmr",
                "title": "Diversificação com MMR",
                "description": (
                    "Selecionamos chunks diversos para evitar repetições "
                    "e cobrir diferentes aspectos."
                ),
                "icon": "layers",
                "status": "completed",
                "metadata": {
                    "mmr_lambda": mmr_lambda,
                    "mmr_k": phase2.get("mmr_k")
                }
            })
        
        # 7. Re-ranking (se aplicado)
        rerank_applied = phase2.get("reranking_applied")
        if rerank_applied:
            rerank_scores = debug_info.get("rerank_scores", [])
            chunks_before_rerank = len(rerank_scores) + debug_info.get("chunks_rejected", 0)
            chunks_after_rerank = debug_info.get("chunks_after_rerank", chunks_before_rerank)
            rerank_time = debug_info.get("rerank_time_ms")
            
            # Formatar top scores
            top_scores = self._format_top_scores(rerank_scores[:5])
            
            steps.append({
                "id": "rerank",
                "title": "Re-ranking com Cross-Encoder",
                "description": (
                    f"Refinamos de {chunks_before_rerank} → {chunks_after_rerank} chunks "
                    "usando modelo mais preciso."
                ),
                "icon": "filter",
                "status": "completed",
                "duration_ms": rerank_time,
                "metadata": {
                    "initial": chunks_before_rerank,
                    "final": chunks_after_rerank,
                    "rejected": chunks_before_rerank - chunks_after_rerank,
                    "top_reranked_scores": top_scores,
                    "all_scores": rerank_scores
                }
            })
        else:
            chunks_after_rerank = initial_chunks
        
        # 8. Compressão (se aplicada)
        compression = debug_info.get("compression", {})
        if compression.get("was_compressed"):
            compression_ratio = compression.get("compression_ratio", 0)
            original_size = compression.get("original_size", 0)
            final_size = compression.get("final_size", 0)
            
            steps.append({
                "id": "compression",
                "title": "Compressão de contexto",
                "description": (
                    f"Contexto reduzido em {compression_ratio:.1f}% "
                    "para otimizar a resposta."
                ),
                "icon": "compress",
                "status": "completed",
                "duration_ms": compression.get("compression_time_ms"),
                "metadata": {
                    "original_size": original_size,
                    "final_size": final_size,
                    "compression_ratio": compression_ratio,
                    "original_tokens": compression.get("original_tokens"),
                    "final_tokens": compression.get("final_tokens")
                }
            })
        
        # 9. Geração de resposta
        llm_time = debug_info.get("llm_time_ms")
        llm_tokens = debug_info.get("llm_tokens")
        
        generation_metadata = {}
        if llm_tokens:
            generation_metadata.update({
                "prompt_tokens": llm_tokens.get("prompt_tokens"),
                "completion_tokens": llm_tokens.get("completion_tokens"),
                "total_tokens": llm_tokens.get("total_tokens")
            })
        
        steps.append({
            "id": "generation",
            "title": "Geração de resposta",
            "description": "Resposta gerada pelo modelo de linguagem.",
            "icon": "bot",
            "status": "completed",
            "duration_ms": llm_time,
            "metadata": generation_metadata if generation_metadata else None
        })
        
        # 10. Self-RAG (se aplicado)
        if debug_info.get("self_rag_applied"):
            steps.append({
                "id": "self_rag",
                "title": "Verificação de qualidade (Self-RAG)",
                "description": (
                    "Verificamos se a resposta é relevante e factualmente correta."
                ),
                "icon": "check-circle",
                "status": "completed",
                "metadata": {
                    "reflection_score": debug_info.get("reflection_score"),
                    "is_relevant": debug_info.get("is_relevant"),
                    "is_factual": debug_info.get("is_factual")
                }
            })
        
        # Resumo final
        total_time = debug_info.get("total_time_ms", 0)
        
        return {
            "question": question,
            "steps": steps,
            "final_result": {
                "chunks_used": chunks_after_rerank,
                "total_chunks_found": initial_chunks,
                "total_time_ms": total_time
            },
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_search_type(self, search_metrics: Dict[str, Any]) -> str:
        """Determina o tipo de busca usado."""
        if "hybrid" in search_metrics:
            return "hybrid"
        elif "fts" in search_metrics:
            return "hybrid"
        else:
            return "vector"
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Trunca texto adicionando reticências se necessário."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _format_expansions(self, expansions: List[str]) -> List[str]:
        """Formata as expansões de query."""
        if not expansions:
            return []
        return [self._truncate_text(exp, 100) for exp in expansions[:5]]
    
    def _format_top_scores(self, scores: List[float]) -> List[Dict[str, Any]]:
        """Formata os top scores do re-ranking."""
        formatted = []
        for i, score in enumerate(scores):
            formatted.append({
                "rank": i + 1,
                "score": score,
                "score_percent": score * 100
            })
        return formatted
    
    def _estimate_time(self, operation: str) -> Optional[int]:
        """Estima tempo de operações não medidas."""
        # Estimativas baseadas em testes anteriores
        estimates = {
            "hyde": 200  # ms
        }
        return estimates.get(operation)


# Instância global do explicador
explainer = RAGExplainer()
