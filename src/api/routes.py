"""
Rotas da API Flask.
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context

from src.core.rag import query_rag, query_rag_stream, search_only
from src.data.database import get_document_count, check_connection

api = Blueprint("api", __name__)


@api.route("/health", methods=["GET"])
def health_check():
    """Endpoint de health check."""
    db_ok = check_connection()
    
    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected"
    }), 200 if db_ok else 503


@api.route("/stats", methods=["GET"])
def get_stats():
    """Retorna estatísticas do sistema."""
    try:
        doc_count = get_document_count()
        
        return jsonify({
            "documents_count": doc_count,
            "status": "ok"
        })
    except Exception as e:
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
    data = request.get_json()
    
    if not data or "question" not in data:
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
        
        return jsonify(result)
    
    except Exception as e:
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
    
    if not data or "question" not in data:
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    question = data["question"]
    top_k = data.get("top_k", 5)
    temperature = data.get("temperature", 0.7)
    
    def generate():
        try:
            for token in query_rag_stream(question, top_k, temperature):
                yield token
        except Exception as e:
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
    data = request.get_json()
    
    if not data or "question" not in data:
        return jsonify({"error": "Campo 'question' é obrigatório"}), 400
    
    question = data["question"]
    top_k = data.get("top_k", 5)
    
    try:
        results = search_only(question, top_k)
        
        return jsonify({
            "results": results,
            "count": len(results)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
