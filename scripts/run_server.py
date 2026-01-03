"""
Script para rodar o servidor Flask da aplicação RAG.
Este script é chamado pelo run_app.py para iniciar o backend.
"""
import os
import sys

# Adicionar o diretório raiz ao path para permitir imports relativos
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from src.app import create_app


def main():
    """Função principal para rodar o servidor Flask."""
    
    # Obter configurações de ambiente (setadas pelo run_app.py)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    use_reloader = os.environ.get('USE_RELOADER', 'false').lower() == 'true'
    threaded = os.environ.get('THREADED', 'true').lower() == 'true'
    
    print(f"Iniciando servidor Flask na porta {port}...")
    print(f"Debug: {debug}, Use Reloader: {use_reloader}, Threaded: {threaded}")
    
    # Criar aplicação
    app = create_app()
    
    # Rodar servidor
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=use_reloader,
        threaded=threaded
    )


if __name__ == "__main__":
    main()
