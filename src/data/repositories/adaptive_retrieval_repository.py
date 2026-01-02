"""
Repository para Adaptive Retrieval Metrics.

Gerencia persistência e consulta de métricas de adaptive retrieval.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
from src.data.repositories.base import BaseRepository
from src.core.logger import logger


class AdaptiveRetrievalRepository(BaseRepository):
    """Repository para métricas de adaptive retrieval."""
    
    def create(self, entity: Any) -> int:
        """Não implementado para este repository."""
        raise NotImplementedError("Use save_metric em seu lugar")

    def find_by_id(self, id: int) -> Optional[Any]:
        """Busca métrica por ID."""
        try:
            with self._get_cursor() as cur:
                cur.execute("SELECT * FROM adaptive_retrieval_metrics WHERE id = %s", (id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error finding adaptive metric by id: {e}")
            raise

    def save_metric(
        self,
        session_id: Optional[str],
        question: str,
        complexity_score: int,
        word_count: int,
        top_k_original: int,
        top_k_adjusted: int,
        min_similarity_original: float,
        min_similarity_adjusted: float,
        adjustment_reason: str,
        characteristics: Dict[str, Any],
        duration_ms: Optional[int] = None
    ) -> int:
        """
        Salva uma métrica de adaptive retrieval.
        
        Args:
            session_id: ID da sessão (opcional)
            question: Pergunta do usuário
            complexity_score: Score de complexidade (0-10)
            word_count: Número de palavras
            top_k_original: Valor original de top_k
            top_k_adjusted: Valor ajustado de top_k
            min_similarity_original: Valor original de min_similarity
            min_similarity_adjusted: Valor ajustado de min_similarity
            adjustment_reason: Razão do ajuste
            characteristics: Características detectadas (JSON)
            duration_ms: Duração da query em ms
            
        Returns:
            ID da métrica salva
        """
        try:
            with self._get_cursor() as cur:
                cur.execute("""
                    INSERT INTO adaptive_retrieval_metrics (
                        session_id, question, complexity_score, word_count,
                        top_k_original, top_k_adjusted,
                        min_similarity_original, min_similarity_adjusted,
                        adjustment_reason, characteristics, duration_ms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    session_id,
                    question,
                    complexity_score,
                    word_count,
                    top_k_original,
                    top_k_adjusted,
                    min_similarity_original,
                    min_similarity_adjusted,
                    adjustment_reason,
                    json.dumps(characteristics),
                    duration_ms
                ))
                result = cur.fetchone()
                metric_id = result[0] if result else None
                logger.info(f"Adaptive metric saved: ID={metric_id}, complexity={complexity_score}")
                return metric_id
        except Exception as e:
            logger.error(f"Error saving adaptive retrieval metric: {e}")
            raise
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtém estatísticas agregadas das métricas.
        
        Args:
            days: Número de dias para considerar
            
        Returns:
            Dict com estatísticas agregadas
        """
        try:
            with self._get_cursor() as cur:
                # Total de queries com adaptive
                cur.execute("""
                    SELECT COUNT(*) as total
                    FROM adaptive_retrieval_metrics
                    WHERE created_at >= NOW() - INTERVAL '1 day' * %s
                """, (days,))
                total = cur.fetchone()[0]
                
                if total == 0:
                    return {
                        "total_queries": 0,
                        "adaptive_applied_pct": 0,
                        "avg_complexity": 0,
                        "avg_top_k": 0,
                        "avg_min_similarity": 0,
                        "complexity_distribution": {
                            "simple": 0,
                            "medium": 0,
                            "complex": 0
                        },
                        "complexity_by_score": {},
                        "days": days
                    }
                
                # Médias
                cur.execute("""
                    SELECT 
                        AVG(complexity_score)::float as avg_complexity,
                        AVG(top_k_adjusted)::float as avg_top_k,
                        AVG(min_similarity_adjusted)::float as avg_min_similarity
                    FROM adaptive_retrieval_metrics
                    WHERE created_at >= NOW() - INTERVAL '1 day' * %s
                """, (days, days))
                row = cur.fetchone()
                avg_complexity = round(row[0], 2) if row[0] else 0
                avg_top_k = round(row[1], 1) if row[1] else 0
                avg_min_similarity = round(row[2], 2) if row[2] else 0
                
                # Distribuição de complexidade
                cur.execute("""
                    SELECT 
                        complexity_score,
                        COUNT(*) as count
                    FROM adaptive_retrieval_metrics
                    WHERE created_at >= NOW() - INTERVAL '1 day' * %s
                    GROUP BY complexity_score
                    ORDER BY complexity_score
                """, (days,))
                complexity_dist = {row[0]: row[1] for row in cur.fetchall()}
                
                # Categorizar (Simple, Medium, Complex)
                simple = sum(v for k, v in complexity_dist.items() if k <= 3)
                medium = sum(v for k, v in complexity_dist.items() if 4 <= k <= 6)
                complex = sum(v for k, v in complexity_dist.items() if k >= 7)
                
                return {
                    "total_queries": total,
                    "adaptive_applied_pct": 100.0,  # Se está na tabela, adaptive foi aplicado
                    "avg_complexity": avg_complexity,
                    "avg_top_k": avg_top_k,
                    "avg_min_similarity": avg_min_similarity,
                    "complexity_distribution": {
                        "simple": simple,
                        "medium": medium,
                        "complex": complex
                    },
                    "complexity_by_score": complexity_dist,
                    "days": days
                }
        except Exception as e:
            logger.error(f"Error getting adaptive retrieval stats: {e}")
            raise
    
    def get_recent_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtém as métricas mais recentes.
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            Lista de métricas
        """
        try:
            with self._get_cursor() as cur:
                cur.execute("""
                    SELECT 
                        id, session_id, question, complexity_score, word_count,
                        top_k_original, top_k_adjusted,
                        min_similarity_original, min_similarity_adjusted,
                        adjustment_reason, characteristics, duration_ms,
                        created_at
                    FROM adaptive_retrieval_metrics
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                
                columns = [
                    'id', 'session_id', 'question', 'complexity_score', 'word_count',
                    'top_k_original', 'top_k_adjusted',
                    'min_similarity_original', 'min_similarity_adjusted',
                    'adjustment_reason', 'characteristics', 'duration_ms',
                    'created_at'
                ]
                
                results = []
                for row in cur.fetchall():
                    result = dict(zip(columns, row))
                    # Converter created_at para string ISO
                    if result['created_at']:
                        result['created_at'] = result['created_at'].isoformat()
                    results.append(result)
                
                return results
        except Exception as e:
            logger.error(f"Error getting recent adaptive metrics: {e}")
            raise
    
    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtém métricas de performance do adaptive retrieval.
        
        Args:
            days: Número de dias para considerar
            
        Returns:
            Dict com métricas de performance
        """
        try:
            with self._get_cursor() as cur:
                # Média de duração
                cur.execute("""
                    SELECT 
                        AVG(duration_ms)::float as avg_duration,
                        MIN(duration_ms)::float as min_duration,
                        MAX(duration_ms)::float as max_duration,
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms)::float as median_duration
                    FROM adaptive_retrieval_metrics
                    WHERE duration_ms IS NOT NULL
                    AND created_at >= NOW() - INTERVAL '1 day' * %s
                """, (days,))
                row = cur.fetchone()
                
                if not row or row[0] is None:
                    return {
                        "avg_duration_ms": 0,
                        "min_duration_ms": 0,
                        "max_duration_ms": 0,
                        "median_duration_ms": 0,
                        "days": days
                    }
                
                return {
                    "avg_duration_ms": round(row[0], 1) if row[0] else 0,
                    "min_duration_ms": round(row[1], 1) if row[1] else 0,
                    "max_duration_ms": round(row[2], 1) if row[2] else 0,
                    "median_duration_ms": round(row[3], 1) if row[3] else 0,
                    "days": days
                }
        except Exception as e:
            logger.error(f"Error getting adaptive retrieval performance metrics: {e}")
            raise

    def cleanup_old_metrics(self, days: int = 30) -> int:
        """
        Remove métricas antigas para economizar espaço.
        
        Args:
            days: Manter apenas registros mais recentes que este número de dias
            
        Returns:
            Número de registros removidos
        """
        try:
            with self._get_cursor() as cur:
                cur.execute("""
                    DELETE FROM adaptive_retrieval_metrics
                    WHERE created_at < NOW() - INTERVAL '1 day' * %s
                    RETURNING id
                """, (days,))
                deleted_ids = [row[0] for row in cur.fetchall()]
                deleted_count = len(deleted_ids)
                logger.info(f"Cleaned up {deleted_count} old adaptive metrics (older than {days} days)")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up adaptive metrics: {e}")
            raise


# Instância global
adaptive_retrieval_repo = AdaptiveRetrievalRepository()
