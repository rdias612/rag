"""
Módulo de conexão e operações com PostgreSQL + pgvector.

DEPRECATED: A maioria das funções neste módulo foi substituída por Repositories.
Use src.data.repositories em seu lugar:
- DocumentRepository: operações com documentos/chunks
- PromptRepository: operações com prompts  
- IngestionRepository: controle de ingestão
- FeedbackRepository: feedback de usuários

Este módulo será removido em uma versão futura.
"""
import json
import logging
import time
import warnings
import os
from functools import wraps
from typing import Optional
from contextlib import contextmanager

from alembic.config import Config
from alembic import command

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import (
    DATABASE_CONFIG,
    DATABASE_URL,
    EMBEDDING_DIMENSION,
    TOP_K_RESULTS,
    MIN_SIMILARITY_THRESHOLD,
    ENABLE_CONNECTION_POOL,
    ENABLE_ENCRYPTION,
    ENCRYPT_DOCUMENT_CONTENT,
    ENCRYPT_METADATA,
    ENCRYPT_FEEDBACK_COMMENTS
)
from src.core.connection_pool import get_db_connection as get_pooled_connection

# Standard logger for database operations
db_logger = logging.getLogger("rag.database")

# Importar funções de criptografia
try:
    from src.core.encryption import (
        encrypt_data,
        decrypt_data,
        encrypt_metadata,
        decrypt_metadata,
        is_encryption_enabled
    )
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logging.getLogger("rag.database").warning("Encryption module not available, encryption disabled")


def deprecated(replacement: str):
    """Decorator para marcar funções como deprecated."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__}() está deprecated. Use {replacement} em seu lugar.",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Cache em memória para prompts para evitar queries repetitivas
PROMPT_CACHE = {}
# Tempo de expiração do cache em segundos (ex: 5 minutos)
PROMPT_CACHE_TTL = 300
PROMPT_CACHE_LAST_UPDATE = 0


@contextmanager
def get_connection():
    """Context manager para conexão com o banco de dados.
    
    Usa o pool de conexões avançado se ENABLE_CONNECTION_POOL=True,
    caso contrário usa conexões diretas (método original).
    """
    if ENABLE_CONNECTION_POOL:
        # Usar pool de conexões avançado
        db_logger.debug("Using connection pool...")
        with get_pooled_connection() as conn:
            yield conn
    else:
        # Método original (fallback)
        config_with_timeout = {
            **DATABASE_CONFIG,
            'connect_timeout': 10,  # 10 segundos para conectar
            'options': '-c statement_timeout=30000'  # 30 segundos max por query
        }
        db_logger.debug("Opening database connection (direct)...")
        conn = psycopg2.connect(**config_with_timeout)
        db_logger.debug("Database connection opened successfully")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            db_logger.error("Database transaction error | error=%s", e, exc_info=True)
            raise e
        finally:
            conn.close()
        db_logger.debug("Database connection closed")


# Alias para backward compatibility
get_db_connection = get_connection


def run_migrations():
    """Executa as migrações do Alembic programaticamente."""
    db_logger.info("Iniciando migrações automáticas do banco de dados...")
    try:
        # Caminho para o arquivo alembic.ini (na raiz do projeto)
        # src/data/database.py -> src/data -> src -> raiz
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ini_path = os.path.join(base_dir, "alembic.ini")
        
        if not os.path.exists(ini_path):
            db_logger.error("Arquivo alembic.ini não encontrado em: %s", ini_path)
            return False
            
        alembic_cfg = Config(ini_path)
        
        # Sobrescrever a URL do banco com a das configurações do app
        # Escapar '%' para evitar problemas com o ConfigParser do Alembic
        db_url = DATABASE_URL.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Executar upgrade para a versão mais recente
        command.upgrade(alembic_cfg, "head")
        db_logger.info("Migrações concluídas com sucesso!")
        return True
    except Exception as e:
        db_logger.error("Erro ao executar migrações: %s", e, exc_info=True)
        return False


def init_database():
    """
    Verifica a conexão e executa as migrações do Alembic.
    """
    db_logger.info("Inicializando banco de dados (Alembic)...")
    
    # 1. Executar migrações automáticas
    run_migrations()
    
    # 2. Verificar prontidão
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
            "Esquema não encontrado mesmo após migrações. "
            "Verifique os logs do Alembic."
        )
        db_logger.error(msg)
        raise RuntimeError(msg)

    duration = time.time() - start_time
    db_logger.info("Database ready check completed in %.2fs", duration)
    db_logger.info("Banco de dados pronto (schema gerenciado pelo Alembic)")


@deprecated("DocumentRepository.create")
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
    db_logger.debug("DB INSERT | query=%s | params_count=%d", query[:500], 4)
    
    # Criptografar conteúdo e metadados se habilitado
    if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION:
        if ENCRYPT_DOCUMENT_CONTENT:
            content = encrypt_data(content)
        if ENCRYPT_METADATA:
            metadata_str = encrypt_metadata(metadata)
        else:
            metadata_str = json.dumps(metadata)
    else:
        metadata_str = json.dumps(metadata)
    
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
                (content, metadata_str, embedding, collection_id)
            )
            doc_id = cur.fetchone()[0]
    
    duration = time.time() - start_time
    db_logger.debug("DB INSERT Result | affected_rows=%d | duration=%.3fs", 1, duration)
    
    return doc_id


@deprecated("DocumentRepository.create_batch")
def insert_documents_batch(documents: list[dict]) -> int:
    """
    Insere múltiplos documentos em batch para melhor performance.
    
    Args:
        documents: Lista de dicts com keys: content, metadata, embedding, collection_id (opcional)
        
    Returns:
        Número de documentos inseridos
    """
    start_time = time.time()
    db_logger.debug("DB INSERT BATCH | documents_count=%d", len(documents))
    
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
                    db_logger.warning("SKIPPING CHUNK due to invalid embedding for %s: %s", file_info, error_detail)
                    continue

                # Criptografar conteúdo e metadados se habilitado
                content = doc["content"]
                metadata = doc["metadata"]
                
                if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION:
                    if ENCRYPT_DOCUMENT_CONTENT:
                        content = encrypt_data(content)
                    if ENCRYPT_METADATA:
                        metadata_str = encrypt_metadata(metadata)
                    else:
                        metadata_str = json.dumps(metadata)
                else:
                    metadata_str = json.dumps(metadata)

                values.append((
                    content,
                    metadata_str,
                    doc["embedding"],
                    doc.get("collection_id", "default")
                ))
            
            if not values:
                db_logger.warning("No documents were inserted in this batch (all were invalid)")
                return 0

            # Inserção em batch usando executemany
            cur.executemany(
                """
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s::vector, %s);
                """,
                values
            )
            inserted_count = len(values)
    
    duration = time.time() - start_time
    db_logger.debug("DB INSERT BATCH Result | affected_rows=%d | duration=%.3fs", inserted_count, duration)
    
    return inserted_count


@deprecated("DocumentRepository.find_similar")
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
    db_logger.info("DB Vector Search | embedding_dim=%d | embedding_sample=%s | top_k=%d",
                   len(query_embedding), str(query_embedding[:10]), top_k)
    
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Construir query dinamicamente baseada no filtro de coleção e chunk_type
            # Priorizamos buscar 'child' ou chunks sem tipo definido (legado)
            where_conditions = ["(metadata->>'chunk_type' != 'parent' OR metadata->>'chunk_type' IS NULL)"]
            params = [query_embedding] # Para o SELECT similarity
            
            if collection_id:
                where_conditions.append("collection_id = %s")
                params.append(collection_id)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Adicionar params para ORDER BY e LIMIT
            params.extend([query_embedding, top_k])
            
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
    # Descriptografar conteúdo e metadados se necessário
    results_list = []
    for row in results:
        row_dict = dict(row)
        
        if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION:
            # Descriptografar conteúdo
            if ENCRYPT_DOCUMENT_CONTENT and row_dict.get("content"):
                try:
                    row_dict["content"] = decrypt_data(row_dict["content"])
                except Exception as e:
                    db_logger.warning("Failed to decrypt content for doc %s: %s", row_dict.get('id'), e)
            
            # Descriptografar metadados
            if ENCRYPT_METADATA and row_dict.get("metadata"):
                try:
                    row_dict["metadata"] = decrypt_metadata(row_dict["metadata"])
                except Exception as e:
                    db_logger.warning("Failed to decrypt metadata for doc %s: %s", row_dict.get('id'), e)
                    row_dict["metadata"] = json.loads(row_dict["metadata"]) if row_dict["metadata"] else {}
        
        results_list.append(row_dict)
    
    # Filtrar por similaridade mínima
    if min_similarity > 0:
        original_count = len(results_list)
        results_list = [r for r in results_list if r["similarity"] >= min_similarity]
        filtered_count = original_count - len(results_list)
        
        if filtered_count > 0:
            db_logger.info(
                "Filtered %d/%d results below similarity threshold %.2f",
                filtered_count, original_count, min_similarity
            )
    
    # Log dos resultados da busca
    db_logger.info("DB Search Results | results_count=%d | duration=%.3fs", len(results_list), duration)
    
    return results_list


@deprecated("DocumentRepository.count")
def get_document_count() -> int:
    """Retorna o número total de documentos no banco."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documentos;")
            count = cur.fetchone()[0]
            db_logger.debug("Document count: %d", count)
            return count


@deprecated("DocumentRepository.list_collections")
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
                db_logger.debug("list_collections: Returning %d collections", len(result))
                return result
    except Exception as e:
        db_logger.error("list_collections: Error - %s", e, exc_info=True)
        raise


@deprecated("DocumentRepository.clear_all")
def clear_documents():
    """Remove todos os documentos do banco. Use com cuidado!"""
    db_logger.warning("Clearing all documents from database!")
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documentos RESTART IDENTITY;")
    
    duration = time.time() - start_time
    db_logger.debug("DB TRUNCATE Result | affected_rows=0 | duration=%.3fs", duration)
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
        db_logger.error("Database connection failed: %s", e, exc_info=True)
        return False


@deprecated("FeedbackRepository.create")
def insert_feedback(session_id: str, message_index: int, rating: int, comment: Optional[str] = None, metadata: Optional[dict] = None) -> bool:
    """
    Insere um feedback do usuário no banco de dados.
    """
    start_time = time.time()
    query = "INSERT INTO feedback (session_id, message_index, rating, comment, metadata) VALUES (%s, %s, %s, %s, %s)"
    db_logger.debug("DB INSERT FEEDBACK | query=%s | params_count=%d", query[:500], 5)
    
    try:
        # Criptografar comentário se habilitado
        encrypted_comment = comment
        if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION and ENCRYPT_FEEDBACK_COMMENTS and comment:
            try:
                encrypted_comment = encrypt_data(comment)
            except Exception as e:
                db_logger.warning("Failed to encrypt comment: %s", e)
        
        # Criptografar metadados se habilitado
        encrypted_metadata = metadata
        if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION and ENCRYPT_METADATA and metadata:
            try:
                encrypted_metadata = encrypt_metadata(metadata)
            except Exception as e:
                db_logger.warning("Failed to encrypt feedback metadata: %s", e)
                encrypted_metadata = json.dumps(metadata) if metadata else None
        else:
            encrypted_metadata = json.dumps(metadata) if metadata else None
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback (session_id, message_index, rating, comment, metadata)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (session_id, message_index, rating, encrypted_comment, encrypted_metadata)
                )
        
        duration = time.time() - start_time
        db_logger.debug("DB INSERT FEEDBACK Result | affected_rows=%d | duration=%.3fs", 1, duration)
        return True
    except Exception as e:
        db_logger.error("Error inserting feedback: %s", e, exc_info=True)
        return False


# =============================================================================
# Controle de Ingestão de Documentos
# =============================================================================

@deprecated("IngestionRepository.find_by_path")
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


@deprecated("IngestionRepository.create")
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
    db_logger.info("Registered ingested document: %s (ID: %d) in %.2fs", file_path, doc_id, duration)
    
    return doc_id


@deprecated("DocumentRepository.delete_by_source")
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
    db_logger.info("Removed %d chunks from %s in %.2fs", deleted, source_path, duration)
    
    return deleted


@deprecated("IngestionRepository.list_all")
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


@deprecated("IngestionRepository.delete_by_path")
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


@deprecated("DocumentRepository.clear_all e IngestionRepository.clear_all")
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
    db_logger.info("Cleared all documents: %d chunks, %d control records in %.2fs",
                   chunks_deleted, control_deleted, duration)
    
    return {
        "chunks_deleted": chunks_deleted,
        "control_records_deleted": control_deleted,
        "duration_seconds": duration
    }


# =============================================================================
# Gestão de Prompts
# =============================================================================

@deprecated("PromptRepository.find_by_name")
def get_prompt(name: str, use_cache: bool = True) -> Optional[str]:
    """
    Busca um prompt pelo nome no banco de dados.
    Utiliza um cache em memória para otimizar a performance.
    
    Args:
        name: Nome único do prompt
        use_cache: Se deve usar o cache ou forçar busca no banco
        
    Returns:
        Template do prompt ou None se não encontrado
    """
    global PROMPT_CACHE, PROMPT_CACHE_LAST_UPDATE
    
    current_time = time.time()
    
    # Verificar cache
    if use_cache and name in PROMPT_CACHE:
        if current_time - PROMPT_CACHE_LAST_UPDATE < PROMPT_CACHE_TTL:
            db_logger.debug("Prompt '%s' retrieved from cache", name)
            return PROMPT_CACHE[name]

    # Buscar no banco
    db_logger.debug("Fetching prompt '%s' from database...", name)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT template FROM prompts WHERE name = %s AND is_active = TRUE",
                    (name,)
                )
                row = cur.fetchone()
                if row:
                    template = row[0]
                    # Atualizar cache
                    PROMPT_CACHE[name] = template
                    PROMPT_CACHE_LAST_UPDATE = current_time
                    return template
                else:
                    db_logger.warning("Prompt '%s' not found in database", name)
                    return None
    except Exception as e:
        db_logger.error("Error fetching prompt '%s': %s", name, e, exc_info=True)
        return None


@deprecated("PromptRepository.update")
def update_prompt(name: str, template: str) -> bool:
    """
    Atualiza o template de um prompt.
    
    Args:
        name: Nome do prompt
        template: Novo conteúdo do template
        
    Returns:
        True se atualizado com sucesso
    """
    global PROMPT_CACHE
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE prompts 
                    SET template = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE name = %s
                    """,
                    (template, name)
                )
                updated = cur.rowcount > 0
                
                if updated:
                    # Invalidar cache
                    if name in PROMPT_CACHE:
                        del PROMPT_CACHE[name]
                    db_logger.info("Prompt '%s' updated successfully", name)
                    return True
                return False
    except Exception as e:
        db_logger.error("Error updating prompt '%s': %s", name, e, exc_info=True)
        return False


@deprecated("PromptRepository.list_all")
def list_prompts() -> list[dict]:
    """Lista todos os prompts disponíveis."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, category, priority, tags, description, 
                           use_case, is_active, updated_at, created_by
                    FROM prompts 
                    ORDER BY category, priority DESC, name
                """)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        db_logger.error("Error listing prompts: %s", e, exc_info=True)
        return []


@deprecated("PromptRepository.find_by_id")
def get_prompt_by_id(prompt_id: int) -> Optional[dict]:
    """Busca um prompt específico pelo ID."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, name, template, category, priority, tags, 
                           description, use_case, is_active, created_at, 
                           updated_at, created_by, version
                    FROM prompts 
                    WHERE id = %s
                """, (prompt_id,))
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        db_logger.error("Error fetching prompt %d: %s", prompt_id, e, exc_info=True)
        return None


@deprecated("PromptRepository.find_by_category")
def get_prompts_by_category(category: str, include_inactive: bool = False) -> list[dict]:
    """Busca todos os prompts de uma categoria."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = """
                    SELECT id, name, template, priority, tags, is_active
                    FROM prompts 
                    WHERE category = %s
                """
                params = [category]
                
                if not include_inactive:
                    query += " AND is_active = TRUE"
                
                query += " ORDER BY priority DESC, updated_at DESC"
                
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        db_logger.error("Error fetching prompts for category %s: %s", category, e, exc_info=True)
        return []


@deprecated("PromptRepository.count_active_in_category")
def count_active_prompts_in_category(category: str) -> int:
    """Conta quantos prompts ativos existem em uma categoria."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM prompts 
                    WHERE category = %s AND is_active = TRUE
                """, (category,))
                return cur.fetchone()[0]
    except Exception as e:
        db_logger.error("Error counting prompts in category %s: %s", category, e, exc_info=True)
        return 0


@deprecated("PromptRepository.create")
def create_prompt(
    name: str,
    template: str,
    category: str,
    description: str = None,
    priority: int = 100,
    tags: list[str] = None,
    use_case: str = None,
    created_by: str = 'user'
) -> tuple[bool, int, str]:
    """
    Cria um novo prompt.
    
    Returns:
        (success: bool, prompt_id: int, error_message: str)
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Verificar se nome já existe
                cur.execute("SELECT id FROM prompts WHERE name = %s", (name,))
                if cur.fetchone():
                    return False, 0, f"Já existe um prompt com o nome '{name}'"
                
                cur.execute("""
                    INSERT INTO prompts 
                        (name, template, category, description, priority, tags, use_case, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (name, template, category, description, priority, tags or [], use_case, created_by))
                
                prompt_id = cur.fetchone()[0]
                
                # Invalidar cache
                global PROMPT_CACHE
                PROMPT_CACHE.clear()
                
                db_logger.info("Created prompt '%s' (ID: %d) in category '%s'", name, prompt_id, category)
                return True, prompt_id, ""
                
    except Exception as e:
        db_logger.error("Error creating prompt: %s", e, exc_info=True)
        return False, 0, str(e)


@deprecated("PromptRepository.update")
def update_prompt_full(
    prompt_id: int,
    template: str = None,
    description: str = None,
    priority: int = None,
    tags: list[str] = None,
    use_case: str = None,
    is_active: bool = None
) -> tuple[bool, str]:
    """
    Atualiza um prompt existente.
    
    Returns:
        (success: bool, error_message: str)
    """
    global PROMPT_CACHE
    
    try:
        # Buscar prompt atual
        prompt = get_prompt_by_id(prompt_id)
        if not prompt:
            return False, "Prompt não encontrado"
        
        # Construir query dinâmica
        updates = []
        params = []
        
        if template is not None:
            updates.append("template = %s")
            params.append(template)
        
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        
        if priority is not None:
            updates.append("priority = %s")
            params.append(priority)
        
        if tags is not None:
            updates.append("tags = %s")
            params.append(tags)
        
        if use_case is not None:
            updates.append("use_case = %s")
            params.append(use_case)
        
        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)
        
        if not updates:
            return False, "Nenhuma atualização fornecida"
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        updates.append("version = version + 1")
        params.append(prompt_id)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = f"UPDATE prompts SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, params)
                
                if cur.rowcount == 0:
                    return False, "Prompt não encontrado"
                
                # Invalidar cache
                if prompt['name'] in PROMPT_CACHE:
                    del PROMPT_CACHE[prompt['name']]
                
                db_logger.info("Updated prompt ID %d ('%s')", prompt_id, prompt['name'])
                return True, ""
                
    except Exception as e:
        db_logger.error("Error updating prompt %d: %s", prompt_id, e, exc_info=True)
        return False, str(e)


# Categorias críticas que devem sempre ter pelo menos 1 prompt ativo
CRITICAL_CATEGORIES = {
    'rag_main': 'Prompt principal para RAG',
    'hyde': 'Geração de documentos hipotéticos',
    'query_expansion': 'Expansão de queries'
}


@deprecated("PromptRepository.can_delete")
def can_delete_prompt(prompt_id: int) -> tuple[bool, str]:
    """
    Verifica se um prompt pode ser deletado.
    
    Returns:
        (can_delete: bool, error_message: str)
    """
    prompt = get_prompt_by_id(prompt_id)
    
    if not prompt:
        return False, "Prompt não encontrado"
    
    category = prompt.get('category')
    
    # Verificar se é categoria crítica
    if category in CRITICAL_CATEGORIES:
        count = count_active_prompts_in_category(category)
        
        # Se for o último ativo, não pode deletar
        if prompt['is_active'] and count <= 1:
            category_desc = CRITICAL_CATEGORIES[category]
            return False, f"Não é possível deletar o último prompt ativo da categoria '{category}'. Esta categoria é essencial: {category_desc}."
    
    return True, ""


@deprecated("PromptRepository.delete")
def delete_prompt_safe(prompt_id: int) -> tuple[bool, str]:
    """
    Deleta um prompt com validação de segurança.
    
    Returns:
        (success: bool, error_message: str)
    """
    global PROMPT_CACHE
    
    # Verificar se pode deletar
    can_delete, error_msg = can_delete_prompt(prompt_id)
    if not can_delete:
        return False, error_msg
    
    try:
        prompt = get_prompt_by_id(prompt_id)
        if not prompt:
            return False, "Prompt não encontrado"
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM prompts WHERE id = %s", (prompt_id,))
                
                if cur.rowcount == 0:
                    return False, "Prompt não encontrado"
                
                # Invalidar cache
                if prompt['name'] in PROMPT_CACHE:
                    del PROMPT_CACHE[prompt['name']]
                
                db_logger.info("Deleted prompt ID %d ('%s')", prompt_id, prompt['name'])
                return True, ""
                
    except Exception as e:
        db_logger.error("Error deleting prompt %d: %s", prompt_id, e, exc_info=True)
        return False, str(e)


@deprecated("DocumentRepository.get_parent_content")
def get_parent_content(source_path: str, parent_index: int) -> Optional[str]:
    """
    Recupera o texto de um chunk pai baseado no caminho do arquivo e índice.
    
    Args:
        source_path: Caminho completo do arquivo original
        parent_index: Índice do chunk pai no documento
        
    Returns:
        Conteúdo do texto do pai ou None se não encontrado
    """
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content
                FROM documentos
                WHERE metadata->>'source_path' = %s
                AND (metadata->>'chunk_index')::int = %s
                AND metadata->>'chunk_type' = 'parent'
                LIMIT 1;
                """,
                (source_path, parent_index)
            )
            row = cur.fetchone()
            
    content = row[0] if row else None
    
    # Descriptografar se necessário
    if content and ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION and ENCRYPT_DOCUMENT_CONTENT:
        try:
            content = decrypt_data(content)
        except Exception as e:
            db_logger.warning("Failed to decrypt parent content: %s", e)
            
    duration = time.time() - start_time
    if content:
        db_logger.debug("Retrieved parent content for %s index %d in %.4fs", source_path, parent_index, duration)
    
    return content
