"""
Módulo de logging centralizado para o sistema RAG.
Configura saída formatada e estruturada para console e arquivos se necessário.
"""
import logging
import sys
import os

# Nível padrão de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Formato padrão limpo e legível
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str = "rag", level: str = None) -> logging.Logger:
    """
    Retorna uma instância de logger configurada.
    
    Args:
        name: Nome do logger (geralmente __name__)
        level: Nível de log opcional (DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger(name)
    log_level = getattr(logging, (level or LOG_LEVEL), logging.INFO)
    logger.setLevel(log_level)

    # Evitar adicionar múltiplos handlers caso setup seja chamado repetidamente
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    logger.propagate = False
    return logger


# Logger global padrão para conveniência
logger = setup_logger("rag")


def get_logger(name: str) -> logging.Logger:
    """Helper para obter loggers com o padrão do projeto."""
    return setup_logger(name)
