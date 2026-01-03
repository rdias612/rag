#!/usr/bin/env python
"""
Script para iniciar o servidor Flask com logging configurado corretamente.
"""
import sys
import os

# Adicionar o diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
os.chdir(root_dir)

# Configurar logging ANTES de qualquer import da aplicação
from src.core.logging_config import setup_logging
setup_logging(force=True)

# Agora importar e criar a aplicação
from src.app import create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    use_reloader = os.environ.get("USE_RELOADER", "false").lower() == "true"
    threaded = os.environ.get("THREADED", "true").lower() == "true"
    
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=use_reloader,
        threaded=threaded
    )
