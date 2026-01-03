"""
Configuração centralizada de logging via dictConfig.

Este módulo configura o sistema de logging do Python seguindo as
diretrizes enterprise para Flask, unificando a configuração através
do Root Logger para capturar logs do Flask, SQLAlchemy e outras
bibliotecas de terceiros.

Formato de log: timestamp level module message
Exemplo: 2026-01-03 12:30:45 INFO flask.app Iniciando processamento do pedido 9988
"""
import logging
from logging.config import dictConfig
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


def setup_logging():
    """
    Configura logging via dictConfig.

    Esta função deve ser chamada ANTES de criar a instância Flask
    para garantir que todos os logs (incluindo logs de inicialização)
    sigam o formato configurado.
    """
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": LOG_FORMAT,
                "datefmt": LOG_DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": str(LOG_DIR / LOG_FILE),
                "maxBytes": LOG_MAX_BYTES,
                "backupCount": LOG_BACKUP_COUNT,
            },
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file"],
        },
        # Configurar loggers específicos
        "loggers": {
            "flask.app": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",  # Reduzir verbosidade do SQLAlchemy
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "werkzeug": {
                "level": "WARNING",  # Reduzir verbosidade do Werkzeug
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
    })
