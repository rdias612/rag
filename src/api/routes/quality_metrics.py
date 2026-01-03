"""Blueprint para métricas de qualidade de respostas RAG."""
import logging
import time
from flask import Blueprint, jsonify, request

from src.data.repositories import evaluation_repo
from src.core.evaluation import evaluate_rag_response
from src.api.middleware.rate_limiter import limiter, LIMITS
from src.config import ENABLE_AUTO_EVALUATION

api_logger = logging.getLogger("rag.api")

quality_bp = Blueprint("quality_metrics", __name__)


@quality_bp.route("/stats", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_quality_stats():
    """
    Retorna estatísticas agregadas de qualidade.
    
    Query Params:
        - days: Número de dias para filtrar (default: 7)
        
    Returns:
        Dict com médias, min, max, median das métricas
    """
    start_time = time.time()
    days = request.args.get('days', 7, type=int)
    
    try:
        stats = evaluation_repo.get_stats(days=days)
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/stats", 200, time.time() - start_time)
        return jsonify(stats)
        
    except Exception as e:
        api_logger.exception("Error getting quality stats: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/recent", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_recent_evaluations():
    """
    Retorna avaliações recentes.
    
    Query Params:
        - limit: Número máximo de registros (default: 50)
        - min_score: Score mínimo para filtrar (opcional)
        
    Returns:
        Lista de avaliações recentes
    """
    start_time = time.time()
    limit = request.args.get('limit', 50, type=int)
    min_score = request.args.get('min_score', type=float)
    
    try:
        evaluations = evaluation_repo.get_recent_evaluations(limit, min_score)
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/recent", 200, time.time() - start_time)
        return jsonify({"evaluations": evaluations})
        
    except Exception as e:
        api_logger.exception("Error getting recent evaluations: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/recent", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/trends", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_quality_trends():
    """
    Retorna tendência temporal de qualidade.
    
    Query Params:
        - days: Número de dias para analisar (default: 30)
        - group_by: 'day' ou 'week' (default: 'day')
        
    Returns:
        Lista de pontos temporais com métricas
    """
    start_time = time.time()
    days = request.args.get('days', 30, type=int)
    group_by = request.args.get('group_by', 'day', type=str)
    
    try:
        trends = evaluation_repo.get_trends(days, group_by)
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/trends", 200, time.time() - start_time)
        return jsonify({"trends": trends})
        
    except Exception as e:
        api_logger.exception("Error getting quality trends: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/trends", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/top-worst", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_top_worst():
    """
    Retorna as melhores e piores queries.
    
    Query Params:
        - limit: Número de registros (default: 5)
        - days: Período em dias (default: 7)
        
    Returns:
        Dict com 'best' e 'worst' queries
    """
    start_time = time.time()
    limit = request.args.get('limit', 5, type=int)
    days = request.args.get('days', 7, type=int)
    
    try:
        top_worst = evaluation_repo.get_top_worst_queries(limit, days)
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/top-worst", 200, time.time() - start_time)
        return jsonify(top_worst)
        
    except Exception as e:
        api_logger.exception("Error getting top/worst queries: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/top-worst", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/evaluate", methods=["POST"])
@limiter.limit(LIMITS["query"])
def evaluate_response_endpoint():
    """
    Avalia uma resposta sob demanda.
    
    Body:
        - question: Pergunta original
        - answer: Resposta gerada
        - context: Contexto usado
        - chunks: Chunks recuperados (opcional)
        
    Returns:
        Dict com scores da avaliação
    """
    start_time = time.time()
    data = request.get_json() or {}
    
    # Validar campos obrigatórios
    required_fields = ['question', 'answer', 'context']
    for field in required_fields:
        if field not in data:
            api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                           "/api/metrics/quality/evaluate", 400, time.time() - start_time)
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        # Avaliar
        result = evaluate_rag_response(
            question=data['question'],
            answer=data['answer'],
            context=data['context'],
            chunks=data.get('chunks')
        )
        
        # Salvar se habilitado
        if ENABLE_AUTO_EVALUATION:
            evaluation_repo.save_evaluation(
                question=data['question'],
                answer=data['answer'],
                context=data['context'],
                scores=result,
                user_id=data.get('user_id'),
                chunks_retrieved=len(data.get('chunks', []))
            )
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/evaluate", 200, time.time() - start_time)
        return jsonify(result)
        
    except Exception as e:
        api_logger.exception("Error evaluating response: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/metrics/quality/evaluate", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
