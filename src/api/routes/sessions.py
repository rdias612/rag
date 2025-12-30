"""
Blueprint de gerenciamento de sessões de conversa.

Endpoints:
- GET /sessions - Lista sessões
- GET /sessions/<id> - Detalhes de sessão
- DELETE /sessions/<id> - Remove sessão
- POST /new - Cria nova sessão
"""
import time
from flask import Blueprint, jsonify

from src.core.rag import get_conversation_history, clear_conversation
from src.core.conversation import conversation_manager
from src.core.logger import api_logger, log_api_request, log_api_response

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """Lista todas as sessões de conversa ativas."""
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


@sessions_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Retorna o histórico completo de uma sessão."""
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


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Remove uma sessão de conversa."""
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


@sessions_bp.route("/new", methods=["POST"])
def new_session():
    """Cria uma nova sessão de conversa."""
    start_time = time.time()
    log_api_request("/api/chat/new", "POST")
    
    try:
        session_id = conversation_manager.create_session()
        
        log_api_response("/api/chat/new", 200, time.time() - start_time)
        return jsonify({"session_id": session_id})
    except Exception as e:
        api_logger.error(f"Error creating session: {e}")
        log_api_response("/api/chat/new", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
