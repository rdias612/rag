"""
Blueprint de saúde e estatísticas do sistema.

Endpoints:
- GET /health - Health check
- GET /stats - Estatísticas do sistema
- GET /collections - Lista coleções
"""
import time
from flask import Blueprint, jsonify

from src.data.database import check_connection
from src.data.repositories import DocumentRepository
from src.core.logger import api_logger, log_api_request, log_api_response

health_bp = Blueprint("health", __name__)

# Instância do repository
_doc_repo = DocumentRepository()


@health_bp.route("/health", methods=["GET"])
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


@health_bp.route("/stats", methods=["GET"])
def get_stats():
    """Retorna estatísticas do sistema."""
    start_time = time.time()
    log_api_request("/api/stats", "GET")
    
    try:
        doc_count = _doc_repo.count()
        
        log_api_response("/api/stats", 200, time.time() - start_time)
        
        return jsonify({
            "documents_count": doc_count,
            "status": "ok"
        })
    except Exception as e:
        api_logger.error(f"Error in /stats: {e}")
        log_api_response("/api/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@health_bp.route("/collections", methods=["GET"])
def get_collections():
    """Lista todas as coleções disponíveis."""
    start_time = time.time()
    log_api_request("/api/collections", "GET")
    
    try:
        collections = _doc_repo.list_collections()
        log_api_response("/api/collections", 200, time.time() - start_time)
        return jsonify({"collections": collections})
    except Exception as e:
        api_logger.error(f"Error in /collections: {e}")
        log_api_response("/api/collections", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
