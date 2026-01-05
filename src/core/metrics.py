"""
Módulo de métricas com Prometheus para observabilidade do sistema RAG.

Fornece histogramas de latência, contadores e gauges para monitorar:
- Latência por fase do pipeline (embedding, search, rerank, llm, compression)
- Taxa de cache hit/miss de embeddings
- Sessões de chat ativas
- Queries processadas
- Erros e timeouts
"""
import time
from functools import wraps
from typing import Callable, Any


print(__name__)

# Flag para indicar se prometheus está disponível
PROMETHEUS_AVAILABLE = False

try:
    from prometheus_client import (
        Histogram, 
        Counter, 
        Gauge, 
        Summary,
        generate_latest,
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        REGISTRY
    )
    PROMETHEUS_AVAILABLE = True
    print("prometheus-client disponível para métricas")
except ImportError:
    print(
        "prometheus-client não instalado. "
        "Métricas desabilitadas. "
        "Instale com: pip install prometheus-client"
    )


# =============================================================================
# Definição das Métricas (apenas se prometheus disponível)
# =============================================================================

if PROMETHEUS_AVAILABLE:
    # Latência por fase do pipeline RAG
    RAG_LATENCY = Histogram(
        'rag_pipeline_duration_seconds',
        'Tempo de execução de cada fase do pipeline RAG',
        ['phase'],  # embedding, search, rerank, llm, compression, total
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
    )
    
    # Contador de queries
    RAG_QUERIES_TOTAL = Counter(
        'rag_queries_total',
        'Número total de queries processadas',
        ['status', 'question_type']  # status: success, no_results, error
    )
    
    # Chunks recuperados por query
    RAG_CHUNKS_RETRIEVED = Histogram(
        'rag_chunks_retrieved',
        'Número de chunks recuperados por query',
        buckets=(0, 1, 2, 3, 5, 7, 10, 15, 20, 30)
    )
    
    # Cache de embeddings
    EMBEDDING_CACHE_OPERATIONS = Counter(
        'embedding_cache_operations_total',
        'Operações no cache de embeddings',
        ['operation']  # hit, miss, set, evict
    )
    
    EMBEDDING_CACHE_SIZE = Gauge(
        'embedding_cache_size',
        'Número atual de embeddings em cache'
    )
    
    # Sessões de chat
    CHAT_SESSIONS_ACTIVE = Gauge(
        'chat_sessions_active',
        'Número de sessões de chat ativas'
    )
    
    # Compressão de contexto
    CONTEXT_COMPRESSION_RATIO = Summary(
        'context_compression_ratio',
        'Razão de compressão do contexto (1 - compressed/original)'
    )
    
    # Erros
    RAG_ERRORS = Counter(
        'rag_errors_total',
        'Erros no pipeline RAG',
        ['error_type']  # embedding_error, search_error, llm_error, timeout
    )
    
    # Ingestão de documentos
    INGESTION_DOCUMENTS = Counter(
        'ingestion_documents_total',
        'Documentos processados na ingestão',
        ['status']  # success, failed
    )
    
    INGESTION_CHUNKS = Counter(
        'ingestion_chunks_total',
        'Chunks criados na ingestão'
    )
    
    INGESTION_DURATION = Histogram(
        'ingestion_duration_seconds',
        'Tempo de ingestão por documento',
        buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
    )


# =============================================================================
# Helpers e Decorators
# =============================================================================

def measure_latency(phase: str):
    """
    Decorator para medir latência de uma fase do pipeline.
    
    Uso:
        @measure_latency('embedding')
        def get_embedding(text):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if PROMETHEUS_AVAILABLE:
                with RAG_LATENCY.labels(phase=phase).time():
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


class LatencyTracker:
    """
    Context manager para medir latência de blocos de código.
    
    Uso:
        with LatencyTracker('search'):
            results = search_similar(...)
    """
    
    def __init__(self, phase: str):
        self.phase = phase
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.perf_counter() - self.start_time
        if PROMETHEUS_AVAILABLE:
            RAG_LATENCY.labels(phase=self.phase).observe(self.duration)
        return False  # Não suprime exceções


# =============================================================================
# Funções de Incremento de Métricas
# =============================================================================

def inc_query(status: str = "success", question_type: str = "unknown"):
    """Incrementa contador de queries."""
    if PROMETHEUS_AVAILABLE:
        RAG_QUERIES_TOTAL.labels(status=status, question_type=question_type).inc()


def observe_chunks_retrieved(count: int):
    """Registra número de chunks recuperados."""
    if PROMETHEUS_AVAILABLE:
        RAG_CHUNKS_RETRIEVED.observe(count)


def inc_cache_hit():
    """Incrementa contador de cache hit."""
    if PROMETHEUS_AVAILABLE:
        EMBEDDING_CACHE_OPERATIONS.labels(operation='hit').inc()


def inc_cache_miss():
    """Incrementa contador de cache miss."""
    if PROMETHEUS_AVAILABLE:
        EMBEDDING_CACHE_OPERATIONS.labels(operation='miss').inc()


def inc_cache_set():
    """Incrementa contador de cache set."""
    if PROMETHEUS_AVAILABLE:
        EMBEDDING_CACHE_OPERATIONS.labels(operation='set').inc()


def inc_cache_evict():
    """Incrementa contador de cache eviction."""
    if PROMETHEUS_AVAILABLE:
        EMBEDDING_CACHE_OPERATIONS.labels(operation='evict').inc()


def set_cache_size(size: int):
    """Atualiza gauge do tamanho do cache."""
    if PROMETHEUS_AVAILABLE:
        EMBEDDING_CACHE_SIZE.set(size)


def set_active_sessions(count: int):
    """Atualiza gauge de sessões ativas."""
    if PROMETHEUS_AVAILABLE:
        CHAT_SESSIONS_ACTIVE.set(count)


def observe_compression_ratio(ratio: float):
    """Registra razão de compressão."""
    if PROMETHEUS_AVAILABLE:
        CONTEXT_COMPRESSION_RATIO.observe(ratio)


def inc_error(error_type: str):
    """Incrementa contador de erros."""
    if PROMETHEUS_AVAILABLE:
        RAG_ERRORS.labels(error_type=error_type).inc()


def inc_ingestion_document(status: str = "success"):
    """Incrementa contador de documentos ingeridos."""
    if PROMETHEUS_AVAILABLE:
        INGESTION_DOCUMENTS.labels(status=status).inc()


def inc_ingestion_chunks(count: int = 1):
    """Incrementa contador de chunks criados."""
    if PROMETHEUS_AVAILABLE:
        INGESTION_CHUNKS.inc(count)


def observe_ingestion_duration(duration: float):
    """Registra tempo de ingestão."""
    if PROMETHEUS_AVAILABLE:
        INGESTION_DURATION.observe(duration)


# =============================================================================
# Endpoint de Métricas
# =============================================================================

def get_metrics():
    """
    Retorna métricas no formato Prometheus.
    
    Returns:
        Tupla (content, content_type) para resposta HTTP
    """
    if PROMETHEUS_AVAILABLE:
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
    else:
        return b"# Prometheus metrics not available\n", "text/plain"


def check_metrics_available() -> dict:
    """
    Verifica status do módulo de métricas.
    
    Returns:
        Dict com status das métricas
    """
    return {
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "metrics_enabled": PROMETHEUS_AVAILABLE
    }
