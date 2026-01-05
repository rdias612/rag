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
from src.api.middleware.rate_limiter import limiter, LIMITS

print("rag.api")

health_bp = Blueprint("health", __name__)

# Instância do repository
_doc_repo = DocumentRepository()


@health_bp.route("/health", methods=["GET"])
@limiter.limit(LIMITS["health"])
def health_check():
    """Endpoint de health check."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", "/api/health", "GET")
    
    db_ok = check_connection()
    status_code = 200 if db_ok else 503
    
    print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                   "/api/health", status_code, time.time() - start_time)
    
    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected"
    }), status_code


@health_bp.route("/stats", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_stats():
    """Retorna estatísticas do sistema."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", "/api/stats", "GET")
    
    try:
        doc_count = _doc_repo.count()
        
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/stats", 200, time.time() - start_time)
        
        return jsonify({
            "documents_count": doc_count,
            "status": "ok"
        })
    except Exception as e:
        print("Error in /stats: %s", e)
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@health_bp.route("/collections", methods=["GET"])
def get_collections():
    """Lista todas as coleções disponíveis."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", "/api/collections", "GET")
    
    try:
        collections = _doc_repo.list_collections()
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/collections", 200, time.time() - start_time)
        return jsonify({"collections": collections})
    except Exception as e:
        print("Error in /collections: %s", e)
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/collections", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
