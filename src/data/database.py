"""
Módulo de conexão e operações com PostgreSQL + pgvector.
"""
import json
from typing import Optional
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import DATABASE_CONFIG, EMBEDDING_DIMENSION, TOP_K_RESULTS


@contextmanager
def get_connection():
    """Context manager para conexão com o banco de dados."""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Inicializa o banco de dados com a extensão pgvector e tabela de documentos."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Habilitar extensão pgvector
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Criar tabela de documentos
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS documentos (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSONB,
                    embedding VECTOR({EMBEDDING_DIMENSION}),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Criar índice para busca vetorial (IVFFlat)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
                ON documentos 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            
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
            return doc_id


def insert_documents_batch(documents: list[dict]) -> int:
    """
    Insere múltiplos documentos em batch para melhor performance.
    
    Args:
        documents: Lista de dicts com keys: content, metadata, embedding
        
    Returns:
        Número de documentos inseridos
    """
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
            
            return len(documents)


def search_similar(query_embedding: list[float], top_k: int = TOP_K_RESULTS) -> list[dict]:
    """
    Busca os documentos mais similares ao embedding da query.
    
    Args:
        query_embedding: Vetor de embedding da pergunta
        top_k: Número de resultados a retornar
        
    Returns:
        Lista de documentos com content, metadata e score
    """
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
            return [dict(row) for row in results]


def get_document_count() -> int:
    """Retorna o número total de documentos no banco."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documentos;")
            return cur.fetchone()[0]


def clear_documents():
    """Remove todos os documentos do banco. Use com cuidado!"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documentos RESTART IDENTITY;")
            print("⚠️ Todos os documentos foram removidos!")


def check_connection() -> bool:
    """Verifica se a conexão com o banco está funcionando."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False
