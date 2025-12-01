"""
Rotas da API Flask.
"""
import os
import time
import uuid
import threading
from pathlib import Path
from datetime import datetime
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
from src.data.database import get_document_count, check_connection, insert_documents_batch
from src.data.ingestion import (
    SUPPORTED_EXTENSIONS, 
    process_document, 
    get_document_stats
)
from src.core.embeddings import get_embeddings_batch
from src.config import DOCUMENTS_DIR
from src.core.logger import (
    api_logger,
    log_api_request,
    log_api_response,
    log_api_input
)

api = Blueprint("api", __name__)


# =============================================================================
# Gerenciador de Jobs de Ingestão (em memória)
# =============================================================================
_ingestion_jobs: dict[str, dict] = {}
_ingestion_lock = threading.Lock()

# Diretório temporário para uploads
UPLOAD_DIR = Path(DOCUMENTS_DIR) / "_uploads"


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


# =============================================================================
# Endpoints de Ingestão de Documentos
# =============================================================================

def _process_ingestion_job(job_id: str, file_path: Path, original_filename: str):
    """
    Processa um documento em background.
    
    Args:
        job_id: ID do job de ingestão
        file_path: Caminho do arquivo salvo
        original_filename: Nome original do arquivo
    """
    try:
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "processing"
            _ingestion_jobs[job_id]["message"] = "Extraindo texto e dividindo em chunks..."
        
        # 1. Processar documento (extrair texto e criar chunks)
        chunks = process_document(file_path)
        
        with _ingestion_lock:
            _ingestion_jobs[job_id]["chunks_created"] = len(chunks)
            _ingestion_jobs[job_id]["message"] = f"Gerando embeddings para {len(chunks)} chunks..."
        
        if not chunks:
            with _ingestion_lock:
                _ingestion_jobs[job_id]["status"] = "failed"
                _ingestion_jobs[job_id]["error"] = "Nenhum texto extraído do documento"
            return
        
        # 2. Gerar embeddings
        texts = [chunk["content"] for chunk in chunks]
        embeddings = get_embeddings_batch(texts)
        
        with _ingestion_lock:
            _ingestion_jobs[job_id]["message"] = "Inserindo no banco de dados..."
        
        # 3. Preparar para inserção
        documents_to_insert = []
        for chunk, embedding in zip(chunks, embeddings):
            documents_to_insert.append({
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "embedding": embedding
            })
        
        # 4. Inserir no banco
        inserted = insert_documents_batch(documents_to_insert)
        
        # 5. Finalizar
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "completed"
            _ingestion_jobs[job_id]["chunks_inserted"] = inserted
            _ingestion_jobs[job_id]["message"] = f"Sucesso! {inserted} chunks indexados."
            _ingestion_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        api_logger.info(f"Ingestion job {job_id[:8]}... completed: {inserted} chunks")
        
    except Exception as e:
        api_logger.error(f"Ingestion job {job_id[:8]}... failed: {e}")
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "failed"
            _ingestion_jobs[job_id]["error"] = str(e)
    
    finally:
        # Limpar arquivo temporário
        try:
            if file_path.exists():
                file_path.unlink()
        except:
            pass


@api.route("/ingest", methods=["POST"])
def ingest_document():
    """
    Upload e ingestão de um documento.
    
    O processamento é feito em background. Use o job_id retornado
    para verificar o status.
    
    Request:
        Content-Type: multipart/form-data
        file: arquivo (PDF, DOCX, TXT, MD, HTML)
        
    Response:
        {
            "job_id": "uuid",
            "filename": "documento.pdf",
            "status": "queued",
            "message": "Documento recebido, processamento iniciado"
        }
    """
    start_time = time.time()
    log_api_request("/api/ingest", "POST")
    
    # Verificar se há arquivo
    if "file" not in request.files:
        log_api_response("/api/ingest", 400, time.time() - start_time)
        return jsonify({"error": "Nenhum arquivo enviado. Use 'file' no form-data."}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        log_api_response("/api/ingest", 400, time.time() - start_time)
        return jsonify({"error": "Nome do arquivo vazio"}), 400
    
    # Verificar extensão
    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        log_api_response("/api/ingest", 400, time.time() - start_time)
        return jsonify({
            "error": f"Formato não suportado: {ext}",
            "supported_formats": list(SUPPORTED_EXTENSIONS)
        }), 400
    
    try:
        # Criar diretório de uploads se não existir
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Gerar nome único para o arquivo
        job_id = str(uuid.uuid4())
        safe_filename = f"{job_id}_{filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        # Salvar arquivo
        file.save(str(file_path))
        
        # Registrar job
        with _ingestion_lock:
            _ingestion_jobs[job_id] = {
                "job_id": job_id,
                "filename": filename,
                "file_type": ext,
                "status": "queued",
                "message": "Documento recebido, aguardando processamento",
                "chunks_created": 0,
                "chunks_inserted": 0,
                "created_at": datetime.now().isoformat(),
                "completed_at": None,
                "error": None
            }
        
        # Iniciar processamento em background
        thread = threading.Thread(
            target=_process_ingestion_job,
            args=(job_id, file_path, filename)
        )
        thread.daemon = True
        thread.start()
        
        api_logger.info(f"Ingestion job started: {job_id[:8]}... for {filename}")
        log_api_response("/api/ingest", 202, time.time() - start_time)
        
        return jsonify({
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "message": "Documento recebido, processamento iniciado"
        }), 202
        
    except Exception as e:
        api_logger.error(f"Error starting ingestion: {e}")
        log_api_response("/api/ingest", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/ingest/status/<job_id>", methods=["GET"])
def get_ingestion_status(job_id: str):
    """
    Verifica o status de um job de ingestão.
    
    Response:
        {
            "job_id": "uuid",
            "filename": "documento.pdf",
            "status": "completed",  // queued, processing, completed, failed
            "chunks_created": 15,
            "chunks_inserted": 15,
            "message": "Sucesso! 15 chunks indexados.",
            "created_at": "2025-11-30T10:00:00",
            "completed_at": "2025-11-30T10:00:05"
        }
    """
    start_time = time.time()
    log_api_request(f"/api/ingest/status/{job_id[:8]}...", "GET")
    
    with _ingestion_lock:
        job = _ingestion_jobs.get(job_id)
    
    if job is None:
        log_api_response(f"/api/ingest/status/{job_id[:8]}...", 404, time.time() - start_time)
        return jsonify({"error": "Job não encontrado"}), 404
    
    log_api_response(f"/api/ingest/status/{job_id[:8]}...", 200, time.time() - start_time)
    return jsonify(job)


@api.route("/ingest/jobs", methods=["GET"])
def list_ingestion_jobs():
    """
    Lista todos os jobs de ingestão.
    
    Query params:
        status: filtrar por status (queued, processing, completed, failed)
        
    Response:
        {
            "jobs": [...],
            "count": 5
        }
    """
    start_time = time.time()
    log_api_request("/api/ingest/jobs", "GET")
    
    status_filter = request.args.get("status")
    
    with _ingestion_lock:
        jobs = list(_ingestion_jobs.values())
    
    # Filtrar por status se especificado
    if status_filter:
        jobs = [j for j in jobs if j["status"] == status_filter]
    
    # Ordenar por data de criação (mais recente primeiro)
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    log_api_response("/api/ingest/jobs", 200, time.time() - start_time)
    
    return jsonify({
        "jobs": jobs,
        "count": len(jobs)
    })


@api.route("/ingest/formats", methods=["GET"])
def get_supported_formats():
    """
    Retorna os formatos de arquivo suportados para ingestão.
    
    Response:
        {
            "formats": [".pdf", ".docx", ".txt", ".md", ".html", ".htm"],
            "description": {...}
        }
    """
    start_time = time.time()
    log_api_request("/api/ingest/formats", "GET")
    
    log_api_response("/api/ingest/formats", 200, time.time() - start_time)
    
    return jsonify({
        "formats": sorted(list(SUPPORTED_EXTENSIONS)),
        "description": {
            ".pdf": "Documento PDF",
            ".docx": "Microsoft Word",
            ".txt": "Texto plano",
            ".md": "Markdown",
            ".html": "HTML",
            ".htm": "HTML"
        }
    })


@api.route("/documents/stats", methods=["GET"])
def documents_stats():
    """
    Retorna estatísticas dos documentos no diretório de ingestão.
    
    Response:
        {
            "total_files": 10,
            "files_by_type": {".pdf": 5, ".docx": 3, ".txt": 2},
            "total_pdf_pages": 150,
            "total_size_mb": 25.5,
            "indexed_chunks": 500
        }
    """
    start_time = time.time()
    log_api_request("/api/documents/stats", "GET")
    
    try:
        # Stats do diretório
        if DOCUMENTS_DIR.exists():
            dir_stats = get_document_stats(DOCUMENTS_DIR)
        else:
            dir_stats = {
                "total_files": 0,
                "files_by_type": {},
                "total_pdf_pages": 0,
                "total_size_mb": 0,
                "files": []
            }
        
        # Chunks indexados no banco
        indexed_chunks = get_document_count()
        
        result = {
            **dir_stats,
            "indexed_chunks": indexed_chunks,
            "documents_dir": str(DOCUMENTS_DIR)
        }
        
        log_api_response("/api/documents/stats", 200, time.time() - start_time)
        return jsonify(result)
        
    except Exception as e:
        api_logger.error(f"Error in /documents/stats: {e}")
        log_api_response("/api/documents/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
