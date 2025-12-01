"""
Configurações centralizadas do sistema RAG.
"""
import os
from pathlib import Path


# =============================================================================
# Diretórios
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
DOCUMENTS_DIR = Path(r"C:\Users\Rian\Documents\treinamento")


# =============================================================================
# PostgreSQL + pgvector
# =============================================================================
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
    "database": os.getenv("DB_NAME", "ragdb"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "changeme"),
}

# String de conexão para psycopg2
DATABASE_URL = (
    f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}"
    f"@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
)


# =============================================================================
# LM Studio API
# =============================================================================
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")

# Modelo de embeddings (Nomic Embed v1.5)
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
EMBEDDING_DIMENSION = 768  # Dimensão do Nomic Embed v1.5

# Modelo LLM (Phi-3.5 Mini)
LLM_MODEL = "phi-3.5-mini-instruct"


# =============================================================================
# Chunking
# =============================================================================
CHUNK_SIZE = 800  # Tamanho do chunk em caracteres (~200 tokens)
CHUNK_OVERLAP = 150  # Overlap entre chunks


# =============================================================================
# RAG
# =============================================================================
TOP_K_RESULTS = 5  # Número de chunks retornados na busca


# =============================================================================
# Prompt Template
# =============================================================================
RAG_PROMPT_TEMPLATE = """Você é um assistente especializado e deve responder apenas com base no contexto fornecido.

[CONTEXTO]
{contexto}

[PERGUNTA]
{pergunta}

Se a resposta não estiver no contexto, diga: "Não há informações suficientes no contexto."
"""
