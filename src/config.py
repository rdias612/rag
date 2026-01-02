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
    
    # Configurações do Reranker
    # RERANKER_TYPE: "llm" (usa prompt na LLM) ou "api" (usa endpoint /rerank de Cross-Encoder)
    RERANKER_TYPE: str = Field(default="llm", validation_alias="RERANKER_TYPE")
    RERANKER_MODEL: str = Field(default="phi-3.5-mini-instruct", validation_alias="RERANKER_MODEL")
    RERANKER_API_URL: Optional[str] = Field(default=None, validation_alias="RERANKER_API_URL")

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
    ENABLE_RERANKING: bool = False
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
    PARENT_CHUNK_SIZE: int = 2000
    CHILD_CHUNK_SIZE: int = 400
    CHILD_CHUNK_OVERLAP: int = 50
    ENABLE_AUTO_EVALUATION: bool = False
    ENABLE_EVALUATION_UI: bool = True
    EVALUATION_MIN_SCORE_THRESHOLD: float = 0.4
    ENABLE_SELF_RAG: bool = False
    SELF_RAG_MIN_SCORE: int = 60
    SELF_RAG_MAX_ITERATIONS: int = 1
    ENABLE_SENTENCE_WINDOW: bool = False
    SENTENCE_WINDOW_SIZE: int = 2

    # =========================================================================
    # Adaptive Retrieval (Phase 2)
    # =========================================================================
    ENABLE_ADAPTIVE_RETRIEVAL: bool = True
    ADAPTIVE_RETRIEVAL_LOG_LEVEL: str = "INFO"  # DEBUG ou INFO
    ADAPTIVE_TOP_K_MIN: int = 3
    ADAPTIVE_TOP_K_MAX: int = 20
    ADAPTIVE_MIN_SIM_MIN: float = 0.2
    ADAPTIVE_MIN_SIM_MAX: float = 0.8

    # =========================================================================
    # Batch Processing Avançado (Phase 6.1)
    # =========================================================================
    ENABLE_ADVANCED_BATCH_PROCESSING: bool = True
    ADVANCED_BATCH_MAX_WORKERS: int = 4
    ADVANCED_BATCH_SIZE: int = 32
    ADVANCED_WORKER_TIMEOUT: int = 120
    USE_ASYNC_BATCH_PROCESSING: bool = True

    # =========================================================================
    # Connection Pooling Avançado (Phase 6.2)
    # =========================================================================
    ENABLE_CONNECTION_POOL: bool = True
    DB_POOL_MIN_CONN: int = 5
    DB_POOL_MAX_CONN: int = 20
    DB_CONNECTION_TIMEOUT: int = 10
    DB_STATEMENT_TIMEOUT: int = 30

    # =========================================================================
    # Criptografia de Dados (Phase 5.4)
    # =========================================================================
    ENABLE_ENCRYPTION: bool = False
    ENCRYPTION_KEY: Optional[str] = None
    
    # Criptografia de campos específicos
    ENCRYPT_DOCUMENT_CONTENT: bool = True
    ENCRYPT_METADATA: bool = True
    ENCRYPT_FEEDBACK_COMMENTS: bool = True

    # =========================================================================
    # Segurança em Trânsito (TLS/HTTPS)
    # =========================================================================
    ENABLE_HTTPS: bool = False
    SSL_CERT_PATH: Optional[str] = None
    SSL_KEY_PATH: Optional[str] = None
    SSL_PROTOCOL: str = "TLSv1.3"
    SSL_CIPHERS: str = "HIGH:!aNULL:!MD5"

    # =========================================================================
    # CORS Configuration
    # =========================================================================
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    CORS_MAX_AGE: int = 3600  # 1 hora de cache para preflight
    
    @property
    def ALLOWED_ORIGINS_LIST(self) -> list[str]:
        """Retorna lista de origens permitidas."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # =========================================================================
    # Rate Limiting (Phase 7)
    # =========================================================================
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_STORAGE: str = "memory://"  # ou "redis://localhost:6379"

    # Limites padrão
    RATE_LIMIT_DEFAULT: str = "200 per day, 50 per hour"

    # Limites específicos por endpoint
    RATE_LIMIT_QUERY: str = "30 per minute"        # Queries RAG (pesadas)
    RATE_LIMIT_SEARCH: str = "60 per minute"       # Busca sem LLM
    RATE_LIMIT_INGEST: str = "20 per minute"       # Ingestão de docs
    RATE_LIMIT_HEALTH: str = "120 per minute"      # Health checks

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
PARENT_CHUNK_SIZE = settings.PARENT_CHUNK_SIZE
CHILD_CHUNK_SIZE = settings.CHILD_CHUNK_SIZE
CHILD_CHUNK_OVERLAP = settings.CHILD_CHUNK_OVERLAP
ENABLE_AUTO_EVALUATION = settings.ENABLE_AUTO_EVALUATION
ENABLE_EVALUATION_UI = settings.ENABLE_EVALUATION_UI
EVALUATION_MIN_SCORE_THRESHOLD = settings.EVALUATION_MIN_SCORE_THRESHOLD
ENABLE_ADAPTIVE_RETRIEVAL = settings.ENABLE_ADAPTIVE_RETRIEVAL
ENABLE_SELF_RAG = settings.ENABLE_SELF_RAG
SELF_RAG_MIN_SCORE = settings.SELF_RAG_MIN_SCORE
SELF_RAG_MAX_ITERATIONS = settings.SELF_RAG_MAX_ITERATIONS
ENABLE_SENTENCE_WINDOW = settings.ENABLE_SENTENCE_WINDOW
SENTENCE_WINDOW_SIZE = settings.SENTENCE_WINDOW_SIZE
ENABLE_ADVANCED_BATCH_PROCESSING = settings.ENABLE_ADVANCED_BATCH_PROCESSING
ADVANCED_BATCH_MAX_WORKERS = settings.ADVANCED_BATCH_MAX_WORKERS
ADVANCED_BATCH_SIZE = settings.ADVANCED_BATCH_SIZE
ADVANCED_WORKER_TIMEOUT = settings.ADVANCED_WORKER_TIMEOUT
USE_ASYNC_BATCH_PROCESSING = settings.USE_ASYNC_BATCH_PROCESSING

# =============================================================================
# Connection Pool (Phase 6.2)
# =============================================================================
ENABLE_CONNECTION_POOL = settings.ENABLE_CONNECTION_POOL
DB_POOL_MIN_CONN = settings.DB_POOL_MIN_CONN
DB_POOL_MAX_CONN = settings.DB_POOL_MAX_CONN
DB_CONNECTION_TIMEOUT = settings.DB_CONNECTION_TIMEOUT
DB_STATEMENT_TIMEOUT = settings.DB_STATEMENT_TIMEOUT

# =============================================================================#
# Criptografia (Phase 5.4)
# =============================================================================
ENABLE_ENCRYPTION = settings.ENABLE_ENCRYPTION
ENCRYPTION_KEY = settings.ENCRYPTION_KEY
ENCRYPT_DOCUMENT_CONTENT = settings.ENCRYPT_DOCUMENT_CONTENT
ENCRYPT_METADATA = settings.ENCRYPT_METADATA
ENCRYPT_FEEDBACK_COMMENTS = settings.ENCRYPT_FEEDBACK_COMMENTS

# =============================================================================
# Segurança em Trânsito (TLS/HTTPS)
# =============================================================================
ENABLE_HTTPS = settings.ENABLE_HTTPS
SSL_CERT_PATH = settings.SSL_CERT_PATH
SSL_KEY_PATH = settings.SSL_KEY_PATH
SSL_PROTOCOL = settings.SSL_PROTOCOL
SSL_CIPHERS = settings.SSL_CIPHERS

# =============================================================================
# CORS Configuration
# =============================================================================
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS
ALLOWED_ORIGINS_LIST = settings.ALLOWED_ORIGINS_LIST
CORS_MAX_AGE = settings.CORS_MAX_AGE

# =============================================================================
# Rate Limiting (Phase 7)
# =============================================================================
RATE_LIMIT_ENABLED = settings.RATE_LIMIT_ENABLED
RATE_LIMIT_STORAGE = settings.RATE_LIMIT_STORAGE
RATE_LIMIT_DEFAULT = settings.RATE_LIMIT_DEFAULT
RATE_LIMIT_QUERY = settings.RATE_LIMIT_QUERY
RATE_LIMIT_SEARCH = settings.RATE_LIMIT_SEARCH
RATE_LIMIT_INGEST = settings.RATE_LIMIT_INGEST
RATE_LIMIT_HEALTH = settings.RATE_LIMIT_HEALTH

# =============================================================================
# Adaptive Retrieval (Phase 2)
# =============================================================================
ADAPTIVE_RETRIEVAL_LOG_LEVEL = settings.ADAPTIVE_RETRIEVAL_LOG_LEVEL
ADAPTIVE_TOP_K_MIN = settings.ADAPTIVE_TOP_K_MIN
ADAPTIVE_TOP_K_MAX = settings.ADAPTIVE_TOP_K_MAX
ADAPTIVE_MIN_SIM_MIN = settings.ADAPTIVE_MIN_SIM_MIN
ADAPTIVE_MIN_SIM_MAX = settings.ADAPTIVE_MIN_SIM_MAX

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

RAG_PROMPT_ENHANCED = """Você é o **Assistente de Base de Conhecimento**, um especialista em extrair e sintetizar informações de documentos técnicos. Sua missão é fornecer respostas precisas, baseando-se estritamente no [CONTEXTO] fornecido.

### DIRETRIZES:
1. **Fidelidade ao Contexto**: Responda APENAS com informações contidas no [CONTEXTO]. Se a informação não for encontrada, admita claramente: "Não encontrei informações sobre [tópico] nos documentos fornecidos."
2. **Citações**: Sempre que fizer uma afirmação baseada em um documento, cite a fonte (ex: [Fonte: manual_tecnico.pdf, pág. 12]).
3. **Formatação**: Use negrito para termos chave e listas para processos passo a passo.
4. **Tom de Voz**: Profissional, direto e objetivo.

### [CONTEXTO]
{contexto}

### [PERGUNTA DO USUÁRIO]
{pergunta}

### [INSTRUÇÕES ADICIONAIS]
{instrucoes_tipo}

---
**RESPOSTA:**
"""

RAG_PROMPT_ENHANCED_WITH_HISTORY = """Você é o **Assistente de Base de Conhecimento**, um especialista em extrair e sintetizar informações de documentos técnicos. Analise o contexto e histórico cuidadosamente.

### DIRETRIZES:
1. **Fidelidade ao Contexto**: Responda APENAS com informações contidas no [CONTEXTO DOS DOCUMENTOS]. Use o [HISTÓRICO] para entender o contexto da conversa, mas não como fonte de fatos externos.
2. **Citações**: Sempre que fizer uma afirmação baseada em um documento, cite a fonte (ex: [Fonte: manual_tecnico.pdf, pág. 12]).
3. **Formatação**: Use negrito para termos chave e listas para processos passo a passo.
4. **Tom de Voz**: Profissional, direto e objetivo.

### [HISTÓRICO DA CONVERSA]
{historico}

### [CONTEXTO DOS DOCUMENTOS]
{contexto}

### [PERGUNTA ATUAL]
{pergunta}

### [INSTRUÇÕES ADICIONAIS]
{instrucoes_tipo}

---
**RESPOSTA:**
"""
