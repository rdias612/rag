"""Repository para gerenciamento de avaliações RAG."""
from typing import List, Dict, Any, Optional

from src.data.repositories.base import BaseRepository
from src.core.logger import db_logger
import time


class EvaluationRepository(BaseRepository):
    """Repository para operações de avaliação."""
    
    def create(self, entity: Dict[str, Any]) -> int:
        """Cria uma avaliação e retorna seu ID."""
        return self.save_evaluation(
            question=entity['question'],
            answer=entity['answer'],
            context=entity['context'],
            scores=entity['scores'],
            session_id=entity.get('session_id'),
            user_id=entity.get('user_id'),
            chunks_retrieved=entity.get('chunks_retrieved'),
            search_mode=entity.get('search_mode'),
            adaptive_used=entity.get('adaptive_used', False)
        )
    
    def find_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Busca avaliação por ID."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM rag_evaluations WHERE id = %s", (id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def save_evaluation(
        self,
        question: str,
        answer: str,
        context: str,
        scores: Dict[str, float],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        chunks_retrieved: Optional[int] = None,
        search_mode: Optional[str] = None,
        adaptive_used: bool = False
    ) -> Optional[int]:
        """
        Salva uma avaliação no banco.
        
        Args:
            question: Pergunta do usuário
            answer: Resposta gerada
            context: Contexto usado
            scores: Dict com scores das métricas
            session_id: ID da sessão (opcional)
            user_id: ID do usuário (opcional)
            chunks_retrieved: Número de chunks recuperados
            search_mode: Modo de busca usado
            adaptive_used: Se adaptive retrieval foi usado
            
        Returns:
            ID do registro inserido
        """
        start_time = time.time()
        
        query = """
            INSERT INTO rag_evaluations (
                question, answer, context, 
                faithfulness, answer_relevancy, context_precision, overall_score,
                evaluation_summary,
                session_id, user_id, chunks_retrieved, search_mode, adaptive_used,
                created_at
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s,
                %s, %s, %s, %s, %s,
                NOW()
            ) RETURNING id
        """
        
        params = (
            question,
            answer,
            context,
            scores.get('faithfulness'),
            scores.get('answer_relevancy'),
            scores.get('context_precision'),
            scores.get('overall_score', 0),
            scores.get('evaluation_summary', ''),
            session_id,
            user_id,
            chunks_retrieved,
            search_mode,
            adaptive_used
        )
        
        try:
            with self._get_cursor() as cur:
                cur.execute(query, params)
                doc_id = cur.fetchone()[0]
            
            duration = time.time() - start_time
            db_logger.debug(f"Evaluation saved in {duration:.2f}s: score={scores.get('overall_score', 0):.2%}")
            return doc_id
        except Exception as e:
            db_logger.error(f"Failed to save evaluation: {e}")
            return None
    
    def get_stats(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Retorna estatísticas agregadas das avaliações.
        
        Args:
            days: Número de dias para filtrar (default: 7)
            
        Returns:
            Dict com estatísticas agregadas
        """
        with self._get_cursor(dict_cursor=True) as cur:
            query = """
                SELECT 
                    COUNT(*) as total_evaluations,
                    AVG(overall_score) as avg_score,
                    AVG(faithfulness) as avg_faithfulness,
                    AVG(answer_relevancy) as avg_relevancy,
                    AVG(context_precision) as avg_precision,
                    MIN(overall_score) as min_score,
                    MAX(overall_score) as max_score,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY overall_score) as median_score
                FROM rag_evaluations
                WHERE created_at >= NOW() - INTERVAL '%s days'
            """
            cur.execute(query, (days,))
            result = cur.fetchone()
            return dict(result) if result else {}
    
    def get_trends(
        self,
        days: int = 30,
        group_by: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Retorna tendência temporal de qualidade.
        
        Args:
            days: Número de dias para analisar
            group_by: Como agrupar ('day', 'week')
            
        Returns:
            Lista de pontos temporais com métricas
        """
        if group_by == 'day':
            date_format = 'YYYY-MM-DD'
            date_trunc = 'DATE(created_at)'
        else:
            date_format = 'YYYY-"W"WW'
            date_trunc = 'EXTRACT(WEEK FROM created_at)'
        
        query = f"""
            SELECT 
                TO_CHAR({date_trunc}, '{date_format}') as period,
                COUNT(*) as evaluations_count,
                AVG(overall_score) as avg_score,
                AVG(faithfulness) as avg_faithfulness,
                AVG(answer_relevancy) as avg_relevancy
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL %s days
            GROUP BY {date_trunc}
            ORDER BY period ASC
        """
        
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute(query, (days,))
            results = cur.fetchall()
            return [dict(row) for row in results]
    
    def get_recent_evaluations(
        self,
        limit: int = 50,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna avaliações recentes.
        
        Args:
            limit: Número máximo de registros
            min_score: Score mínimo para filtrar
            
        Returns:
            Lista de avaliações recentes
        """
        query = """
            SELECT 
                id, question, answer, overall_score,
                faithfulness, answer_relevancy, context_precision,
                evaluation_summary, created_at
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """
        
        params = []
        if min_score is not None:
            query += " AND overall_score >= %s"
            params.append(min_score)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute(query, tuple(params))
            results = cur.fetchall()
            return [dict(row) for row in results]
    
    def get_top_worst_queries(
        self,
        limit: int = 5,
        days: int = 7
    ) -> Dict[str, List[Dict]]:
        """
        Retorna as melhores e piores queries.
        
        Args:
            limit: Número de registros
            days: Período em dias
            
        Returns:
            Dict com 'best' e 'worst' queries
        """
        query = """
            (SELECT 
                'best' as category,
                question, overall_score, created_at
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL %s days
            ORDER BY overall_score DESC
            LIMIT %s)
            
            UNION ALL
            
            (SELECT 
                'worst' as category,
                question, overall_score, created_at
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL %s days
            ORDER BY overall_score ASC
            LIMIT %s)
        """
        
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute(query, (days, limit, days, limit))
            results = cur.fetchall()
            results_list = [dict(row) for row in results]
        
        return {
            'best': [r for r in results_list if r['category'] == 'best'],
            'worst': [r for r in results_list if r['category'] == 'worst']
        }
    
    def delete_old_evaluations(self, days: int = 90) -> int:
        """
        Remove avaliações antigas para economizar espaço.
        
        Args:
            days: Número de dias para manter
            
        Returns:
            Número de registros deletados
        """
        start_time = time.time()
        
        with self._get_cursor() as cur:
            cur.execute("""
                DELETE FROM rag_evaluations
                WHERE created_at < NOW() - INTERVAL %s days
                RETURNING COUNT(*)
            """, (days,))
            result = cur.fetchone()
            count = result[0] if result else 0
        
        duration = time.time() - start_time
        if count > 0:
            db_logger.info(f"Deleted {count} old evaluations (>{days} days) in {duration:.2f}s")
        
        return count
    
    def count(self) -> int:
        """Conta total de avaliações."""
        with self._get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM rag_evaluations")
            return cur.fetchone()[0]


# Instância global
evaluation_repo = EvaluationRepository()
