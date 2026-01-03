"""
Configuração centralizada de logging.

Este módulo configura o sistema de logging do Python para gravar
logs tanto no console quanto em arquivo.

Formato de log: timestamp level module message
Exemplo: 2026-01-03 12:30:45 INFO flask.app Iniciando processamento do pedido 9988
"""
import logging
import logging.handlers
import sys
from pathlib import Path

from src.config import (
    LOG_LEVEL,
    LOG_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    BASE_DIR,
)

# Criar diretório de logs se não existir
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Flag para evitar configuração duplicada
_logging_configured = False


def _resolve_level(level_value):
    """Converte níveis informados como string/int para o inteiro esperado pelo logging."""
    try:
        return logging._checkLevel(level_value)
    except Exception:
        # Fallback seguro em caso de valores inválidos vindos do .env
        return logging.INFO


def setup_logging(force: bool = False):
    """
    Configura logging para console e arquivo.
    """
    global _logging_configured
    target_level = _resolve_level(LOG_LEVEL)

    root = logging.getLogger()

    # Se já configuramos mas alguém limpou handlers ou elevou o nível, reconfiguramos.
    if _logging_configured and not force:
        handlers_ok = bool(root.handlers)
        level_ok = root.getEffectiveLevel() <= target_level
        if handlers_ok and level_ok:
            return
    
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # Handler de console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(target_level)
    
    # Handler de arquivo - abre imediatamente para garantir escrita
    log_file_path = str(LOG_DIR / LOG_FILE)
    
    # Usar uma classe de FileHandler com flush automático
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()
    
    file_handler = FlushingFileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(target_level)
    
    # Configurar root logger
    root.setLevel(target_level)
    # Limpar handlers existentes para evitar duplicação
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    logging.captureWarnings(True)
    
    # Lista de loggers da aplicação - adicionar handlers diretamente
    app_loggers = [
        "rag",
        "rag.api",
        "rag.pipeline",
        "rag.search",
        "rag.database",
        "rag.security",
        "rag.repositories",
        "rag.webserver",
        "rag.ingestion",
        "rag.reranker",
        "rag.query_expansion",
        "rag.llm",
        "flask.app",
        "src.core",
        "src.data",
        "src.api",
        "apscheduler",
    ]
    
    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(target_level)
        # Limpar handlers existentes
        logger.handlers.clear()
        # Propagar para o root (que já tem console/file handlers)
        logger.propagate = True
    
    # Reduzir verbosidade de bibliotecas externas
    for lib_logger in ["sqlalchemy", "werkzeug", "urllib3", "httpx"]:
        logging.getLogger(lib_logger).setLevel(logging.WARNING)
    
    # Log de confirmação
    root.info("Logging configurado - arquivo: %s", log_file_path)
    _logging_configured = True
