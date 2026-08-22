"""
Módulo de conexão e inicialização do PostgreSQL + pgvector.

As operações específicas de negócio (documentos, prompts, logs, avaliações)
estão implementadas nas classes de Repositório em `src.data.repositories`.
"""
import os
import time
from contextlib import contextmanager
from typing import Generator

import psycopg2
from alembic.config import Config
from alembic import command

from src.config import (
    DATABASE_CONFIG,
    DATABASE_URL,
    ENABLE_CONNECTION_POOL,
)
from src.core.logger import get_logger

logger = get_logger("data.database")

# Importar pool se habilitado
if ENABLE_CONNECTION_POOL:
    try:
        from src.core.connection_pool import get_db_connection as get_pooled_connection
    except ImportError:
        get_pooled_connection = None
else:
    get_pooled_connection = None


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager para gerenciar conexões com o PostgreSQL.
    
    Utiliza pool avançado se ENABLE_CONNECTION_POOL=True,
    ou abre conexão direta com statement/connection timeout configurados.
    """
    if ENABLE_CONNECTION_POOL and get_pooled_connection is not None:
        with get_pooled_connection() as conn:
            yield conn
    else:
        config_with_timeout = {
            **DATABASE_CONFIG,
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
        conn = psycopg2.connect(**config_with_timeout)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Erro na transação com banco de dados: %s", e, exc_info=True)
            raise e
        finally:
            conn.close()


# Alias para retrocompatibilidade
get_db_connection = get_connection


def check_connection() -> bool:
    """Verifica se o banco de dados está acessível e respondendo."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                res = cur.fetchone()
                return bool(res and res[0] == 1)
    except Exception as e:
        logger.error("Erro ao verificar conexão com o banco: %s", e)
        return False


def run_migrations() -> bool:
    """Executa as migrações do Alembic programaticamente."""
    logger.info("Iniciando migrações automáticas do banco de dados (Alembic)...")
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ini_path = os.path.join(base_dir, "alembic.ini")
        
        if not os.path.exists(ini_path):
            logger.warning("Arquivo alembic.ini não encontrado em: %s", ini_path)
            return False
            
        alembic_cfg = Config(ini_path)
        db_url = DATABASE_URL.replace("%", "%%")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrações do Alembic concluídas com sucesso!")
        return True
    except Exception as e:
        logger.error("Erro ao executar migrações do Alembic: %s", e, exc_info=True)
        return False


def init_database() -> bool:
    """
    Inicializa o banco de dados executando migrações e verificando prontidão.
    """
    logger.info("Inicializando banco de dados...")
    
    # 1. Executar migrações automáticas
    run_migrations()
    
    # 2. Verificar prontidão das tabelas
    start_time = time.time()
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
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
            msg = "Esquema 'documentos' não encontrado após migrações."
            logger.error(msg)
            raise RuntimeError(msg)

        duration = time.time() - start_time
        logger.info("Banco de dados pronto em %.2fs (schema gerenciado pelo Alembic)", duration)
        return True
    except Exception as e:
        logger.error("Falha na inicialização do banco: %s", e, exc_info=True)
        raise
