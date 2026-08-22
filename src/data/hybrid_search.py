"""
Módulo de Busca Híbrida (Vetorial + BM25/Full-Text Search).

Combina busca semântica (pgvector) com busca por palavras-chave
(PostgreSQL Full-Text Search) para obter resultados mais completos.
"""
import time
from typing import Optional, List, Dict, Any
from psycopg2.extras import RealDictCursor

from src.config import TOP_K_RESULTS, MIN_SIMILARITY_THRESHOLD, HYBRID_SEARCH_ALPHA
from src.data.database import get_connection
from src.core.logger import get_logger

logger = get_logger("data.hybrid_search")


def init_fulltext_search():
    """
    Inicializa as estruturas necessárias para Full-Text Search.
    Adiciona coluna tsvector e índice GIN para busca por texto.
    """
    logger.info("Inicializando estruturas de Full-Text Search no PostgreSQL...")
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'documentos' AND column_name = 'search_vector'
                    ) THEN
                        ALTER TABLE documentos ADD COLUMN search_vector tsvector;
                    END IF;
                END $$;
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_search_vector 
                ON documentos USING gin(search_vector);
            """)
            
            cur.execute("""
                CREATE OR REPLACE FUNCTION documentos_search_vector_trigger() 
                RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('portuguese', COALESCE(NEW.content, ''));
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;
            """)
            
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger 
                        WHERE tgname = 'tsvectorupdate'
                    ) THEN
                        CREATE TRIGGER tsvectorupdate 
                        BEFORE INSERT OR UPDATE ON documentos
                        FOR EACH ROW EXECUTE FUNCTION documentos_search_vector_trigger();
                    END IF;
                END $$;
            """)
            
    duration = time.time() - start_time
    logger.info("Full-Text Search inicializado com sucesso em %.2fs", duration)


def search_fulltext(
    query: str,
    top_k: int = TOP_K_RESULTS,
    collection_id: Optional[str] = None
) -> list[dict]:
    """
    Busca documentos usando Full-Text Search (BM25-like ranking).
    """
    logger.debug("Full-text search: '%s...' (top_k=%d)", query[:50], top_k)
    
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where_conditions = ["search_vector @@ query", "(metadata->>'chunk_type' != 'parent' OR metadata->>'chunk_type' IS NULL)"]
            params = [query]
            
            if collection_id:
                where_conditions.append("collection_id = %s")
                params.append(collection_id)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            params.append(top_k)

            cur.execute(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    collection_id,
                    ts_rank_cd(search_vector, query, 32) as rank
                FROM 
                    documentos,
                    plainto_tsquery('portuguese', %s) query
                {where_clause}
                ORDER BY rank DESC
                LIMIT %s;
            """, tuple(params))
            
            results = cur.fetchall()
            return [dict(r) for r in results]


def search_hybrid(
    query: str,
    query_embedding: list[float],
    top_k: int = TOP_K_RESULTS,
    alpha: float = None,
    min_similarity: float = None,
    collection_id: Optional[str] = None,
    request_id: str = None
) -> list[dict]:
    """
    Executa busca híbrida combinando busca vetorial e full-text.
    """
    start_time = time.time()
    request_id = request_id or "unknown"
    
    if alpha is None:
        alpha = HYBRID_SEARCH_ALPHA
    if min_similarity is None:
        min_similarity = MIN_SIMILARITY_THRESHOLD
    
    logger.debug("Hybrid Search Started | request_id=%s | alpha=%.2f | top_k=%d", request_id, alpha, top_k)
    search_k = top_k * 3
    
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where_conditions_v = ["(metadata->>'chunk_type' != 'parent' OR metadata->>'chunk_type' IS NULL)"]
            params_v = [query_embedding]
            
            if collection_id:
                where_conditions_v.append("collection_id = %s")
                params_v.append(collection_id)
            
            where_clause_v = "WHERE " + " AND ".join(where_conditions_v)
            params_v.extend([query_embedding, search_k])

            cur.execute(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM documentos
                {where_clause_v}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, tuple(params_v))
            vector_results = cur.fetchall()
            
            where_conditions_f = ["search_vector @@ query", "(metadata->>'chunk_type' != 'parent' OR metadata->>'chunk_type' IS NULL)"]
            params_f = [query]
            
            if collection_id:
                where_conditions_f.append("collection_id = %s")
                params_f.append(collection_id)
            
            where_clause_f = "WHERE " + " AND ".join(where_conditions_f)
            params_f.append(search_k)

            cur.execute(f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    ts_rank_cd(search_vector, query, 32) as rank
                FROM 
                    documentos,
                    plainto_tsquery('portuguese', %s) query
                {where_clause_f}
                ORDER BY rank DESC
                LIMIT %s;
            """, tuple(params_f))
            fts_results = cur.fetchall()

    # Combinar resultados usando Reciprocal Rank Fusion (RRF)
    k = 60
    rrf_scores = {}
    doc_data = {}
    
    for rank_idx, doc in enumerate(vector_results):
        doc_id = doc['id']
        rrf_score = alpha * (1.0 / (k + rank_idx + 1))
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + rrf_score
        doc_data[doc_id] = {
            'id': doc['id'],
            'content': doc['content'],
            'metadata': doc['metadata'],
            'vector_similarity': doc['similarity'],
            'fts_rank': 0.0
        }
    
    for rank_idx, doc in enumerate(fts_results):
        doc_id = doc['id']
        rrf_score = (1.0 - alpha) * (1.0 / (k + rank_idx + 1))
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + rrf_score
        
        if doc_id in doc_data:
            doc_data[doc_id]['fts_rank'] = doc['rank']
        else:
            doc_data[doc_id] = {
                'id': doc['id'],
                'content': doc['content'],
                'metadata': doc['metadata'],
                'vector_similarity': 0.0,
                'fts_rank': doc['rank']
            }
    
    final_results = []
    for doc_id, score in rrf_scores.items():
        data = doc_data[doc_id]
        if min_similarity > 0 and data['vector_similarity'] > 0 and data['vector_similarity'] < min_similarity:
            continue
            
        final_results.append({
            'id': data['id'],
            'content': data['content'],
            'metadata': data['metadata'],
            'similarity': data['vector_similarity'],
            'fts_rank': data['fts_rank'],
            'hybrid_score': score
        })
    
    final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    final_results = final_results[:top_k]
    
    duration = time.time() - start_time
    logger.info("Hybrid Search Complete | request_id=%s | vec=%d | fts=%d | final=%d | duration=%.3fs",
                request_id, len(vector_results), len(fts_results), len(final_results), duration)
    return final_results


def check_fulltext_ready() -> bool:
    """Verifica se o Full-Text Search está configurado."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'documentos' AND column_name = 'search_vector'
                    );
                """)
                column_exists = cur.fetchone()[0]
                if not column_exists:
                    return False
                
                cur.execute("SELECT COUNT(*) FROM documentos WHERE search_vector IS NOT NULL;")
                count = cur.fetchone()[0]
                return count > 0
    except Exception:
        return False


def update_existing_documents_fts() -> int:
    """Atualiza o search_vector para todos os documentos existentes."""
    logger.info("Atualizando search_vector para documentos existentes...")
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE documentos 
                SET search_vector = to_tsvector('portuguese', COALESCE(content, ''))
                WHERE search_vector IS NULL;
            """)
            updated = cur.rowcount
            
    duration = time.time() - start_time
    logger.info("Atualizados %d documentos com Full-Text Search em %.2fs", updated, duration)
    return updated
