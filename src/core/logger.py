"""
Módulo de compatibilidade para logging.

Este módulo fornece funções de compatibilidade para facilitar
a migração do sistema de logging customizado para o padrão do Python.
"""
import logging
import uuid


# =============================================================================
# Loggers Especializados (Compatibilidade)
# =============================================================================
def get_logger(name: str) -> logging.Logger:
    """
    Retorna um logger configurado para o módulo especificado.
    
    Args:
        name: Nome do logger (ex: "rag.llm", "rag.api")
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


# Loggers específicos para compatibilidade
logger = get_logger("rag")
llm_logger = get_logger("rag.llm")
db_logger = get_logger("rag.database")
embedding_logger = get_logger("rag.embeddings")
api_logger = get_logger("rag.api")
rag_logger = get_logger("rag.pipeline")
ingestion_logger = get_logger("rag.ingestion")
security_logger = get_logger("rag.security")
webserver_logger = get_logger("webserver")


# =============================================================================
# Funções de Compatibilidade (Deprecated)
# =============================================================================
def generate_request_id() -> str:
    """
    Gera um request ID único para rastrear uma requisição.
    
    Returns:
        String única representando o request ID
    """
    return str(uuid.uuid4())[:8]


def log_step(logger_instance: logging.Logger, step_name: str, **data):
    """
    Loga um passo específico do fluxo com dados estruturados.
    
    Args:
        logger_instance: Logger a ser usado
        step_name: Nome do passo
        **data: Dados adicionais para o log
    """
    request_id = data.get("request_id", "unknown")
    data_str = " | ".join(f"{k}={v}" for k, v in data.items() if k != "request_id")
    logger_instance.info("[%s] | request_id=%s | %s", step_name, request_id, data_str)


def log_error(logger_instance: logging.Logger, component: str, error: Exception, **context):
    """
    Loga erro com contexto completo.
    
    Args:
        logger_instance: Logger a ser usado
        component: Nome do componente que falhou
        error: Exceção capturada
        **context: Contexto adicional
    """
    request_id = context.get("request_id", "unknown")
    logger_instance.exception(
        "[%s] Error | request_id=%s | error_type=%s | error_message=%s | context=%s",
        component, request_id, type(error).__name__, str(error), context
    )


def log_stage(stage_name: str, logger_instance: logging.Logger, **context):
    """
    Loga início de uma etapa do pipeline com contexto.
    
    Args:
        stage_name: Nome da etapa
        logger_instance: Logger a ser usado
        **context: Contexto adicional
    """
    request_id = context.get("request_id", "unknown")
    logger_instance.info("[%s] Started | request_id=%s", stage_name, request_id)
    
    # Retorna um context manager para uso com 'with'
    from contextlib import contextmanager
    
    @contextmanager
    def _stage_context():
        logger_instance.info("[%s] Started | request_id=%s", stage_name, request_id)
        yield
        logger_instance.info("[%s] Completed | request_id=%s", stage_name, request_id)
    
    return _stage_context()


# =============================================================================
# Funções Deprecated (mantidas para compatibilidade temporária)
# =============================================================================
def log_with_data(logger_instance: logging.Logger, level: int, message: str, data: dict):
    """Deprecated: Use logger.info() com lazy formatting."""
    data_str = " | ".join(f"{k}={v}" for k, v in data.items())
    logger_instance.log(level, "%s | %s", message, data_str)


def log_llm_request(prompt: str, model: str, params: dict):
    """Deprecated: Use llm_logger.info() com lazy formatting."""
    llm_logger.info("LLM Request | model=%s | prompt_len=%d | params=%s",
                    model, len(prompt), params)


def log_llm_response(response: str, duration: float, tokens: int = None):
    """Deprecated: Use llm_logger.info() com lazy formatting."""
    llm_logger.info("LLM Response | response_len=%d | duration=%.3fs | tokens=%s",
                    len(response), duration, tokens)


def log_llm_full_request(url: str, payload: dict):
    """Deprecated: Use llm_logger.debug() com lazy formatting."""
    llm_logger.debug("LLM Full Request | url=%s | payload=%s", url, payload)


def log_llm_full_response(response_json: dict):
    """Deprecated: Use llm_logger.debug() com lazy formatting."""
    llm_logger.debug("LLM Full Response | response=%s", response_json)


def log_db_query(operation: str, query: str, params: tuple = None):
    """Deprecated: Use db_logger.debug() com lazy formatting."""
    db_logger.debug("DB %s | query=%s | params_count=%d",
                    operation, query[:500], len(params) if params else 0)


def log_db_result(operation: str, rows_affected: int, duration: float):
    """Deprecated: Use db_logger.info() com lazy formatting."""
    db_logger.info("DB %s Complete | rows=%d | duration=%.3fs",
                    operation, rows_affected, duration)


def log_db_search_with_embedding(query_embedding: list, top_k: int):
    """Deprecated: Use db_logger.info() com lazy formatting."""
    db_logger.info("DB Vector Search | embedding_dim=%d | embedding_sample=%s | top_k=%d",
                    len(query_embedding), query_embedding[:10], top_k)


def log_db_search_results(results: list, duration: float):
    """Deprecated: Use db_logger.info() com lazy formatting."""
    db_logger.info("DB Search Results | results_count=%d | duration=%.3fs",
                    len(results), duration)


def log_embedding_request(text: str, model: str):
    """Deprecated: Use embedding_logger.info() com lazy formatting."""
    embedding_logger.info("Embedding Request | model=%s | text_len=%d",
                         model, len(text))


def log_embedding_response(embedding: list, duration: float):
    """Deprecated: Use embedding_logger.info() com lazy formatting."""
    embedding_logger.info("Embedding Response | dim=%d | duration=%.3fs",
                         len(embedding), duration)


def log_embedding_batch_request(texts_count: int, model: str):
    """Deprecated: Use embedding_logger.info() com lazy formatting."""
    embedding_logger.info("Embedding Batch Request | model=%s | texts_count=%d",
                         model, texts_count)


def log_embedding_batch_response(embeddings_count: int, duration: float, dimension: int):
    """Deprecated: Use embedding_logger.info() com lazy formatting."""
    embedding_logger.info("Embedding Batch Response | count=%d | duration=%.3fs | dim=%d",
                         embeddings_count, duration, dimension)


def log_rag_query(question: str, top_k: int):
    """Deprecated: Use rag_logger.info() com lazy formatting."""
    rag_logger.info("RAG Query | question=%s | top_k=%d", question, top_k)


def log_rag_context(context: str, sources: list):
    """Deprecated: Use rag_logger.info() com lazy formatting."""
    rag_logger.info("RAG Context | context_len=%d | sources_count=%d",
                    len(context), len(sources))


def log_rag_result(chunks_found: int, sources: list, total_duration: float):
    """Deprecated: Use rag_logger.info() com lazy formatting."""
    rag_logger.info("RAG Query Complete | chunks=%d | duration=%.3fs",
                    chunks_found, total_duration)


def log_ingestion_start(file_path: str, collection_id: str):
    """Deprecated: Use ingestion_logger.info() com lazy formatting."""
    ingestion_logger.info("Ingestion Started | file=%s | collection=%s",
                         file_path, collection_id)


def log_ingestion_chunks(file_path: str, chunks_count: int, duration: float):
    """Deprecated: Use ingestion_logger.info() com lazy formatting."""
    ingestion_logger.info("Chunks Generated | file=%s | chunks=%d | duration=%.3fs",
                         file_path, chunks_count, duration)


def log_ingestion_complete(file_path: str, total_chunks: int, total_duration: float):
    """Deprecated: Use ingestion_logger.info() com lazy formatting."""
    ingestion_logger.info("Ingestion Complete | file=%s | chunks=%d | duration=%.3fs",
                         file_path, total_chunks, total_duration)


def log_api_request(endpoint: str, method: str, body: dict = None):
    """Deprecated: Use api_logger.info() com lazy formatting."""
    api_logger.info("API Request | endpoint=%s | method=%s | body=%s",
                    endpoint, method, body)


def log_api_response(endpoint: str, status_code: int, duration: float):
    """Deprecated: Use api_logger.info() com lazy formatting."""
    api_logger.info("API Response | endpoint=%s | status=%d | duration=%.3fs",
                    endpoint, status_code, duration)


def log_api_input(endpoint: str, method: str, body: dict):
    """Deprecated: Use api_logger.info() com lazy formatting."""
    api_logger.info("API Input Received | endpoint=%s | method=%s | body=%s",
                    endpoint, method, body)


def flush_loggers(*logger_instances: logging.Logger):
    """
    No-op para compatibilidade.
    
    O sistema de logging padrão do Python já gerencia flush
    automaticamente. Esta função é mantida apenas para compatibilidade.
    """
    pass
