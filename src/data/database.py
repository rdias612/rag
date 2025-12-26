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
    """
    Verifica a conexão e se o esquema está presente.

    A criação/alteração de schema agora é gerenciada por migrações Alembic.
    Caso a tabela principal não exista, orienta a rodar as migrações.
    """
    db_logger.info("Checking database readiness (migrations managed via Alembic)...")
    start_time = time.time()

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Verificar se tabela principal existe
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'documentos'
                );
                """
            )
            exists = cur.fetchone()[0]

    if not exists:
        msg = (
            "Esquema não encontrado. Rode as migrações antes de continuar: "
            "alembic upgrade head"
        )
        db_logger.error(msg)
        raise RuntimeError(msg)

    duration = time.time() - start_time
    db_logger.info(f"Database ready check completed in {duration:.2f}s")
    print("✅ Banco de dados pronto (schema gerenciado pelo Alembic)")


def insert_document(content: str, metadata: dict, embedding: list[float], collection_id: str = "default") -> int:
    """
    Insere um documento com seu embedding no banco de dados.
    
    Args:
        content: Texto do chunk
        metadata: Metadados (source, page, etc.)
        embedding: Vetor de embedding
        collection_id: ID da coleção/projeto
        
    Returns:
        ID do documento inserido
    """
    start_time = time.time()
    query = "INSERT INTO documentos (content, metadata, embedding, collection_id) VALUES (%s, %s, %s, %s) RETURNING id"
    log_db_query("INSERT", query, (content[:100], metadata, f"[{len(embedding)} dims]", collection_id))
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (content, json.dumps(metadata), embedding, collection_id)
            )
            doc_id = cur.fetchone()[0]
    
    duration = time.time() - start_time
    log_db_result("INSERT", 1, duration)
    
    return doc_id


def insert_documents_batch(documents: list[dict]) -> int:
    """
    Insere múltiplos documentos em batch para melhor performance.
    
    Args:
        documents: Lista de dicts com keys: content, metadata, embedding, collection_id (opcional)
        
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
                    doc["embedding"],
                    doc.get("collection_id", "default")
                ))
            
            # Inserção em batch usando executemany
            cur.executemany(
                """
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s, %s);
                """,
                values
            )
    
    duration = time.time() - start_time
    log_db_result("INSERT BATCH", len(documents), duration)
    
    return len(documents)


def search_similar(
    query_embedding: list[float], 
    top_k: int = TOP_K_RESULTS,
    min_similarity: Optional[float] = None,
    collection_id: Optional[str] = None
) -> list[dict]:
    """
    Busca os documentos mais similares ao embedding da query.
    
    Args:
        query_embedding: Vetor de embedding da pergunta
        top_k: Número de resultados a retornar
        min_similarity: Similaridade mínima para incluir um resultado (0.0 a 1.0).
                       Se None, usa MIN_SIMILARITY_THRESHOLD da config.
                       Se 0.0, desabilita o filtro.
        collection_id: Filtrar por coleção específica (opcional)
        
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
            # Construir query dinamicamente baseada no filtro de coleção
            where_clause = ""
            params = [query_embedding, query_embedding, top_k]
            
            if collection_id:
                where_clause = "WHERE collection_id = %s"
                # Ordem esperada: embedding (para WHERE), collection_id, embedding (para ORDER BY), top_k
                params = [query_embedding, collection_id, query_embedding, top_k]
            
            query = f"""
                SELECT 
                    id,
                    content,
                    metadata,
                    collection_id,
                    1 - (embedding <=> %s::vector) as similarity
                FROM documentos
                {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """
            
            cur.execute(query, tuple(params))
            
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


def list_collections() -> list[str]:
    """Retorna a lista de collection_id distintos existentes."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT collection_id
                FROM documentos
                WHERE collection_id IS NOT NULL
                ORDER BY collection_id;
                """
            )
            rows = cur.fetchall()
            return [row[0] for row in rows]


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


def insert_feedback(session_id: str, message_index: int, rating: int, comment: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
    """
    Insere um feedback do usuário no banco de dados.
    """
    start_time = time.time()
    query = "INSERT INTO feedback (session_id, message_index, rating, comment, metadata) VALUES (%s, %s, %s, %s, %s)"
    log_db_query("INSERT FEEDBACK", query, (session_id, message_index, rating, comment))
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback (session_id, message_index, rating, comment, metadata)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (session_id, message_index, rating, comment, json.dumps(metadata) if metadata else None)
                )
        
        duration = time.time() - start_time
        log_db_result("INSERT FEEDBACK", 1, duration)
        return True
    except Exception as e:
        db_logger.error(f"Error inserting feedback: {e}")
        return False
