"""
Sistema de logging centralizado para o RAG.
Registra interações com LLM, banco de dados e API.
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from functools import wraps
import time

from src.config import BASE_DIR


# =============================================================================
# Configuração de Diretórios de Logs
# =============================================================================
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# =============================================================================
# Formatters Customizados
# =============================================================================
class SimpleFormatter(logging.Formatter):
    """Formatter simples que gera logs em formato de texto legível."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().isoformat()
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()
        
        # Adicionar dados extras se existirem
        if hasattr(record, "extra_data"):
            extra_data_str = json.dumps(record.extra_data, ensure_ascii=False, default=str)
            return f"{timestamp} {level} {logger_name} {message} {extra_data_str}"
        
        return f"{timestamp} {level} {logger_name} {message}"


class DetailedFormatter(logging.Formatter):
    """Formatter detalhado para console."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Cores para diferentes níveis
        colors = {
            "DEBUG": "\033[36m",     # Cyan
            "INFO": "\033[32m",      # Green
            "WARNING": "\033[33m",   # Yellow
            "ERROR": "\033[31m",     # Red
            "CRITICAL": "\033[35m",  # Magenta
        }
        reset = "\033[0m"
        
        color = colors.get(record.levelname, "")
        
        formatted = (
            f"{color}[{datetime.now().strftime('%H:%M:%S')}] "
            f"{record.levelname:8}{reset} | "
            f"{record.name:20} | {record.getMessage()}"
        )
        
        return formatted


# =============================================================================
# Configuração dos Loggers
# =============================================================================
def setup_logger(
    name: str,
    level: int = logging.DEBUG,
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_file: str = "server.log"
) -> logging.Logger:
    """
    Configura e retorna um logger.
    
    Args:
        name: Nome do logger
        level: Nível de log
        log_to_file: Se deve salvar em arquivo
        log_to_console: Se deve exibir no console
        log_file: Nome do arquivo de log (padrão: server.log para backend)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    
    # Evitar handlers duplicados
    if logger.handlers:
        # Verifica se algum handler já usa o novo formato
        has_simple_formatter = any(
            isinstance(h.formatter, SimpleFormatter) 
            for h in logger.handlers
        )
        if has_simple_formatter:
            return logger  # Já está configurado corretamente
        # Caso contrário, remove handlers antigos e reconfigura
        logger.handlers.clear()
    
    # Handler para arquivo (texto simples) - consolidado em um único arquivo
    if log_to_file:
        file_handler = logging.FileHandler(
            LOGS_DIR / log_file,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(SimpleFormatter())
        logger.addHandler(file_handler)
    
    # Handler para console
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(DetailedFormatter())
        logger.addHandler(console_handler)
    
    return logger


# =============================================================================
# Loggers Específicos - Backend (todos usam server.log)
# =============================================================================
# Logger genérico
logger = setup_logger("rag", log_file="server.log")

# Logger para interações com LLM
llm_logger = setup_logger("rag.llm", log_file="server.log")

# Logger para banco de dados
db_logger = setup_logger("rag.database", log_file="server.log")

# Logger para embeddings
embedding_logger = setup_logger("rag.embeddings", log_file="server.log")

# Logger para API
api_logger = setup_logger("rag.api", log_file="server.log")

# Logger para pipeline RAG
rag_logger = setup_logger("rag.pipeline", log_file="server.log")

# Logger para ingestão
ingestion_logger = setup_logger("rag.ingestion", log_file="server.log")

# Logger para segurança (incluindo rate limiting)
security_logger = setup_logger("rag.security", log_file="server.log")

# Logger para webserver (logs recebidos do frontend)
webserver_logger = setup_logger("webserver", log_file="webserver.log")


# =============================================================================
# Funções de Log Especializadas
# =============================================================================
def log_with_data(logger: logging.Logger, level: int, message: str, data: dict):
    """Loga uma mensagem com dados extras estruturados."""
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None
    )
    record.extra_data = data
    logger.handle(record)


def log_api_input(endpoint: str, method: str, body: dict):
    """Loga o input completo recebido na API."""
    log_with_data(api_logger, logging.INFO, "API Input Received", {
        "endpoint": endpoint,
        "method": method,
        "body": body  # Corpo completo da requisição
    })


def log_llm_request(prompt: str, model: str, params: dict):
    """Loga uma requisição para o LLM."""
    log_with_data(llm_logger, logging.INFO, "LLM Request", {
        "model": model,
        "prompt_length": len(prompt),
        "prompt_full": prompt,  # Prompt completo enviado ao LLM
        "parameters": params
    })


def log_llm_response(response: str, duration: float, tokens: Optional[int] = None):
    """Loga uma resposta do LLM."""
    log_with_data(llm_logger, logging.INFO, "LLM Response", {
        "response_length": len(response),
        "response_full": response,  # Resposta completa do LLM
        "duration_seconds": round(duration, 3),
        "tokens": tokens
    })


def log_llm_full_request(url: str, payload: dict):
    """Loga a requisição completa enviada ao LLM (URL + payload JSON)."""
    log_with_data(llm_logger, logging.INFO, "LLM Full Request", {
        "url": url,
        "payload": payload  # Payload JSON completo enviado à API
    })


def log_llm_full_response(response_json: dict):
    """Loga a resposta completa recebida do LLM (JSON original)."""
    log_with_data(llm_logger, logging.INFO, "LLM Full Response", {
        "response_json": response_json  # JSON completo retornado pela API
    })


def log_db_query(operation: str, query: str, params: Optional[tuple] = None):
    """Loga uma query no banco de dados."""
    log_with_data(db_logger, logging.DEBUG, f"DB {operation}", {
        "query": query[:500],
        "params_count": len(params) if params else 0
    })


def log_db_result(operation: str, rows_affected: int, duration: float):
    """Loga o resultado de uma operação no banco."""
    log_with_data(db_logger, logging.INFO, f"DB {operation} Complete", {
        "rows_affected": rows_affected,
        "duration_seconds": round(duration, 3)
    })


def log_db_search_with_embedding(query_embedding: list, top_k: int):
    """Loga a busca no banco com o embedding usado."""
    log_with_data(db_logger, logging.INFO, "DB Vector Search", {
        "embedding_dimension": len(query_embedding),
        "embedding_sample": query_embedding[:10],  # Primeiros 10 valores do embedding
        "embedding_full": query_embedding,  # Embedding completo
        "top_k": top_k
    })


def log_db_search_results(results: list, duration: float):
    """Loga os resultados da busca no banco."""
    log_with_data(db_logger, logging.INFO, "DB Search Results", {
        "results_count": len(results),
        "results": [
            {
                "id": r.get("id"),
                "content_preview": r.get("content", "")[:200],
                "content_full": r.get("content"),
                "metadata": r.get("metadata"),
                "similarity": round(r.get("similarity", 0), 4)
            }
            for r in results
        ],
        "duration_seconds": round(duration, 3)
    })


def log_embedding_request(text: str, model: str):
    """Loga uma requisição de embedding com o texto."""
    log_with_data(embedding_logger, logging.INFO, "Embedding Request", {
        "text_length": len(text),
        "text": text,  # Texto completo para gerar embedding
        "model": model
    })


def log_embedding_response(embedding: list, duration: float):
    """Loga resposta de embedding com o vetor gerado."""
    log_with_data(embedding_logger, logging.INFO, "Embedding Response", {
        "dimension": len(embedding),
        "embedding_sample": embedding[:10],  # Primeiros 10 valores
        "embedding_full": embedding,  # Embedding completo
        "duration_seconds": round(duration, 3)
    })


def log_embedding_batch_request(texts_count: int, model: str):
    """Loga uma requisição de embeddings em batch."""
    log_with_data(embedding_logger, logging.INFO, "Embedding Batch Request", {
        "texts_count": texts_count,
        "model": model
    })


def log_embedding_batch_response(embeddings_count: int, duration: float, dimension: int):
    """Loga resposta de embeddings em batch."""
    log_with_data(embedding_logger, logging.INFO, "Embedding Batch Response", {
        "embeddings_count": embeddings_count,
        "dimension": dimension,
        "duration_seconds": round(duration, 3)
    })


def log_rag_query(question: str, top_k: int):
    """Loga uma query RAG."""
    log_with_data(rag_logger, logging.INFO, "RAG Query Started", {
        "question": question,
        "top_k": top_k
    })


def log_rag_context(context: str, sources: list):
    """Loga o contexto montado para o RAG."""
    log_with_data(rag_logger, logging.INFO, "RAG Context Built", {
        "context_length": len(context),
        "context_full": context,  # Contexto completo enviado ao LLM
        "sources": sources,
        "chunks_count": len(sources)
    })


def log_rag_result(chunks_found: int, sources: list, total_duration: float):
    """Loga o resultado de uma query RAG."""
    log_with_data(rag_logger, logging.INFO, "RAG Query Complete", {
        "chunks_found": chunks_found,
        "sources": sources,
        "total_duration_seconds": round(total_duration, 3)
    })


def log_ingestion_start(file_path: str, collection_id: str):
    """Loga o início da ingestão de um documento."""
    log_with_data(ingestion_logger, logging.INFO, "Ingestion Started", {
        "file_path": file_path,
        "collection_id": collection_id
    })


def log_ingestion_chunks(file_path: str, chunks_count: int, duration: float):
    """Loga a geração de chunks de um documento."""
    log_with_data(ingestion_logger, logging.INFO, "Chunks Generated", {
        "file_path": file_path,
        "chunks_count": chunks_count,
        "duration_seconds": round(duration, 3)
    })


def log_ingestion_complete(file_path: str, total_chunks: int, total_duration: float):
    """Loga a conclusão da ingestão de um documento."""
    log_with_data(ingestion_logger, logging.INFO, "Ingestion Complete", {
        "file_path": file_path,
        "total_chunks": total_chunks,
        "total_duration_seconds": round(total_duration, 3)
    })


def log_api_request(endpoint: str, method: str, body: Optional[dict] = None):
    """Loga uma requisição da API."""
    log_with_data(api_logger, logging.INFO, "API Request", {
        "endpoint": endpoint,
        "method": method,
        "body_preview": str(body)[:200] if body else None
    })


def log_api_response(endpoint: str, status_code: int, duration: float):
    """Loga uma resposta da API."""
    log_with_data(api_logger, logging.INFO, "API Response", {
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_seconds": round(duration, 3)
    })


def flush_loggers(*loggers: logging.Logger):
    """Force flush on file handlers to avoid buffered logs being lost."""
    for logger in loggers:
        for handler in logger.handlers:
            try:
                handler.flush()
            except Exception:
                # Ignore handlers that do not support flush
                pass


# =============================================================================
# Decorators para Logging Automático
# =============================================================================
def log_execution_time(logger: logging.Logger):
    """Decorator que loga o tempo de execução de uma função."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                logger.info(f"{func.__name__} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"{func.__name__} failed after {duration:.3f}s: {e}")
                raise
        return wrapper
    return decorator
