"""
Aplicação Flask principal.
"""
from flask import Flask
from flask_cors import CORS
import sys

from src.api.routes import api
from src.data.database import init_database, check_connection
from src.core.logger import api_logger
from src.core.security import init_security, get_ssl_context
from src.config import ENABLE_HTTPS


def create_app() -> Flask:
    """Factory function para criar a aplicação Flask."""
    app = Flask(__name__)
    
    # Configurar JSON para não escapar caracteres Unicode (acentos, ç, etc)
    app.json.ensure_ascii = False
    
    # Habilitar CORS para frontend (aceita preflight OPTIONS para todos endpoints)
    # Habilitar CORS totalmente permissivo para debug
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Registrar blueprint da API
    app.register_blueprint(api, url_prefix="/api")
    
    # Inicializar middleware de segurança (headers de segurança e HTTPS)
    init_security(app)
    
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
    
    # Inicializar banco (criar tabelas se não existirem)
    api_logger.info("Inicializando banco de dados...")
    init_database()
    
    # Criar e rodar aplicação
    app = create_app()
    
    print("\n" + "=" * 50)
    
    # Determinar protocolo (HTTP ou HTTPS)
    protocol = "https" if ENABLE_HTTPS else "http"
    print(f"🎉 RAG API rodando em: {protocol}://localhost:5000")
    
    if ENABLE_HTTPS:
        print(f"🔒 HTTPS habilitado com TLS")
    else:
        print("⚠️  HTTPS desabilitado (use apenas em desenvolvimento)")
    
    print("=" * 50 + "\n")
    
    # Configurar SSL context se HTTPS estiver habilitado
    ssl_context = get_ssl_context()
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        ssl_context=ssl_context
    )


if __name__ == "__main__":
    main()
