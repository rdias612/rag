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
import uuid
from flask import Blueprint, request, jsonify, Response, stream_with_context
from pydantic import ValidationError

from src.api.schemas import QueryRequest, ChatRequest, SearchRequest, StreamQueryRequest
from src.core.rag import query_rag, query_rag_stream, search_only, query_rag_with_history
from src.core.rag_explainer import explainer
from src.api.middleware.rate_limiter import limiter, LIMITS

print(__name__)

query_bp = Blueprint("query", __name__)


def generate_request_id():
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


@query_bp.route("/query", methods=["POST"])
@limiter.limit(LIMITS["query"])
def query():
    # User query endpoint called
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
    print("API Request Received | request_id=%s | endpoint=%s | method=%s | question=%s | body=%s",
                   request_id, "/api/query", "POST", data.get("question", "")[:100], data)
    
    # 3. Validar
    try:
        req = QueryRequest(**data)
        print("Validation Passed | request_id=%s", request_id)
    except ValidationError as e:
        print("Validation Failed | request_id=%s | errors=%s", request_id, e.errors())
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/query", 400, time.time() - start_time)
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
        print("Query Success | request_id=%s | status_code=%d | total_duration=%.3fs",
                       request_id, 200, total_duration)
        
        return jsonify(result)
    
    except Exception as e:
        print("Error in /api/query | request_id=%s | question=%s | collection_id=%s",
                           request_id, req.question if 'req' in locals() else data.get("question"),
                           req.collection if 'req' in locals() else data.get("collection"))
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/query", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@query_bp.route("/query/stream", methods=["POST"])
@limiter.limit(LIMITS["query"])
def query_stream():
    """Endpoint RAG com streaming."""
    data = request.get_json() or {}
    
    # Gerar request_id
    request_id = generate_request_id()

    # Log entrada
    print("API Request Received | request_id=%s | endpoint=%s | method=%s | question=%s",
                   request_id, "/api/query/stream", "POST", data.get("question", "")[:100])
    
    try:
        req = StreamQueryRequest(**data)
        print("Validation Passed | request_id=%s", request_id)
    except ValidationError as e:
        print("Validation Failed | request_id=%s | errors=%s", request_id, e.errors())
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    print("Stream Query Started | request_id=%s", request_id)
    
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
            print("Stream query completed successfully | request_id=%s", request_id)
        except Exception as e:
            print("Stream Query | request_id=%s | question=%s",
                               request_id, req.question)
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
    print("API Request Received | request_id=%s | endpoint=%s | method=%s | question=%s",
                   request_id, "/api/search", "POST", data.get("question", "")[:100])
    
    try:
        req = SearchRequest(**data)
        print("Validation Passed | request_id=%s", request_id)
    except ValidationError as e:
        print("Validation Failed | request_id=%s | errors=%s", request_id, e.errors())
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/search", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        results = search_only(req.question, req.top_k, request_id=request_id)
        
        total_duration = time.time() - start_time
        print("Search Success | request_id=%s | status_code=%d | results_count=%d | total_duration=%.3fs",
                       request_id, 200, len(results), total_duration)
        
        return jsonify({"results": results, "count": len(results)})
    
    except Exception as e:
        print("Error in /api/search | request_id=%s | question=%s",
                           request_id, req.question if 'req' in locals() else data.get("question"))
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/search", 500, time.time() - start_time)
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
    print("API Request Received | request_id=%s | endpoint=%s | method=%s | question=%s | session_id=%s",
                   request_id, "/api/chat", "POST", data.get("question", "")[:100], data.get("session_id"))
    
    try:
        req = ChatRequest(**data)
        print("Validation Passed | request_id=%s", request_id)
    except ValidationError as e:
        print("Validation Failed | request_id=%s | errors=%s", request_id, e.errors())
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/chat", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        # Explicit log to confirm chat handler execution and question receipt
        print("/chat received question (len=%d) | request_id=%s", len(req.question), request_id)
        print("/chat processing: session=%s question='%s' | request_id=%s",
                       req.session_id or 'new', req.question[:80], request_id)
        
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
        print("Chat Success | request_id=%s | status_code=%d | session_id=%s | total_duration=%.3fs",
                       request_id, 200, req.session_id, total_duration)
        
        print("/chat completed successfully | request_id=%s", request_id)
        
        return jsonify(result)
    
    except Exception as e:
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "session_id": req.session_id if 'req' in locals() else None,
            "question": req.question if 'req' in locals() else data.get('question', 'N/A')
        }

        # Log full stacktrace for easier diagnosis
        print("Error in /chat: %s", e)
        print("Error in /chat: %s", e)
        print("Error in /chat: %s | %s", e, traceback.format_exc())
        
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/chat", 500, time.time() - start_time)
        return jsonify({"error": str(e), "details": error_details}), 500
