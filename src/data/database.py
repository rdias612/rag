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
    # Adiciona timeout de conexão e statement para evitar travamentos
    config_with_timeout = {
        **DATABASE_CONFIG,
        'connect_timeout': 10,  # 10 segundos para conectar
        'options': '-c statement_timeout=30000'  # 30 segundos max por query
    }
    db_logger.debug("Opening database connection...")
    conn = psycopg2.connect(**config_with_timeout)
    db_logger.debug("Database connection opened successfully")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        db_logger.error(f"Database transaction error: {e}")
        raise e
    finally:
        conn.close()
        db_logger.debug("Database connection closed")


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
    db_logger.info("Banco de dados pronto (schema gerenciado pelo Alembic)")


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
            # Garantir que o embedding é uma lista de floats e não contém None
            if not isinstance(embedding, list) or any(v is None for v in embedding):
                raise ValueError(f"Embedding inválido: contém valores nulos ou tipo incorreto. Tamanho: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
                
            cur.execute(
                """
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s::vector, %s)
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
                # Validar embedding
                is_invalid = False
                error_detail = ""
                
                if doc["embedding"] is None:
                    is_invalid = True
                    error_detail = "None (is null)"
                elif not isinstance(doc["embedding"], list):
                    is_invalid = True
                    error_detail = f"not a list (type: {type(doc['embedding'])})"
                else:
                    # Encontrar o índice do primeiro nulo (se houver)
                    for idx, val in enumerate(doc["embedding"]):
                        if val is None:
                            is_invalid = True
                            error_detail = f"contains NULL at index {idx}"
                            break
                
                if is_invalid:
                    file_info = doc.get("metadata", {}).get("source_path", "unknown")
                    db_logger.error(f"DETALHE ERRO EMBEDDING: {error_detail} para {file_info}")
                    raise ValueError(f"Embedding inválido detectado para {file_info}: {error_detail}")

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
                VALUES (%s, %s, %s::vector, %s);
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
    db_logger.debug("list_collections: Starting...")
    try:
        with get_connection() as conn:
            db_logger.debug("list_collections: Got connection, creating cursor...")
            with conn.cursor() as cur:
                db_logger.debug("list_collections: Executing query...")
                cur.execute(
                    """
                    SELECT DISTINCT collection_id
                    FROM documentos
                    WHERE collection_id IS NOT NULL
                    ORDER BY collection_id;
                    """
                )
                db_logger.debug("list_collections: Query executed, fetching results...")
                rows = cur.fetchall()
                result = [row[0] for row in rows]
                db_logger.debug(f"list_collections: Returning {len(result)} collections")
                return result
    except Exception as e:
        db_logger.error(f"list_collections: Error - {e}")
        raise


def clear_documents():
    """Remove todos os documentos do banco. Use com cuidado!"""
    db_logger.warning("Clearing all documents from database!")
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documentos RESTART IDENTITY;")
    
    duration = time.time() - start_time
    log_db_result("TRUNCATE", 0, duration)
    db_logger.warning("Todos os documentos foram removidos!")


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


# =============================================================================
# Controle de Ingestão de Documentos
# =============================================================================

def get_ingested_document(file_path: str) -> Optional[dict]:
    """
    Verifica se um documento já foi ingerido.
    
    Args:
        file_path: Caminho absoluto do arquivo
        
    Returns:
        Dict com informações do documento se existir, None caso contrário
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, file_path, file_hash, file_size, collection_id, 
                       chunks_count, status, ingested_at, updated_at
                FROM documentos_ingeridos
                WHERE file_path = %s;
                """,
                (file_path,)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def register_ingested_document(
    file_path: str,
    file_hash: str,
    file_size: int,
    collection_id: str = "default",
    chunks_count: int = 0,
    status: str = "success"
) -> int:
    """
    Registra um documento como ingerido (ou atualiza se já existir).
    
    Args:
        file_path: Caminho absoluto do arquivo
        file_hash: Hash SHA-256 do conteúdo
        file_size: Tamanho em bytes
        collection_id: ID da coleção
        chunks_count: Número de chunks gerados
        status: Status da ingestão (success, error, partial)
        
    Returns:
        ID do registro
    """
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documentos_ingeridos 
                    (file_path, file_hash, file_size, collection_id, chunks_count, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_path) DO UPDATE SET
                    file_hash = EXCLUDED.file_hash,
                    file_size = EXCLUDED.file_size,
                    collection_id = EXCLUDED.collection_id,
                    chunks_count = EXCLUDED.chunks_count,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id;
                """,
                (file_path, file_hash, file_size, collection_id, chunks_count, status)
            )
            doc_id = cur.fetchone()[0]
    
    duration = time.time() - start_time
    db_logger.info(f"Registered ingested document: {file_path} (ID: {doc_id}) in {duration:.2f}s")
    
    return doc_id


def remove_document_chunks_by_source(source_path: str) -> int:
    """
    Remove todos os chunks de um documento específico.
    Usado antes de re-ingerir um documento modificado.
    
    Args:
        source_path: Caminho do arquivo fonte (metadata->source_path)
        
    Returns:
        Número de chunks removidos
    """
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM documentos
                WHERE metadata->>'source_path' = %s;
                """,
                (source_path,)
            )
            deleted = cur.rowcount
    
    duration = time.time() - start_time
    db_logger.info(f"Removed {deleted} chunks from {source_path} in {duration:.2f}s")
    
    return deleted


def list_ingested_documents(collection_id: Optional[str] = None) -> list[dict]:
    """
    Lista todos os documentos ingeridos.
    
    Args:
        collection_id: Filtrar por coleção (opcional)
        
    Returns:
        Lista de documentos ingeridos
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if collection_id:
                cur.execute(
                    """
                    SELECT id, file_path, file_hash, file_size, collection_id, 
                           chunks_count, status, ingested_at, updated_at
                    FROM documentos_ingeridos
                    WHERE collection_id = %s
                    ORDER BY ingested_at DESC;
                    """,
                    (collection_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT id, file_path, file_hash, file_size, collection_id, 
                           chunks_count, status, ingested_at, updated_at
                    FROM documentos_ingeridos
                    ORDER BY ingested_at DESC;
                    """
                )
            rows = cur.fetchall()
            return [dict(row) for row in rows]


def remove_ingested_document_record(file_path: str) -> bool:
    """
    Remove o registro de um documento ingerido.
    
    Args:
        file_path: Caminho absoluto do arquivo
        
    Returns:
        True se removido, False se não encontrado
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM documentos_ingeridos
                WHERE file_path = %s;
                """,
                (file_path,)
            )
            return cur.rowcount > 0


def clear_all_documents() -> dict:
    """
    Limpa todas as tabelas de documentos (documentos e documentos_ingeridos).
    Usado para reprocessar toda a base de conhecimento do zero.
    
    Returns:
        Dicionário com contagem de registros removidos
    """
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Limpar tabela de chunks
            cur.execute("DELETE FROM documentos;")
            chunks_deleted = cur.rowcount
            
            # Limpar tabela de controle de ingestão
            cur.execute("DELETE FROM documentos_ingeridos;")
            control_deleted = cur.rowcount
    
    duration = time.time() - start_time
    db_logger.info(f"Cleared all documents: {chunks_deleted} chunks, {control_deleted} control records in {duration:.2f}s")
    
    return {
        "chunks_deleted": chunks_deleted,
        "control_records_deleted": control_deleted,
        "duration_seconds": duration
    }
