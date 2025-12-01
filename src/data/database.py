"""
Módulo de conexão e operações com PostgreSQL + pgvector.
"""
import json
import time
from typing import Optional
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import DATABASE_CONFIG, EMBEDDING_DIMENSION, TOP_K_RESULTS, MIN_SIMILARITY_THRESHOLD
from src.core.logger import (
    db_logger,
    log_db_query,
    log_db_result,
    log_db_search_with_embedding,
    log_db_search_results
)


@contextmanager
def get_connection():
    """Context manager para conexão com o banco de dados."""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        db_logger.error(f"Database transaction error: {e}")
        raise e
    finally:
        conn.close()


def init_database():
    """Inicializa o banco de dados com a extensão pgvector e tabela de documentos."""
    db_logger.info("Initializing database...")
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Habilitar extensão pgvector
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            log_db_query("CREATE EXTENSION", "CREATE EXTENSION IF NOT EXISTS vector")
            
            # Criar tabela de documentos
            create_table_query = f"""
                CREATE TABLE IF NOT EXISTS documentos (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding VECTOR({EMBEDDING_DIMENSION}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            cur.execute(create_table_query)
            log_db_query("CREATE TABLE", create_table_query)
            
            # Criar índice para busca vetorial (IVFFlat)
            create_index_query = """
                CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
                ON documentos 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """
            cur.execute(create_index_query)
            log_db_query("CREATE INDEX", create_index_query)
    
    duration = time.time() - start_time
    db_logger.info(f"Database initialized in {duration:.2f}s")
    print("✅ Banco de dados inicializado com sucesso!")


def insert_document(content: str, metadata: dict, embedding: list[float]) -> int:
    """
    Insere um documento com seu embedding no banco de dados.
    
    Args:
        content: Texto do chunk
        metadata: Metadados (source, page, etc.)
        embedding: Vetor de embedding
        
    Returns:
        ID do documento inserido
    """
    start_time = time.time()
    query = "INSERT INTO documentos (content, metadata, embedding) VALUES (%s, %s, %s) RETURNING id"
    log_db_query("INSERT", query, (content[:100], metadata, f"[{len(embedding)} dims]"))
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documentos (content, metadata, embedding)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (content, json.dumps(metadata), embedding)
            )
            doc_id = cur.fetchone()[0]
    
    duration = time.time() - start_time
    log_db_result("INSERT", 1, duration)
    
    return doc_id


def insert_documents_batch(documents: list[dict]) -> int:
    """
    Insere múltiplos documentos em batch para melhor performance.
    
    Args:
        documents: Lista de dicts com keys: content, metadata, embedding
        
    Returns:
        Número de documentos inseridos
    """
    start_time = time.time()
    log_db_query("INSERT BATCH", f"Inserting {len(documents)} documents")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Preparar dados para inserção em batch
            values = []
            for doc in documents:
                values.append((
                    doc["content"],
                    json.dumps(doc["metadata"]),
                    doc["embedding"]
                ))
            
            # Inserção em batch usando executemany
            cur.executemany(
                """
                INSERT INTO documentos (content, metadata, embedding)
                VALUES (%s, %s, %s);
                """,
                values
            )
    
    duration = time.time() - start_time
    log_db_result("INSERT BATCH", len(documents), duration)
    
    return len(documents)


def search_similar(
    query_embedding: list[float], 
    top_k: int = TOP_K_RESULTS,
    min_similarity: Optional[float] = None
) -> list[dict]:
    """
    Busca os documentos mais similares ao embedding da query.
    
    Args:
        query_embedding: Vetor de embedding da pergunta
        top_k: Número de resultados a retornar
        min_similarity: Similaridade mínima para incluir um resultado (0.0 a 1.0).
                       Se None, usa MIN_SIMILARITY_THRESHOLD da config.
                       Se 0.0, desabilita o filtro.
        
    Returns:
        Lista de documentos com content, metadata e score
    """
    start_time = time.time()
    
    # Usar threshold da config se não especificado
    if min_similarity is None:
        min_similarity = MIN_SIMILARITY_THRESHOLD
    
    # Log do embedding usado na busca
    log_db_search_with_embedding(query_embedding, top_k)
    
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM documentos
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding, query_embedding, top_k)
            )
            
            results = cur.fetchall()
    
    duration = time.time() - start_time
    results_list = [dict(row) for row in results]
    
    # Filtrar por similaridade mínima
    if min_similarity > 0:
        original_count = len(results_list)
        results_list = [r for r in results_list if r["similarity"] >= min_similarity]
        filtered_count = original_count - len(results_list)
        
        if filtered_count > 0:
            db_logger.info(
                f"Filtered {filtered_count}/{original_count} results below similarity threshold {min_similarity}"
            )
    
    # Log dos resultados da busca
    log_db_search_results(results_list, duration)
    
    return results_list


def get_document_count() -> int:
    """Retorna o número total de documentos no banco."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documentos;")
            count = cur.fetchone()[0]
            db_logger.debug(f"Document count: {count}")
            return count


def clear_documents():
    """Remove todos os documentos do banco. Use com cuidado!"""
    db_logger.warning("Clearing all documents from database!")
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documentos RESTART IDENTITY;")
    
    duration = time.time() - start_time
    log_db_result("TRUNCATE", 0, duration)
    print("⚠️ Todos os documentos foram removidos!")


def check_connection() -> bool:
    """Verifica se a conexão com o banco está funcionando."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                db_logger.info("Database connection successful")
                return True
    except Exception as e:
        db_logger.error(f"Database connection failed: {e}")
        return False
