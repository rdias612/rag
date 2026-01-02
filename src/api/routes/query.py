"""
Blueprint de queries RAG.

Endpoints:
- POST /query - Query RAG principal
- POST /query/stream - Query com streaming
- POST /search - Apenas busca (sem LLM)
- POST /chat - Chat com histórico
"""
import time
import traceback
from flask import Blueprint, request, jsonify, Response, stream_with_context
from pydantic import ValidationError

from src.api.schemas import QueryRequest, ChatRequest, SearchRequest, StreamQueryRequest
from src.core.rag import query_rag, query_rag_stream, search_only, query_rag_with_history
from src.core.rag_explainer import explainer
from src.core.logger import (
    api_logger,
    rag_logger,
    logger,
    log_api_request,
    log_api_response,
    log_api_input,
    flush_loggers,
    generate_request_id,
    log_step,
    log_error,
)
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
    
    # 1. Gerar request_id
    request_id = generate_request_id()
    
    # 2. Log entrada
    log_step(api_logger, "API Request Received", 
              request_id=request_id, 
              endpoint="/api/query", 
              method="POST", 
              question=data.get("question", "")[:100],
              body=data)
    
    # 3. Validar
    try:
        req = QueryRequest(**data)
        log_step(api_logger, "Validation Passed", request_id=request_id)
    except ValidationError as e:
        log_step(api_logger, "Validation Failed", 
                  request_id=request_id, 
                  errors=e.errors())
        log_api_response("/api/query", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    # 4. Chamar pipeline RAG com request_id
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
            search_mode=req.search_mode,
            request_id=request_id  # Propagar request_id
        )
        
        if include_explanation and "_debug" in result and "search" in result:
            result["explanation"] = explainer.explain_rag_pipeline(
                question=req.question,
                debug_info=result["_debug"],
                search_metrics=result["search"]
            )
            del result["_debug"]
        
        total_duration = time.time() - start_time
        log_step(api_logger, "Query Success", 
                  request_id=request_id, 
                  status_code=200,
                  total_duration=f"{total_duration:.3f}s")
        
        return jsonify(result)
    
    except Exception as e:
        log_error(api_logger, "/api/query", e, 
                  request_id=request_id,
                  question=req.question if 'req' in locals() else data.get("question"),
                  collection_id=req.collection if 'req' in locals() else data.get("collection"))
        
        log_api_response("/api/query", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@query_bp.route("/query/stream", methods=["POST"])
@limiter.limit(LIMITS["query"])
def query_stream():
    """Endpoint RAG com streaming."""
    data = request.get_json() or {}
    
    # Gerar request_id
    request_id = generate_request_id()
    
    # Log entrada
    log_step(api_logger, "API Request Received", 
              request_id=request_id, 
              endpoint="/api/query/stream", 
              method="POST", 
              question=data.get("question", "")[:100])
    
    try:
        req = StreamQueryRequest(**data)
        log_step(api_logger, "Validation Passed", request_id=request_id)
    except ValidationError as e:
        log_step(api_logger, "Validation Failed", 
                  request_id=request_id, 
                  errors=e.errors())
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    log_step(api_logger, "Stream Query Started", request_id=request_id)
    
    def generate():
        try:
            for token in query_rag_stream(
                req.question, 
                req.top_k, 
                req.temperature,
                response_style=req.response_style,
                search_mode=req.search_mode,
                request_id=request_id  # Propagar request_id
            ):
                yield token
            api_logger.info(f"Stream query completed successfully | request_id={request_id}")
        except Exception as e:
            log_error(api_logger, "Stream Query", e,
                      request_id=request_id,
                      question=req.question)
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
    
    # Gerar request_id
    request_id = generate_request_id()
    
    # Log entrada
    log_step(api_logger, "API Request Received", 
              request_id=request_id, 
              endpoint="/api/search", 
              method="POST", 
              question=data.get("question", "")[:100])
    
    try:
        req = SearchRequest(**data)
        log_step(api_logger, "Validation Passed", request_id=request_id)
    except ValidationError as e:
        log_step(api_logger, "Validation Failed", 
                  request_id=request_id, 
                  errors=e.errors())
        log_api_response("/api/search", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        results = search_only(req.question, req.top_k, request_id=request_id)
        
        total_duration = time.time() - start_time
        log_step(api_logger, "Search Success", 
                  request_id=request_id, 
                  status_code=200,
                  results_count=len(results),
                  total_duration=f"{total_duration:.3f}s")
        
        return jsonify({"results": results, "count": len(results)})
    
    except Exception as e:
        log_error(api_logger, "/api/search", e,
                  request_id=request_id,
                  question=req.question if 'req' in locals() else data.get("question"))
        log_api_response("/api/search", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@query_bp.route("/chat", methods=["POST"])
@limiter.limit(LIMITS["query"])
def chat():
    """Endpoint RAG com suporte a histórico de conversas."""
    start_time = time.time()
    data = request.get_json() or {}
    
    # Gerar request_id
    request_id = generate_request_id()
    
    # Log entrada
    log_step(api_logger, "API Request Received", 
              request_id=request_id, 
              endpoint="/api/chat", 
              method="POST", 
              question=data.get("question", "")[:100],
              session_id=data.get("session_id"))
    
    flush_loggers(api_logger, rag_logger, logger)
    
    try:
        req = ChatRequest(**data)
        log_step(api_logger, "Validation Passed", request_id=request_id)
    except ValidationError as e:
        log_step(api_logger, "Validation Failed", 
                  request_id=request_id, 
                  errors=e.errors())
        log_api_response("/api/chat", 400, time.time() - start_time)
        flush_loggers(api_logger, rag_logger, logger)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        # Explicit log to confirm chat handler execution and question receipt
        api_logger.info(f"/chat received question (len={len(req.question)}) | request_id={request_id}")
        rag_logger.info(f"/chat processing: session={req.session_id or 'new'} question='{req.question[:80]}' | request_id={request_id}")
        
        result = query_rag_with_history(
            question=req.question,
            session_id=req.session_id,
            top_k=req.top_k,
            temperature=req.temperature,
            include_sources=req.include_sources,
            collection_id=req.collection,
            response_style=req.response_style,
            enable_adaptive=req.enable_adaptive,
            search_mode=req.search_mode,
            request_id=request_id  # Propagar request_id
        )
        
        total_duration = time.time() - start_time
        log_step(api_logger, "Chat Success", 
                  request_id=request_id, 
                  status_code=200,
                  session_id=req.session_id,
                  total_duration=f"{total_duration:.3f}s")
        
        api_logger.info(f"/chat completed successfully | request_id={request_id}")
        flush_loggers(api_logger, rag_logger, logger)
        return jsonify(result)
    
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "session_id": req.session_id if 'req' in locals() else None,
            "question": req.question if 'req' in locals() else data.get('question', 'N/A')
        }

        # Log full stacktrace for easier diagnosis
        logger.error(f"Error in /chat: {e}", exc_info=True)
        api_logger.error(f"Error in /chat: {e}", exc_info=True)
        rag_logger.error(f"Error in /chat: {e} | {traceback.format_exc()}")
        
        log_error(api_logger, "/api/chat", e,
                  request_id=request_id,
                  session_id=req.session_id if 'req' in locals() else None,
                  question=req.question if 'req' in locals() else data.get("question"))

        log_api_response("/api/chat", 500, time.time() - start_time)
        flush_loggers(api_logger, rag_logger, logger)
        return jsonify({"error": str(e), "details": error_details}), 500
