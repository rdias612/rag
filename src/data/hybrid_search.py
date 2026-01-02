"""
Módulo de Busca Híbrida (Vetorial + BM25/Full-Text Search).

Combina busca semântica (pgvector) com busca por palavras-chave
(PostgreSQL Full-Text Search) para obter resultados mais completos.
"""
import time
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import (
    DATABASE_CONFIG, 
    TOP_K_RESULTS, 
    MIN_SIMILARITY_THRESHOLD,
    HYBRID_SEARCH_ALPHA
)
from src.core.logger import db_logger, log_stage, log_step, log_error


def get_connection():
    """Cria conexão com o banco de dados."""
    return psycopg2.connect(**DATABASE_CONFIG)


def init_fulltext_search():
    """
    Inicializa as estruturas necessárias para Full-Text Search.
    Adiciona coluna tsvector e índice GIN para busca por texto.
    """
    db_logger.info("Initializing Full-Text Search structures...")
    start_time = time.time()
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Adicionar coluna para vetor de texto (se não existir)
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
            
            # Criar índice GIN para Full-Text Search (se não existir)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_fts 
                ON documentos 
                USING gin(search_vector);
            """)
            
            # Atualizar search_vector para documentos existentes
            cur.execute("""
                UPDATE documentos 
                SET search_vector = to_tsvector('portuguese', content)
                WHERE search_vector IS NULL;
            """)
            
            # Criar trigger para atualizar automaticamente o search_vector
            cur.execute("""
                CREATE OR REPLACE FUNCTION update_search_vector()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('portuguese', NEW.content);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # Criar trigger se não existir
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_update_search_vector'
                    ) THEN
                        CREATE TRIGGER trg_update_search_vector
                        BEFORE INSERT OR UPDATE ON documentos
                        FOR EACH ROW
                        EXECUTE FUNCTION update_search_vector();
                    END IF;
                END $$;
            """)
            
            conn.commit()
            
        duration = time.time() - start_time
        db_logger.info(f"Full-Text Search initialized in {duration:.2f}s")
        db_logger.info("Full-Text Search inicializado com sucesso!")
        
    except Exception as e:
        conn.rollback()
        db_logger.error(f"Error initializing Full-Text Search: {e}")
        raise
    finally:
        conn.close()


def search_fulltext(
    query: str,
    top_k: int = TOP_K_RESULTS,
    collection_id: Optional[str] = None
) -> list[dict]:
    """
    Busca documentos usando Full-Text Search (BM25-like ranking).
    
    Args:
        query: Texto da busca
        top_k: Número de resultados
        
    Returns:
        Lista de documentos com content, metadata e rank
    """
    start_time = time.time()
    db_logger.debug(f"Full-text search: '{query[:50]}...' (top_k={top_k})")
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Construir query com filtro de coleção facultativo e chunk_type
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
                    ts_rank_cd(search_vector, query, 32) as rank
                FROM 
                    documentos,
                    plainto_tsquery('portuguese', %s) query
                {where_clause}
                ORDER BY rank DESC
                LIMIT %s;
            """, tuple(params))
            
            results = cur.fetchall()
            
    finally:
        conn.close()
    
    duration = time.time() - start_time
    results_list = [dict(row) for row in results]
    
    db_logger.debug(f"Full-text search returned {len(results_list)} results in {duration:.3f}s")
    
    return results_list


def search_hybrid(
    query: str,
    query_embedding: list[float],
    top_k: int = TOP_K_RESULTS,
    alpha: float = None,
    min_similarity: Optional[float] = None,
    collection_id: Optional[str] = None,
    request_id: str = None
) -> list[dict]:
    """
    Busca híbrida combinando busca vetorial e Full-Text Search.
    
    Usa Reciprocal Rank Fusion (RRF) para combinar os rankings.
    
    Args:
        query: Texto da pergunta (para FTS)
        query_embedding: Embedding da pergunta (para busca vetorial)
        top_k: Número final de resultados
        alpha: Peso da busca vetorial (0.0 a 1.0). 
               1.0 = só vetorial, 0.0 = só FTS
               None = usa config HYBRID_SEARCH_ALPHA
        min_similarity: Similaridade mínima para busca vetorial
        
    Returns:
        Lista de documentos ranqueados com score híbrido
    """
    start_time = time.time()
    request_id = request_id or "unknown"
    
    if alpha is None:
        alpha = HYBRID_SEARCH_ALPHA
    
    if min_similarity is None:
        min_similarity = MIN_SIMILARITY_THRESHOLD
    
    log_step(db_logger, "Hybrid Search Started",
              request_id=request_id,
              alpha=alpha,
              top_k=top_k,
              collection_id=collection_id)
    
    # Buscar mais resultados inicialmente para ter margem de fusão
    search_k = top_k * 3
    
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Busca Vetorial
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
            
            log_step(db_logger, "Vector Search Results",
                      request_id=request_id,
                      results=len(vector_results))
            
            # 2. Busca Full-Text
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
            
            log_step(db_logger, "FTS Search Results",
                      request_id=request_id,
                      results=len(fts_results))
            
    finally:
        conn.close()
    
    # 3. Combinar resultados usando Reciprocal Rank Fusion (RRF)
    # RRF Score = 1 / (k + rank), onde k é uma constante (geralmente 60)
    k = 60
    
    # Criar mapa de scores
    doc_scores = {}
    doc_data = {}
    
    # Processar resultados vetoriais
    for rank, doc in enumerate(vector_results):
        doc_id = doc['id']
        rrf_score = alpha * (1 / (k + rank + 1))
        
        if doc_id not in doc_scores:
            doc_scores[doc_id] = {'vector': 0, 'fts': 0}
            doc_data[doc_id] = {
                'id': doc_id,
                'content': doc['content'],
                'metadata': doc['metadata'],
                'similarity': doc['similarity']
            }
        
        doc_scores[doc_id]['vector'] = rrf_score
    
    # Processar resultados FTS
    for rank, doc in enumerate(fts_results):
        doc_id = doc['id']
        rrf_score = (1 - alpha) * (1 / (k + rank + 1))
        
        if doc_id not in doc_scores:
            doc_scores[doc_id] = {'vector': 0, 'fts': 0}
            doc_data[doc_id] = {
                'id': doc_id,
                'content': doc['content'],
                'metadata': doc['metadata'],
                'similarity': 0  # Não veio da busca vetorial
            }
        
        doc_scores[doc_id]['fts'] = rrf_score
    
    # Calcular score final e ordenar
    final_results = []
    for doc_id, scores in doc_scores.items():
        total_score = scores['vector'] + scores['fts']
        doc_info = doc_data[doc_id]
        
        # Aplicar filtro de similaridade mínima (apenas se veio da busca vetorial)
        if scores['vector'] > 0 and doc_info['similarity'] < min_similarity:
            # Só incluir se também teve match no FTS
            if scores['fts'] == 0:
                continue
        
        final_results.append({
            'id': doc_info['id'],
            'content': doc_info['content'],
            'metadata': doc_info['metadata'],
            'similarity': doc_info['similarity'],
            'hybrid_score': total_score,
            'vector_contribution': scores['vector'],
            'fts_contribution': scores['fts']
        })
    
    # Ordenar por score híbrido
    final_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    # Limitar ao top_k
    final_results = final_results[:top_k]
    
    duration = time.time() - start_time
    
    log_step(db_logger, "Hybrid Search Complete",
              request_id=request_id,
              vector_results=len(vector_results),
              fts_results=len(fts_results),
              final_results=len(final_results),
              total_duration=f"{duration:.3f}s")
    
    return final_results


def check_fulltext_ready() -> bool:
    """
    Verifica se o Full-Text Search está configurado.
    
    Returns:
        True se a coluna search_vector existe e está populada
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Verificar se a coluna existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'documentos' AND column_name = 'search_vector'
                );
            """)
            column_exists = cur.fetchone()[0]
            
            if not column_exists:
                return False
            
            # Verificar se há documentos com search_vector populado
            cur.execute("""
                SELECT COUNT(*) FROM documentos WHERE search_vector IS NOT NULL;
            """)
            count = cur.fetchone()[0]
            
            return count > 0
            
    finally:
        conn.close()


def update_existing_documents_fts():
    """
    Atualiza o search_vector para todos os documentos existentes.
    Útil após adicionar a funcionalidade de FTS.
    """
    db_logger.info("Updating search_vector for all existing documents...")
    start_time = time.time()
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE documentos 
                SET search_vector = to_tsvector('portuguese', content)
                WHERE search_vector IS NULL OR search_vector = '';
            """)
            updated = cur.rowcount
            conn.commit()
            
        duration = time.time() - start_time
        db_logger.info(f"Updated {updated} documents in {duration:.2f}s")
        db_logger.info(f"{updated} documentos atualizados com Full-Text Search!")
        return updated
        
    except Exception as e:
        conn.rollback()
        db_logger.error(f"Error updating documents: {e}")
        raise
    finally:
        conn.close()
