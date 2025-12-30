"""
Configuração de Rate Limiting para a API.
"""
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_STORAGE,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_QUERY,
    RATE_LIMIT_SEARCH,
    RATE_LIMIT_INGEST,
    RATE_LIMIT_HEALTH
)
from src.core.logger import security_logger


def get_client_identifier():
    """
    Identifica o cliente para rate limiting.
    Usa API Key se presente, senão usa IP.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:8]}"  # Primeiros 8 chars
    return get_remote_address()


# Instância global do limiter
limiter = Limiter(
    key_func=get_client_identifier,
    storage_uri=RATE_LIMIT_STORAGE,
    default_limits=[RATE_LIMIT_DEFAULT] if RATE_LIMIT_ENABLED else [],
    enabled=RATE_LIMIT_ENABLED
)


def handle_rate_limit_exceeded(e):
    """Handler para quando limite é excedido."""
    security_logger.warning(
        "rate_limit_exceeded",
        client=get_client_identifier(),
        limit=str(e.description)
    )
    return jsonify({
        "error": "Rate limit exceeded",
        "message": str(e.description),
        "retry_after": e.retry_after
    }), 429


def init_rate_limiter(app: Flask):
    """Inicializa rate limiter na aplicação."""
    limiter.init_app(app)
    app.register_error_handler(429, handle_rate_limit_exceeded)
    
    api_logger.info(
        "rate_limiter_initialized",
        enabled=RATE_LIMIT_ENABLED,
        storage=RATE_LIMIT_STORAGE
    )


# Exportar limites configurados
LIMITS = {
    "query": RATE_LIMIT_QUERY,
    "search": RATE_LIMIT_SEARCH,
    "ingest": RATE_LIMIT_INGEST,
    "health": RATE_LIMIT_HEALTH
}
