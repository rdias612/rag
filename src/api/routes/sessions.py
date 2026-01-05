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

print("rag.api")

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """Lista todas as sessões de conversa ativas."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", "/api/chat/sessions", "GET")
    
    try:
        sessions = conversation_manager.list_sessions()
        
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/chat/sessions", 200, time.time() - start_time)
        
        return jsonify({
            "sessions": sessions,
            "count": len(sessions)
        })
    
    except Exception as e:
        print("Error in /chat/sessions: %s", e)
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/chat/sessions", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """Retorna o histórico completo de uma sessão."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", f"/api/chat/sessions/{session_id[:8]}...", "GET")
    
    try:
        history = get_conversation_history(session_id)
        
        if history is None:
            print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                           f"/api/chat/sessions/{session_id[:8]}...", 404, time.time() - start_time)
            return jsonify({"error": "Sessão não encontrada ou expirada"}), 404
        
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       f"/api/chat/sessions/{session_id[:8]}...", 200, time.time() - start_time)
        
        return jsonify(history)
    
    except Exception as e:
        print("Error in /api/chat/sessions/%s: %s", session_id, e)
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       f"/api/chat/sessions/{session_id[:8]}...", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Remove uma sessão de conversa."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", f"/api/chat/sessions/{session_id[:8]}...", "DELETE")
    
    try:
        deleted = clear_conversation(session_id)
        
        if not deleted:
            print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                           f"/api/chat/sessions/{session_id[:8]}...", 404, time.time() - start_time)
            return jsonify({"error": "Sessão não encontrada"}), 404
        
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       f"/api/chat/sessions/{session_id[:8]}...", 200, time.time() - start_time)
        
        return jsonify({"message": "Sessão removida com sucesso"})
    
    except Exception as e:
        print("Error deleting session %s: %s", session_id, e)
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       f"/api/chat/sessions/{session_id[:8]}...", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@sessions_bp.route("/new", methods=["POST"])
def new_session():
    """Cria uma nova sessão de conversa."""
    start_time = time.time()
    print("API Request | endpoint=%s | method=%s", "/api/chat/new", "POST")
    
    try:
        session_id = conversation_manager.create_session()
        
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/chat/new", 200, time.time() - start_time)
        return jsonify({"session_id": session_id})
    except Exception as e:
        print("Error creating session: %s", e)
        print("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/chat/new", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
