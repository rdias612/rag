"""
Aplicação Flask principal.
"""
from flask import Flask, request
from flask_cors import CORS
import sys
import logging

from src.api.routes import api
from src.data.database import init_database, check_connection
from src.core.security import init_security, get_ssl_context
from src.config import ENABLE_HTTPS, ALLOWED_ORIGINS_LIST, CORS_MAX_AGE
from src.api.middleware.rate_limiter import init_rate_limiter
from src.core.logging_config import setup_logging

# Configurar logging ANTES de criar o Flask
setup_logging()
api_logger = logging.getLogger("rag.api")


def create_app() -> Flask:
    """Factory function para criar a aplicação Flask."""
    app = Flask(__name__)
    
    # Inicializar banco de dados (inclui migrações Alembic)
    # Isso garante que o banco esteja pronto independente de como o app é iniciado
    try:
        api_logger.info("Inicializando banco de dados via create_app()...")
        init_database()
    except Exception as e:
        api_logger.error(f"Erro ao inicializar banco de dados: {e}")
        # Não interrompemos aqui para permitir que o Flask mostre erros se necessário
        # ou para que o processo de boot continue se for um erro não-fatal
    
    # Configurar JSON para não escapar caracteres Unicode (acentos, ç, etc)
    app.json.ensure_ascii = False
    
    # CORS restritivo para produção
    CORS(app, resources={
        r"/api/*": {
            "origins": ALLOWED_ORIGINS_LIST,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
            "expose_headers": ["Content-Disposition"],
            "supports_credentials": True,
            "max_age": CORS_MAX_AGE
        }
    })
    
    # Registrar blueprint da API
    app.register_blueprint(api, url_prefix="/api")

    # Middleware simples de logging para todas as rotas /api/*
    @app.before_request
    def _log_request():
        if request.path.startswith("/api/"):
            try:
                body = request.get_json(silent=True)
            except Exception as e:
                body = None
                # Log exception for debugging
                api_logger.error("Middleware logging exception: %s", e)
            api_logger.info(
                "API Request %s %s | args=%s | json=%s",
                request.method, request.path, dict(request.args), body
            )

    @app.after_request
    def _log_response(response):
        if request.path.startswith("/api/"):
            api_logger.info(
                "API Response %s %s %d | len=%d",
                request.method, request.path, response.status_code, response.content_length
            )
        return response
    
    # Inicializar middleware de segurança (headers de segurança e HTTPS)
    init_security(app)
    
    # Inicializar Rate Limiter
    init_rate_limiter(app)
    
    # Rota raiz
    @app.route("/")
    def index():
        return {
            "name": "RAG API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/health",
                "stats": "/api/stats",
                "query": "/api/query (POST)",
                "query_stream": "/api/query/stream (POST)",
                "search": "/api/search (POST)"
            }
        }
    
    return app


def main():
    """Função principal para rodar a aplicação."""
    api_logger.info("Iniciando RAG API...")
    
    # Verificar conexão com banco
    api_logger.info("Verificando conexão com o banco de dados...")
    if not check_connection():
        api_logger.error("Não foi possível conectar ao banco de dados!")
        api_logger.error("Verifique se o PostgreSQL está rodando.")
        sys.exit(1)
    
    api_logger.info("Conexão com banco de dados OK!")
    
    # Criar e rodar aplicação (create_app já inicializa o banco)
    app = create_app()
    
    # Determinar protocolo (HTTP ou HTTPS)
    protocol = "https" if ENABLE_HTTPS else "http"
    api_logger.info("=" * 50)
    api_logger.info("🎉 RAG API rodando em: %s://localhost:5000", protocol)
    
    if ENABLE_HTTPS:
        api_logger.info("🔒 HTTPS habilitado com TLS")
    else:
        api_logger.warning("⚠️  HTTPS desabilitado (use apenas em desenvolvimento)")
    
    api_logger.info("=" * 50)
    
    # Configurar SSL context se HTTPS estiver habilitado
    ssl_context = get_ssl_context()
    
    # Run without the Flask reloader to avoid duplicate processes and missing logs
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
        ssl_context=ssl_context
    )


if __name__ == "__main__":
    main()
