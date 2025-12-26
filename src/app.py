"""
Aplicação Flask principal.
"""
from flask import Flask
from flask_cors import CORS

from src.api.routes import api
from src.data.database import init_database, check_connection


def create_app() -> Flask:
    """Factory function para criar a aplicação Flask."""
    app = Flask(__name__)
    
    # Configurar JSON para não escapar caracteres Unicode (acentos, ç, etc)
    app.json.ensure_ascii = False
    
    # Habilitar CORS para frontend (Vite default port 5173) e localhost
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://localhost:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Registrar blueprint da API
    app.register_blueprint(api, url_prefix="/api")
    
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
    print("🚀 Iniciando RAG API...")
    
    # Verificar conexão com banco
    print("📊 Verificando conexão com o banco de dados...")
    if not check_connection():
        print("❌ Não foi possível conectar ao banco de dados!")
        print("   Verifique se o PostgreSQL está rodando.")
        return
    
    print("✅ Conexão com banco de dados OK!")
    
    # Inicializar banco (criar tabelas se não existirem)
    print("🔧 Inicializando banco de dados...")
    init_database()
    
    # Criar e rodar aplicação
    app = create_app()
    
    print("\n" + "=" * 50)
    print("🎉 RAG API rodando em: http://localhost:5000")
    print("=" * 50 + "\n")
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )


if __name__ == "__main__":
    main()
