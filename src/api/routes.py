"""
Rotas da API Flask.
"""
import time
from flask import Blueprint, request, jsonify, Response, stream_with_context

from src.core.rag import (
    query_rag, 
    query_rag_stream, 
    search_only,
    query_rag_with_history,
    get_conversation_history,
    clear_conversation
)
from src.core.conversation import conversation_manager
from src.data.database import get_document_count, check_connection
from src.core.logger import (
    api_logger,
    log_api_request,
    log_api_response,
    log_api_input
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
    
    # Log do input completo recebido
    log_api_input("/api/query", "POST", data)
    
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
    
    # Log do input completo recebido
    log_api_input("/api/query/stream", "POST", data)
    
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
    
    # Log do input completo recebido
    log_api_input("/api/search", "POST", data)
    
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


# =============================================================================
# Endpoints de Conversa (Histórico)
# =============================================================================

@api.route("/chat", methods=["POST"])
def chat():
    """
    Endpoint RAG com suporte a histórico de conversas.
    
    Permite perguntas de follow-up mantendo o contexto.
    
    Body:
        {
            "question": "Sua pergunta aqui",
            "session_id": "uuid-opcional",  // omitir para nova conversa
            "top_k": 5,  // opcional
            "temperature": 0.7,  // opcional
            "include_sources": true  // opcional
        }
        
    Response:
        {
            "answer": "...",
            "session_id": "uuid",  // usar nas próximas perguntas
            "message_count": 2,
            "sources": [...]
        }
    """
    start_time = time.time()
    data = request.get_json()
    
    log_api_input("/api/chat", "POST", data)
    
    if not data or "question" not in data:
        api_logger.warning("Chat request missing 'question' field")
        log_api_response("/api/chat", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    question = data["question"]
    session_id = data.get("session_id")  # Opcional
    top_k = data.get("top_k", 5)
    temperature = data.get("temperature", 0.7)
    include_sources = data.get("include_sources", True)
    
    try:
        result = query_rag_with_history(
            question=question,
            session_id=session_id,
            top_k=top_k,
            temperature=temperature,
            include_sources=include_sources
        )
        
        log_api_response("/api/chat", 200, time.time() - start_time)
        
        return jsonify(result)
    
    except Exception as e:
        api_logger.error(f"Error in /chat: {e}")
        log_api_response("/api/chat", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/chat/sessions", methods=["GET"])
def list_sessions():
    """
    Lista todas as sessões de conversa ativas.
    
    Response:
        {
            "sessions": [
                {
                    "session_id": "uuid",
                    "message_count": 4,
                    "created_at": "2025-11-30T10:00:00",
                    "last_activity": "2025-11-30T10:05:00"
                }
            ],
            "count": 1
        }
    """
    start_time = time.time()
    log_api_request("/api/chat/sessions", "GET")
    
    try:
        sessions = conversation_manager.list_sessions()
        
        log_api_response("/api/chat/sessions", 200, time.time() - start_time)
        
        return jsonify({
            "sessions": sessions,
            "count": len(sessions)
        })
    
    except Exception as e:
        api_logger.error(f"Error in /chat/sessions: {e}")
        log_api_response("/api/chat/sessions", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/chat/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """
    Retorna o histórico completo de uma sessão.
    
    Response:
        {
            "session_id": "uuid",
            "messages": [
                {"role": "user", "content": "...", "timestamp": 1234567890},
                {"role": "assistant", "content": "...", "timestamp": 1234567891}
            ],
            "created_at": "2025-11-30T10:00:00",
            "message_count": 4
        }
    """
    start_time = time.time()
    log_api_request(f"/api/chat/sessions/{session_id[:8]}...", "GET")
    
    try:
        history = get_conversation_history(session_id)
        
        if history is None:
            log_api_response(f"/api/chat/sessions/{session_id[:8]}...", 404, time.time() - start_time)
            return jsonify({"error": "Sessão não encontrada ou expirada"}), 404
        
        log_api_response(f"/api/chat/sessions/{session_id[:8]}...", 200, time.time() - start_time)
        
        return jsonify(history)
    
    except Exception as e:
        api_logger.error(f"Error in /chat/sessions/{session_id}: {e}")
        log_api_response(f"/api/chat/sessions/{session_id[:8]}...", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/chat/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """
    Remove uma sessão de conversa.
    
    Response:
        {"message": "Sessão removida com sucesso"}
    """
    start_time = time.time()
    log_api_request(f"/api/chat/sessions/{session_id[:8]}...", "DELETE")
    
    try:
        deleted = clear_conversation(session_id)
        
        if not deleted:
            log_api_response(f"/api/chat/sessions/{session_id[:8]}...", 404, time.time() - start_time)
            return jsonify({"error": "Sessão não encontrada"}), 404
        
        log_api_response(f"/api/chat/sessions/{session_id[:8]}...", 200, time.time() - start_time)
        
        return jsonify({"message": "Sessão removida com sucesso"})
    
    except Exception as e:
        api_logger.error(f"Error deleting session {session_id}: {e}")
        log_api_response(f"/api/chat/sessions/{session_id[:8]}...", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/chat/new", methods=["POST"])
def new_session():
    """
    Cria uma nova sessão de conversa.
    
    Response:
        {"session_id": "uuid"}
    """
    start_time = time.time()
    log_api_request("/api/chat/new", "POST")
    
    try:
        session_id = conversation_manager.create_session()
        
        log_api_response("/api/chat/new", 201, time.time() - start_time)
        
        return jsonify({"session_id": session_id}), 201
    
    except Exception as e:
        api_logger.error(f"Error creating session: {e}")
        log_api_response("/api/chat/new", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
