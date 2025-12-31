"""
Blueprint de queries RAG.

Endpoints:
- POST /query - Query RAG principal
- POST /query/stream - Query com streaming
- POST /search - Apenas busca (sem LLM)
- POST /chat - Chat com histórico
"""
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context
from pydantic import ValidationError

from src.api.schemas import QueryRequest, ChatRequest, SearchRequest, StreamQueryRequest
from src.core.rag import query_rag, query_rag_stream, search_only, query_rag_with_history
from src.core.rag_explainer import explainer
from src.core.logger import api_logger, log_api_request, log_api_response, log_api_input
from src.api.middleware.rate_limiter import limiter, LIMITS

query_bp = Blueprint("query", __name__)


@query_bp.route("/query", methods=["POST"])
@limiter.limit(LIMITS["query"])
def query():
    """
    Endpoint principal do RAG.
    
    Body:
        {
            "question": "Sua pergunta aqui",
            "top_k": 5,
            "temperature": 0.7,
            "include_sources": true,
            "include_explanation": true,
            "collection": "nome_do_projeto"
        }
    """
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/query", "POST", data)
    
    try:
        req = QueryRequest(**data)
    except ValidationError as e:
        api_logger.warning(f"Query validation failed: {e.errors()}")
        log_api_response("/api/query", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        include_explanation = data.get("include_explanation", False)
        
        result = query_rag(
            question=req.question,
            top_k=req.top_k,
            temperature=req.temperature,
            include_sources=req.include_sources,
            collection_id=req.collection,
            response_style=req.response_style,
            debug_mode=req.debug or include_explanation,
            enable_adaptive=req.enable_adaptive,
            search_mode=req.search_mode
        )
        
        if include_explanation and "_debug" in result and "search" in result:
            result["explanation"] = explainer.explain_rag_pipeline(
                question=req.question,
                debug_info=result["_debug"],
                search_metrics=result["search"]
            )
            del result["_debug"]
        
        log_api_response("/api/query", 200, time.time() - start_time)
        return jsonify(result)
    
    except Exception as e:
        api_logger.error(f"Error in /query: {e}")
        log_api_response("/api/query", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@query_bp.route("/query/stream", methods=["POST"])
@limiter.limit(LIMITS["query"])
def query_stream():
    """Endpoint RAG com streaming."""
    data = request.get_json() or {}
    log_api_input("/api/query/stream", "POST", data)
    
    try:
        req = StreamQueryRequest(**data)
    except ValidationError as e:
        api_logger.warning(f"Stream query validation failed: {e.errors()}")
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    def generate():
        try:
            for token in query_rag_stream(
                req.question, 
                req.top_k, 
                req.temperature,
                response_style=req.response_style,
                search_mode=req.search_mode
            ):
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


@query_bp.route("/search", methods=["POST"])
@limiter.limit(LIMITS["search"])
def search():
    """Apenas busca documentos similares, sem gerar resposta."""
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/search", "POST", data)
    
    try:
        req = SearchRequest(**data)
    except ValidationError as e:
        api_logger.warning(f"Search validation failed: {e.errors()}")
        log_api_response("/api/search", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        results = search_only(req.question, req.top_k)
        
        log_api_response("/api/search", 200, time.time() - start_time)
        return jsonify({"results": results, "count": len(results)})
    
    except Exception as e:
        api_logger.error(f"Error in /search: {e}")
        log_api_response("/api/search", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@query_bp.route("/chat", methods=["POST"])
@limiter.limit(LIMITS["query"])
def chat():
    """Endpoint RAG com suporte a histórico de conversas."""
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/chat", "POST", data)
    
    try:
        req = ChatRequest(**data)
    except ValidationError as e:
        api_logger.warning(f"Chat validation failed: {e.errors()}")
        log_api_response("/api/chat", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        result = query_rag_with_history(
            question=req.question,
            session_id=req.session_id,
            top_k=req.top_k,
            temperature=req.temperature,
            include_sources=req.include_sources,
            collection_id=req.collection,
            response_style=req.response_style,
            enable_adaptive=req.enable_adaptive,
            search_mode=req.search_mode
        )
        
        log_api_response("/api/chat", 200, time.time() - start_time)
        return jsonify(result)
    
    except Exception as e:
        api_logger.error(f"Error in /chat: {e}")
        log_api_response("/api/chat", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
