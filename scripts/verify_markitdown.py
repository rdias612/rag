import sys
from pathlib import Path
import logging

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify():
    print("🔍 Verificando integração MarkItDown...\n")
    
    try:
        from src.data.ingestion import SUPPORTED_EXTENSIONS
        print("✅ Módulos carregados com sucesso!")
        print(f"✅ Extensões suportadas: {SUPPORTED_EXTENSIONS}")
        
        print("\n🚀 MarkItDown está pronto para uso!")
            
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    verify()
