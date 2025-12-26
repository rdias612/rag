import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Environment
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    
    # =========================================================================
    # Diretórios
    # =========================================================================
    BASE_DIR: Path = Path(__file__).parent.parent
    DOCUMENTS_DIR: Path = Path(r"C:\Users\Rian\Documents\treinamento")

    # =========================================================================
    # PostgreSQL + pgvector
    # =========================================================================
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    DB_NAME: str = "ragdb"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "changeme"

    @property
    def DATABASE_CONFIG(self) -> Dict[str, Any]:
        return {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
        }

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # =========================================================================
    # LM Studio API
    # =========================================================================
    LM_STUDIO_BASE_URL: str = "http://127.0.0.1:1234/v1"
    
    # Modelo de embeddings (BGE-M3)
    EMBEDDING_MODEL: str = Field(default="text-embedding-bge-m3", validation_alias="EMBEDDING_MODEL")
    EMBEDDING_DIMENSION: int = Field(default=1024, validation_alias="EMBEDDING_DIMENSION")
    
    # Modelo LLM (Phi-3.5 Mini)
    LLM_MODEL: str = Field(default="phi-3.5-mini-instruct", validation_alias="LLM_MODEL")

    # =========================================================================
    # Chunking
    # =========================================================================
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    USE_SEMANTIC_CHUNKING: bool = True
    MIN_CHUNK_SIZE: int = 200
    CHUNK_OVERLAP_SENTENCES: int = 1

    # =========================================================================
    # RAG
    # =========================================================================
    TOP_K_RESULTS: int = 10
    MIN_SIMILARITY_THRESHOLD: float = 0.4

    # =========================================================================
    # Busca Híbrida (Vetorial + Full-Text Search)
    # =========================================================================
    ENABLE_HYBRID_SEARCH: bool = True
    HYBRID_SEARCH_ALPHA: float = 0.7

    # =========================================================================
    # Compressão de Contexto
    # =========================================================================
    ENABLE_CONTEXT_COMPRESSION: bool = True
    CONTEXT_COMPRESSION_THRESHOLD: int = 3000
    CONTEXT_COMPRESSION_TARGET_RATIO: float = 0.5
    CONTEXT_COMPRESSION_METHOD: str = "llm"

    # =========================================================================
    # Conversação
    # =========================================================================
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONVERSATION_HISTORY: int = 10

    # =========================================================================
    # Configurações Adicionais (Phases 1-4)
    # =========================================================================
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_CACHE_MAX_SIZE: int = 1000
    USE_QUESTION_CLASSIFIER: bool = True
    USE_ENHANCED_PROMPTS: bool = True
    ENABLE_RERANKING: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKING_TOP_K_INITIAL: int = 15
    ENABLE_QUERY_EXPANSION: bool = True
    QUERY_EXPANSION_COUNT: int = 3
    ENABLE_MMR: bool = True
    MMR_LAMBDA: float = 0.7
    ENABLE_HYDE: bool = True
    HYDE_WEIGHT: float = 0.5
    ENABLE_CONTEXTUAL_METADATA: bool = True
    CONTEXTUAL_NEIGHBOR_SUMMARIES: bool = True
    CONTEXTUAL_SECTION_DETECTION: bool = True
    ENABLE_HIERARCHICAL_CHUNKING: bool = False
    PARENT_CHUNK_SIZE: int = 2000
    CHILD_CHUNK_SIZE: int = 400
    CHILD_CHUNK_OVERLAP: int = 50
    ENABLE_AUTO_EVALUATION: bool = False
    ENABLE_ADAPTIVE_RETRIEVAL: bool = True
    ENABLE_SELF_RAG: bool = False
    SELF_RAG_MIN_SCORE: int = 60
    ENABLE_SENTENCE_WINDOW: bool = False
    SENTENCE_WINDOW_SIZE: int = 2

    model_config = SettingsConfigDict(
        # Prioridade: .env.{APP_ENV} > .env
        env_file=(".env", f".env.{os.getenv('APP_ENV', 'dev')}"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instância global de configurações
settings = Settings()

# =============================================================================
# Compatibilidade (Exportando nomes originais)
# =============================================================================
BASE_DIR = settings.BASE_DIR
DOCUMENTS_DIR = settings.DOCUMENTS_DIR
DATABASE_CONFIG = settings.DATABASE_CONFIG
DATABASE_URL = settings.DATABASE_URL
LM_STUDIO_BASE_URL = settings.LM_STUDIO_BASE_URL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
EMBEDDING_DIMENSION = settings.EMBEDDING_DIMENSION
LLM_MODEL = settings.LLM_MODEL
CHUNK_SIZE = settings.CHUNK_SIZE
CHUNK_OVERLAP = settings.CHUNK_OVERLAP
USE_SEMANTIC_CHUNKING = settings.USE_SEMANTIC_CHUNKING
MIN_CHUNK_SIZE = settings.MIN_CHUNK_SIZE
CHUNK_OVERLAP_SENTENCES = settings.CHUNK_OVERLAP_SENTENCES
TOP_K_RESULTS = settings.TOP_K_RESULTS
MIN_SIMILARITY_THRESHOLD = settings.MIN_SIMILARITY_THRESHOLD
ENABLE_HYBRID_SEARCH = settings.ENABLE_HYBRID_SEARCH
HYBRID_SEARCH_ALPHA = settings.HYBRID_SEARCH_ALPHA
ENABLE_CONTEXT_COMPRESSION = settings.ENABLE_CONTEXT_COMPRESSION
CONTEXT_COMPRESSION_THRESHOLD = settings.CONTEXT_COMPRESSION_THRESHOLD
CONTEXT_COMPRESSION_TARGET_RATIO = settings.CONTEXT_COMPRESSION_TARGET_RATIO
CONTEXT_COMPRESSION_METHOD = settings.CONTEXT_COMPRESSION_METHOD
SESSION_TIMEOUT_MINUTES = settings.SESSION_TIMEOUT_MINUTES
MAX_CONVERSATION_HISTORY = settings.MAX_CONVERSATION_HISTORY
EMBEDDING_CACHE_ENABLED = settings.EMBEDDING_CACHE_ENABLED
EMBEDDING_CACHE_MAX_SIZE = settings.EMBEDDING_CACHE_MAX_SIZE
USE_QUESTION_CLASSIFIER = settings.USE_QUESTION_CLASSIFIER
USE_ENHANCED_PROMPTS = settings.USE_ENHANCED_PROMPTS
ENABLE_RERANKING = settings.ENABLE_RERANKING
RERANKER_MODEL = settings.RERANKER_MODEL
RERANKING_TOP_K_INITIAL = settings.RERANKING_TOP_K_INITIAL
ENABLE_QUERY_EXPANSION = settings.ENABLE_QUERY_EXPANSION
QUERY_EXPANSION_COUNT = settings.QUERY_EXPANSION_COUNT
ENABLE_MMR = settings.ENABLE_MMR
MMR_LAMBDA = settings.MMR_LAMBDA
ENABLE_HYDE = settings.ENABLE_HYDE
HYDE_WEIGHT = settings.HYDE_WEIGHT
ENABLE_CONTEXTUAL_METADATA = settings.ENABLE_CONTEXTUAL_METADATA
CONTEXTUAL_NEIGHBOR_SUMMARIES = settings.CONTEXTUAL_NEIGHBOR_SUMMARIES
CONTEXTUAL_SECTION_DETECTION = settings.CONTEXTUAL_SECTION_DETECTION
ENABLE_HIERARCHICAL_CHUNKING = settings.ENABLE_HIERARCHICAL_CHUNKING
PARENT_CHUNK_SIZE = settings.PARENT_CHUNK_SIZE
CHILD_CHUNK_SIZE = settings.CHILD_CHUNK_SIZE
CHILD_CHUNK_OVERLAP = settings.CHILD_CHUNK_OVERLAP
ENABLE_AUTO_EVALUATION = settings.ENABLE_AUTO_EVALUATION
ENABLE_ADAPTIVE_RETRIEVAL = settings.ENABLE_ADAPTIVE_RETRIEVAL
ENABLE_SELF_RAG = settings.ENABLE_SELF_RAG
SELF_RAG_MIN_SCORE = settings.SELF_RAG_MIN_SCORE
ENABLE_SENTENCE_WINDOW = settings.ENABLE_SENTENCE_WINDOW
SENTENCE_WINDOW_SIZE = settings.SENTENCE_WINDOW_SIZE

# =============================================================================
# Prompts (Mantidos como constantes por não precisarem de override via env)
# =============================================================================
RAG_PROMPT_TEMPLATE = """Você é um assistente especializado e deve responder apenas com base no contexto fornecido.

[CONTEXTO]
{contexto}

[PERGUNTA]
{pergunta}

Se a resposta não estiver no contexto, diga: "Não há informações suficientes no contexto."
"""

RAG_PROMPT_TEMPLATE_WITH_HISTORY = """Você é um assistente especializado e deve responder apenas com base no contexto fornecido.
Considere o histórico da conversa para entender perguntas de follow-up.

[HISTÓRICO DA CONVERSA]
{historico}

[CONTEXTO DOS DOCUMENTOS]
{contexto}

[PERGUNTA ATUAL]
{pergunta}

Instruções:
- Use o histórico para entender referências como "ele", "isso", "o mesmo", etc.
- Responda baseando-se APENAS no contexto fornecido.
- Se a resposta não estiver no contexto, diga: "Não há informações suficientes no contexto."
"""

RAG_PROMPT_ENHANCED = """Você é um assistente especializado. Analise o contexto cuidadosamente antes de responder.

[CONTEXTO]
{contexto}

[PERGUNTA]
{pergunta}

[INSTRUÇÕES]
1. Primeiro, identifique quais partes do contexto são mais relevantes para a pergunta.
2. Estruture sua resposta de forma clara e organizada.
3. Cite informações específicas do contexto quando apropriado.
4. Se a pergunta não puder ser respondida com o contexto, explique o que está faltando.
{instrucoes_tipo}

[RESPOSTA]
"""

RAG_PROMPT_ENHANCED_WITH_HISTORY = """Você é um assistente especializado. Analise o contexto e histórico cuidadosamente.

[HISTÓRICO DA CONVERSA]
{historico}

[CONTEXTO DOS DOCUMENTOS]
{contexto}

[PERGUNTA ATUAL]
{pergunta}

[INSTRUÇÕES]
1. Use o histórico para entender referências como "ele", "isso", "o mesmo".
2. Identifique quais partes do contexto são relevantes para a pergunta.
3. Estruture sua resposta de forma clara e organizada.
4. Se não puder responder completamente, explique o que está faltando.
{instrucoes_tipo}

[RESPOSTA]
"""
