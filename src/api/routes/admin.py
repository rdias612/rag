"""
Blueprint de endpoints administrativos.

Endpoints:
- GET /embeddings/advanced-stats - Stats do batch processor
- POST /embeddings/advanced-stats/reset - Reset stats
- GET /admin/pool-stats - Stats do connection pool
- POST /admin/pool-stats/reset - Reset pool stats
"""
import logging
import time
from flask import Blueprint, jsonify

from src.core.advanced_batch_processor import get_advanced_processor
from src.core.connection_pool import get_connection_pool
from src.config import ENABLE_ADVANCED_BATCH_PROCESSING, ENABLE_CONNECTION_POOL

api_logger = logging.getLogger("rag.api")

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/embeddings/advanced-stats", methods=["GET"])
def get_advanced_batch_processor_stats():
    """Retorna estatísticas do processador avançado de embeddings."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/embeddings/advanced-stats", "GET")
    
    try:
        processor = get_advanced_processor()
        stats = processor.get_stats()
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/embeddings/advanced-stats", 200, time.time() - start_time)
        
        return jsonify({
            "stats": stats,
            "enabled": ENABLE_ADVANCED_BATCH_PROCESSING
        })
        
    except Exception as e:
        api_logger.exception("Error in /api/embeddings/advanced-stats: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/embeddings/advanced-stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/embeddings/advanced-stats/reset", methods=["POST"])
def reset_advanced_batch_processor_stats():
    """Reseta as estatísticas do processador avançado."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/embeddings/advanced-stats/reset", "POST")
    
    try:
        processor = get_advanced_processor()
        processor.reset_stats()
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/embeddings/advanced-stats/reset", 200, time.time() - start_time)
        
        return jsonify({"message": "Estatísticas resetadas com sucesso"})
        
    except Exception as e:
        api_logger.exception("Error in /api/embeddings/advanced-stats/reset: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/embeddings/advanced-stats/reset", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/admin/pool-stats", methods=["GET"])
def get_connection_pool_stats():
    """Retorna estatísticas do pool de conexões."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/admin/pool-stats", "GET")
    
    try:
        pool = get_connection_pool()
        healthy = pool.health_check()
        stats = pool.get_stats()
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/admin/pool-stats", 200, time.time() - start_time)
        
        return jsonify({
            "healthy": healthy,
            "stats": stats,
            "enabled": ENABLE_CONNECTION_POOL
        })
        
    except Exception as e:
        api_logger.exception("Error in /api/admin/pool-stats: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/admin/pool-stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/admin/pool-stats/reset", methods=["POST"])
def reset_connection_pool_stats():
    """Reseta as estatísticas do pool de conexões."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/admin/pool-stats/reset", "POST")
    
    try:
        pool = get_connection_pool()
        pool.reset_stats()
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/admin/pool-stats/reset", 200, time.time() - start_time)
        
        return jsonify({"message": "Estatísticas do pool resetadas com sucesso"})
        
    except Exception as e:
        api_logger.exception("Error in /api/admin/pool-stats/reset: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/admin/pool-stats/reset", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
