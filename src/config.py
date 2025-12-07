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
CHUNK_OVERLAP = 150  # Overlap entre chunks (usado no modo legado)

# Chunking Semântico (novo)
USE_SEMANTIC_CHUNKING = True  # Se True, usa chunking por sentenças
MIN_CHUNK_SIZE = 200  # Tamanho mínimo do chunk
CHUNK_OVERLAP_SENTENCES = 1  # Número de sentenças de overlap


# =============================================================================
# RAG
# =============================================================================
TOP_K_RESULTS = 10  # Número de chunks retornados na busca
MIN_SIMILARITY_THRESHOLD = 0.4  # Similaridade mínima para considerar um chunk relevante (0.0 a 1.0)


# =============================================================================
# Busca Híbrida (Vetorial + Full-Text Search)
# =============================================================================
ENABLE_HYBRID_SEARCH = True  # Se True, usa busca híbrida ao invés de apenas vetorial
HYBRID_SEARCH_ALPHA = 0.7  # Peso da busca vetorial (0.0 a 1.0). 0.7 = 70% vetorial, 30% FTS


# =============================================================================
# Compressão de Contexto
# =============================================================================
ENABLE_CONTEXT_COMPRESSION = True  # Se True, comprime contexto quando muito grande
CONTEXT_COMPRESSION_THRESHOLD = 3000  # Caracteres acima dos quais ativar compressão
CONTEXT_COMPRESSION_TARGET_RATIO = 0.5  # Proporção alvo (0.5 = reduzir pela metade)
CONTEXT_COMPRESSION_METHOD = "llm"  # "llm" (mais preciso) ou "heuristic" (mais rápido)


# =============================================================================
# Conversação
# =============================================================================
SESSION_TIMEOUT_MINUTES = 30  # Tempo para expirar sessões inativas
MAX_CONVERSATION_HISTORY = 10  # Máximo de mensagens no histórico


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


# Template com histórico de conversa
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


# =============================================================================
# Prompt Template Melhorado (Phase 1)
# =============================================================================
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


# Template com histórico melhorado
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


# =============================================================================
# Configurações de Cache (Phase 1)
# =============================================================================
EMBEDDING_CACHE_ENABLED = True  # Habilita cache de embeddings
EMBEDDING_CACHE_MAX_SIZE = 1000  # Máximo de embeddings em cache


# =============================================================================
# Configurações do Classificador de Perguntas (Phase 1)
# =============================================================================
USE_QUESTION_CLASSIFIER = True  # Habilita classificação de perguntas
USE_ENHANCED_PROMPTS = True  # Usa prompts melhorados com instruções por tipo


# =============================================================================
# Configurações Phase 2 - Re-ranking
# =============================================================================
ENABLE_RERANKING = True  # Habilita re-ranking com cross-encoder
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Modelo do HuggingFace
RERANKING_TOP_K_INITIAL = 15  # Buscar mais chunks para depois filtrar com reranker


# =============================================================================
# Configurações Phase 2 - Query Expansion
# =============================================================================
ENABLE_QUERY_EXPANSION = True  # Habilita expansão de queries
QUERY_EXPANSION_COUNT = 3  # Número de variações a gerar


# =============================================================================
# Configurações Phase 2 - MMR (Diversidade)
# =============================================================================
ENABLE_MMR = True  # Habilita MMR para diversificação
MMR_LAMBDA = 0.7  # Balanço: 0.7 = 70% relevância, 30% diversidade


# =============================================================================
# Configurações Phase 3 - HyDE (Hypothetical Document Embeddings)
# =============================================================================
ENABLE_HYDE = True  # Habilita HyDE
HYDE_WEIGHT = 0.5   # Peso do embedding HyDE (0=só original, 1=só HyDE)


# =============================================================================
# Configurações Phase 3 - Contextual Chunking
# =============================================================================
ENABLE_CONTEXTUAL_METADATA = True  # Adiciona metadados contextuais aos chunks
CONTEXTUAL_NEIGHBOR_SUMMARIES = True  # Resumos dos chunks vizinhos
CONTEXTUAL_SECTION_DETECTION = True  # Detecção de títulos de seção


# =============================================================================
# Configurações Phase 3 - Hierarchical Chunking
# =============================================================================
ENABLE_HIERARCHICAL_CHUNKING = False  # Requer re-ingestão de documentos
PARENT_CHUNK_SIZE = 2000  # Tamanho dos chunks pais
CHILD_CHUNK_SIZE = 400    # Tamanho dos chunks filhos
CHILD_CHUNK_OVERLAP = 50  # Overlap entre filhos


# =============================================================================
# Configurações Phase 3 - Avaliação RAGAS
# =============================================================================
ENABLE_AUTO_EVALUATION = False  # Avaliar automaticamente respostas (lento)


# =============================================================================
# Configurações Phase 4 - Adaptive Retrieval
# =============================================================================
ENABLE_ADAPTIVE_RETRIEVAL = True  # Ajusta top_k/min_similarity dinamicamente


# =============================================================================
# Configurações Phase 4 - Self-RAG
# =============================================================================
ENABLE_SELF_RAG = False  # Avalia e refina respostas (lento, +1 chamada LLM)
SELF_RAG_MIN_SCORE = 60  # Score mínimo para considerar resposta completa


# =============================================================================
# Configurações Phase 4 - Sentence Window
# =============================================================================
ENABLE_SENTENCE_WINDOW = False  # Requer docs indexados por sentença
SENTENCE_WINDOW_SIZE = 2  # Sentenças antes/depois da encontrada
