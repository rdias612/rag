"""
Blueprint de métricas, cache, classificação e avaliação.

Endpoints:
- GET /cache/stats - Estatísticas do cache
- POST /cache/clear - Limpa cache
- POST /classify - Classifica pergunta
- POST /evaluate - Avalia resposta RAG
- POST /hyde/test - Testa HyDE
- GET /metrics - Métricas Prometheus
- GET /metrics/status - Status das métricas
"""
import time
from flask import Blueprint, request, jsonify, Response

from src.core.logger import api_logger, log_api_request, log_api_response, log_api_input

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Retorna estatísticas do cache de embeddings."""
    start_time = time.time()
    log_api_request("/api/cache/stats", "GET")
    
    try:
        from src.core.embedding_cache import get_cache_stats
        stats = get_cache_stats()
        
        log_api_response("/api/cache/stats", 200, time.time() - start_time)
        return jsonify(stats)
        
    except Exception as e:
        api_logger.error(f"Error in /cache/stats: {e}")
        log_api_response("/api/cache/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@metrics_bp.route("/cache/clear", methods=["POST"])
def cache_clear():
    """Limpa o cache de embeddings."""
    start_time = time.time()
    log_api_request("/api/cache/clear", "POST")
    
    try:
        from src.core.embedding_cache import clear_embedding_cache
        clear_embedding_cache()
        
        log_api_response("/api/cache/clear", 200, time.time() - start_time)
        return jsonify({"message": "Cache limpo com sucesso"})
        
    except Exception as e:
        api_logger.error(f"Error in /cache/clear: {e}")
        log_api_response("/api/cache/clear", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@metrics_bp.route("/classify", methods=["POST"])
def classify_question_endpoint():
    """Classifica uma pergunta em um tipo."""
    start_time = time.time()
    data = request.get_json()
    
    log_api_input("/api/classify", "POST", data)
    
    if not data or "question" not in data:
        log_api_response("/api/classify", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    try:
        from src.core.question_classifier import (
            classify_question,
            get_question_type_description
        )
        
        question = data["question"]
        question_type = classify_question(question)
        description = get_question_type_description(question_type)
        
        log_api_response("/api/classify", 200, time.time() - start_time)
        return jsonify({
            "question": question,
            "type": question_type,
            "description": description
        })
        
    except Exception as e:
        api_logger.error(f"Error in /classify: {e}")
        log_api_response("/api/classify", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@metrics_bp.route("/evaluate", methods=["POST"])
def evaluate_response():
    """Avalia qualidade de uma resposta RAG usando métricas RAGAS."""
    start_time = time.time()
    data = request.get_json()
    
    log_api_input("/api/evaluate", "POST", data)
    
    required = ["question", "answer", "context"]
    missing = [f for f in required if f not in data]
    if missing:
        log_api_response("/api/evaluate", 400, time.time() - start_time)
        return jsonify({"error": f"Campos obrigatórios: {', '.join(missing)}"}), 400
    
    try:
        from src.core.evaluation import evaluate_rag_response, get_evaluation_summary
        
        scores = evaluate_rag_response(
            question=data["question"],
            answer=data["answer"],
            context=data["context"],
            chunks=data.get("chunks")
        )
        
        scores["summary"] = get_evaluation_summary(scores)
        
        log_api_response("/api/evaluate", 200, time.time() - start_time)
        return jsonify(scores)
        
    except Exception as e:
        api_logger.error(f"Error in /evaluate: {e}")
        log_api_response("/api/evaluate", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@metrics_bp.route("/hyde/test", methods=["POST"])
def test_hyde():
    """Testa geração de documento hipotético (HyDE)."""
    start_time = time.time()
    data = request.get_json()
    
    log_api_input("/api/hyde/test", "POST", data)
    
    if not data or "question" not in data:
        log_api_response("/api/hyde/test", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    try:
        from src.core.hyde import generate_hypothetical_document
        
        question = data["question"]
        hypothetical_doc = generate_hypothetical_document(question)
        
        log_api_response("/api/hyde/test", 200, time.time() - start_time)
        return jsonify({
            "question": question,
            "hypothetical_document": hypothetical_doc
        })
        
    except Exception as e:
        api_logger.error(f"Error in /hyde/test: {e}")
        log_api_response("/api/hyde/test", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@metrics_bp.route("/metrics", methods=["GET"])
def metrics():
    """Endpoint de métricas Prometheus."""
    from src.core.metrics import get_metrics
    
    content, content_type = get_metrics()
    return Response(content, mimetype=content_type)


@metrics_bp.route("/metrics/status", methods=["GET"])
def metrics_status():
    """Verifica status do módulo de métricas."""
    start_time = time.time()
    log_api_request("/api/metrics/status", "GET")
    
    from src.core.metrics import check_metrics_available
    
    status = check_metrics_available()
    log_api_response("/api/metrics/status", 200, time.time() - start_time)
    
    return jsonify(status)
