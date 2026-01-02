import sys
from pathlib import Path
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify():
    logger.info("🔍 Verificando integração MarkItDown...")
    
    try:
        from src.data.ingestion import SUPPORTED_EXTENSIONS
        logger.info("✅ Módulos carregados com sucesso!")
        logger.info(f"✅ Extensões suportadas: {SUPPORTED_EXTENSIONS}")
        
        logger.info("🚀 MarkItDown está pronto para uso!")
            
    except ImportError as e:
        logger.error(f"❌ Erro ao importar módulos: {e}")
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    verify()
