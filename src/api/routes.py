"""
Rotas da API Flask.
"""
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context

from src.core.rag import query_rag, query_rag_stream, search_only
from src.data.database import get_document_count, check_connection
from src.core.logger import (
    api_logger,
    log_api_request,
    log_api_response
)

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health_check():
    """Endpoint de health check."""
    start_time = time.time()
    log_api_request("/api/health", "GET")
    
    db_ok = check_connection()
    status_code = 200 if db_ok else 503
    
    log_api_response("/api/health", status_code, time.time() - start_time)
    
    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected"
    }), status_code


@api.route("/stats", methods=["GET"])
def get_stats():
    """Retorna estatísticas do sistema."""
    start_time = time.time()
    log_api_request("/api/stats", "GET")
    
    try:
        doc_count = get_document_count()
        
        log_api_response("/api/stats", 200, time.time() - start_time)
        
        return jsonify({
            "documents_count": doc_count,
            "status": "ok"
        })
    except Exception as e:
        api_logger.error(f"Error in /stats: {e}")
        log_api_response("/api/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/query", methods=["POST"])
def query():
    """
    Endpoint principal do RAG.
    
    Body:
        {
            "question": "Sua pergunta aqui",
            "top_k": 5,  // opcional
            "temperature": 0.7,  // opcional
            "include_sources": true  // opcional
        }
    """
    start_time = time.time()
    data = request.get_json()
    
    log_api_request("/api/query", "POST", data)
    
    if not data or "question" not in data:
        api_logger.warning("Query request missing 'question' field")
        log_api_response("/api/query", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    question = data["question"]
    top_k = data.get("top_k", 5)
    temperature = data.get("temperature", 0.7)
    include_sources = data.get("include_sources", True)
    
    try:
        result = query_rag(
            question=question,
            top_k=top_k,
            temperature=temperature,
            include_sources=include_sources
        )
        
        log_api_response("/api/query", 200, time.time() - start_time)
        
        return jsonify(result)
    
    except Exception as e:
        api_logger.error(f"Error in /query: {e}")
        log_api_response("/api/query", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/query/stream", methods=["POST"])
def query_stream():
    """
    Endpoint RAG com streaming.
    
    Body:
        {
            "question": "Sua pergunta aqui",
            "top_k": 5,
            "temperature": 0.7
        }
    """
    data = request.get_json()
    
    log_api_request("/api/query/stream", "POST", data)
    
    if not data or "question" not in data:
        api_logger.warning("Stream query request missing 'question' field")
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    question = data["question"]
    top_k = data.get("top_k", 5)
    temperature = data.get("temperature", 0.7)
    
    def generate():
        try:
            for token in query_rag_stream(question, top_k, temperature):
                yield token
            api_logger.info("Stream query completed successfully")
        except Exception as e:
            api_logger.error(f"Error in stream query: {e}")
            yield f"\n\n[Erro: {str(e)}]"
    
    return Response(
        stream_with_context(generate()),
        mimetype="text/plain",
        headers={"X-Accel-Buffering": "no"}
    )


@api.route("/search", methods=["POST"])
def search():
    """
    Apenas busca documentos similares, sem gerar resposta.
    Útil para debug.
    
    Body:
        {
            "question": "Sua query aqui",
            "top_k": 5
        }
    """
    start_time = time.time()
    data = request.get_json()
    
    log_api_request("/api/search", "POST", data)
    
    if not data or "question" not in data:
        api_logger.warning("Search request missing 'question' field")
        log_api_response("/api/search", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    question = data["question"]
    top_k = data.get("top_k", 5)
    
    try:
        results = search_only(question, top_k)
        
        log_api_response("/api/search", 200, time.time() - start_time)
        
        return jsonify({
            "results": results,
            "count": len(results)
        })
    
    except Exception as e:
        api_logger.error(f"Error in /search: {e}")
        log_api_response("/api/search", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
