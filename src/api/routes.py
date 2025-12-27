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
from pydantic import ValidationError
from apscheduler.schedulers.background import BackgroundScheduler

from src.api.schemas import QueryRequest, ChatRequest, SearchRequest, StreamQueryRequest, FeedbackRequest

from src.core.rag import (
    query_rag, 
    query_rag_stream, 
    search_only,
    query_rag_with_history,
    get_conversation_history,
    clear_conversation
)
from src.core.conversation import conversation_manager
from src.data.database import (
    get_document_count, 
    check_connection, 
    insert_documents_batch, 
    list_collections, 
    insert_feedback,
    get_ingested_document,
    register_ingested_document,
    remove_document_chunks_by_source,
    list_ingested_documents,
    remove_ingested_document_record,
    clear_all_documents
)
from src.data.ingestion import (
    SUPPORTED_EXTENSIONS, 
    process_document, 
    get_document_stats,
    get_all_documents
)
import hashlib
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

# =============================================================================
# Agendador de Tarefas em Background (APScheduler)
# =============================================================================
scheduler = BackgroundScheduler()

def _run_session_cleanup():
    """Wrapper para a tarefa de limpeza periódica de sessões."""
    try:
        count = conversation_manager.cleanup_expired_sessions()
        if count > 0:
            api_logger.debug(f"Background cleanup: {count} sessions removed")
    except Exception as e:
        api_logger.error(f"Error in background session cleanup: {e}")

# Adicionar job para rodar a cada 10 minutos
scheduler.add_job(_run_session_cleanup, 'interval', minutes=10, id='session_cleanup')
scheduler.start()

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
            "include_sources": true,  // opcional
            "collection": "nome_do_projeto" // opcional
        }
    """
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/query", "POST", data)
    
    # Validação com Pydantic
    try:
        req = QueryRequest(**data)
    except ValidationError as e:
        api_logger.warning(f"Query validation failed: {e.errors()}")
        log_api_response("/api/query", 400, time.time() - start_time)
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    try:
        result = query_rag(
            question=req.question,
            top_k=req.top_k,
            temperature=req.temperature,
            include_sources=req.include_sources,
            collection_id=req.collection,
            debug_mode=req.debug
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
    data = request.get_json() or {}
    log_api_input("/api/query/stream", "POST", data)
    
    # Validação com Pydantic
    try:
        req = StreamQueryRequest(**data)
    except ValidationError as e:
        api_logger.warning(f"Stream query validation failed: {e.errors()}")
        return jsonify({"error": "Dados inválidos", "details": e.errors()}), 400
    
    def generate():
        try:
            for token in query_rag_stream(req.question, req.top_k, req.temperature):
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
    data = request.get_json() or {}
    log_api_input("/api/search", "POST", data)
    
    # Validação com Pydantic
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
    data = request.get_json() or {}
    log_api_input("/api/chat", "POST", data)
    
    # Validação com Pydantic
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
            collection_id=req.collection
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
        
        log_api_response("/api/chat/new", 200, time.time() - start_time)
        return jsonify({"session_id": session_id})
    except Exception as e:
        api_logger.error(f"Error creating session: {e}")
        log_api_response("/api/chat/new", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/collections", methods=["GET"])
def get_collections():
    """
    Lista todas as coleções disponíveis.
    
    Response:
        {"collections": ["default", "projeto_A", ...]}
    """
    start_time = time.time()
    log_api_request("/api/collections", "GET")
    
    try:
        collections = list_collections()
        log_api_response("/api/collections", 200, time.time() - start_time)
        return jsonify({"collections": collections})
    except Exception as e:
        print(f"[DEBUG] /collections - ERROR: {e}")
        api_logger.error(f"Error in /collections: {e}")
        log_api_response("/api/collections", 500, time.time() - start_time)
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


# =============================================================================
# Endpoints de Gerenciamento de Documentos Ingeridos
# =============================================================================

def _calculate_file_hash(file_path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@api.route("/documents/ingested", methods=["GET"])
def get_ingested_documents():
    """
    Lista todos os documentos já ingeridos.
    
    Query params:
        collection: filtrar por coleção (opcional)
        
    Response:
        {
            "documents": [
                {
                    "file_path": "/path/to/doc.pdf",
                    "file_name": "doc.pdf",
                    "file_hash": "abc123...",
                    "file_size": 1024,
                    "collection_id": "default",
                    "chunks_count": 15,
                    "status": "success",
                    "ingested_at": "2025-12-26T10:00:00"
                }
            ],
            "count": 1
        }
    """
    start_time = time.time()
    log_api_request("/api/documents/ingested", "GET")
    
    try:
        collection_filter = request.args.get("collection")
        documents = list_ingested_documents(collection_filter)
        
        # Enriquecer com nome do arquivo
        for doc in documents:
            doc["file_name"] = Path(doc["file_path"]).name
            # Converter datetime para string se necessário
            if hasattr(doc.get("ingested_at"), "isoformat"):
                doc["ingested_at"] = doc["ingested_at"].isoformat()
            if hasattr(doc.get("updated_at"), "isoformat"):
                doc["updated_at"] = doc["updated_at"].isoformat()
        
        log_api_response("/api/documents/ingested", 200, time.time() - start_time)
        return jsonify({
            "documents": documents,
            "count": len(documents)
        })
        
    except Exception as e:
        api_logger.error(f"Error in /documents/ingested: {e}")
        log_api_response("/api/documents/ingested", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/documents/delete", methods=["POST"])
def delete_ingested_document():
    """
    Deleta um documento e todos os seus chunks do banco.
    
    Body:
        {
            "file_path": "/path/to/document.pdf"
        }
        
    Response:
        {
            "message": "Documento removido com sucesso",
            "file_path": "/path/to/document.pdf",
            "chunks_removed": 15
        }
    """
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/documents/delete", "POST", data)
    
    if "file_path" not in data:
        log_api_response("/api/documents/delete", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'file_path' é obrigatório"}), 400
    
    file_path = data["file_path"]
    
    try:
        # Verificar se documento existe na tabela de controle
        existing = get_ingested_document(file_path)
        if not existing:
            log_api_response("/api/documents/delete", 404, time.time() - start_time)
            return jsonify({"error": "Documento não encontrado"}), 404
        
        # Remover chunks do banco
        chunks_removed = remove_document_chunks_by_source(file_path)
        
        # Remover registro de controle
        remove_ingested_document_record(file_path)
        
        api_logger.info(f"Document deleted: {file_path}, {chunks_removed} chunks removed")
        log_api_response("/api/documents/delete", 200, time.time() - start_time)
        
        return jsonify({
            "message": "Documento removido com sucesso",
            "file_path": file_path,
            "chunks_removed": chunks_removed
        })
        
    except Exception as e:
        api_logger.error(f"Error deleting document: {e}")
        log_api_response("/api/documents/delete", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


# Estado global para ingestão em massa
_bulk_ingestion_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_file": None,
    "message": "",
    "results": []
}
_bulk_ingestion_lock = threading.Lock()


def _run_bulk_ingestion(force: bool = False, specific_files: list[str] = None):
    """Executa ingestão em massa em background."""
    global _bulk_ingestion_status
    
    try:
        # Listar documentos do diretório
        all_document_files = get_all_documents(DOCUMENTS_DIR)
        
        # Determinar quais arquivos serão realmente processados
        if specific_files:
            # Processar apenas os arquivos selecionados
            files_to_process = [dp for dp in all_document_files if str(dp) in specific_files]
            # Se for específico, forçamos a limpeza do conteúdo antigo
            force = True 
        elif force:
            files_to_process = all_document_files
        else:
            pending = _scan_documents()
            pending_paths = {p["path"] for p in pending}
            files_to_process = [dp for dp in all_document_files if str(dp) in pending_paths]
            
        total_files = len(files_to_process)
        
        if total_files == 0:
            with _bulk_ingestion_lock:
                _bulk_ingestion_status["running"] = False
                _bulk_ingestion_status["progress"] = 0
                _bulk_ingestion_status["total"] = 0
                _bulk_ingestion_status["message"] = "Concluído: Nada para processar (todos os arquivos já estão atualizados)"
            return

        with _bulk_ingestion_lock:
            _bulk_ingestion_status["total"] = total_files
            _bulk_ingestion_status["progress"] = 0
            _bulk_ingestion_status["results"] = []
        
        docs_processed = 0
        docs_skipped = 0
        docs_failed = 0
        
        for i, doc_path in enumerate(files_to_process, start=1):
            file_path_str = str(doc_path)
            file_name = doc_path.name
            
            with _bulk_ingestion_lock:
                _bulk_ingestion_status["progress"] = i
                _bulk_ingestion_status["current_file"] = file_name
                _bulk_ingestion_status["message"] = f"Processando: {file_name}"
            
            try:
                # Calcular hash do arquivo
                file_hash = _calculate_file_hash(doc_path)
                file_size = doc_path.stat().st_size
                
                # Verificar se já foi ingerido para tratar remoção de chunks antigos
                existing = get_ingested_document(file_path_str)
                
                if existing:
                    # Se estamos aqui e existing é true, ou é force=True ou foi detectada mudança pelo _scan
                    # De qualquer forma, precisamos remover o conteúdo antigo primeiro
                    remove_document_chunks_by_source(file_path_str)
                
                # Determinar collection_id
                try:
                    relative_path = doc_path.relative_to(DOCUMENTS_DIR)
                    collection_id = relative_path.parts[0] if len(relative_path.parts) > 1 else "default"
                except ValueError:
                    collection_id = "default"
                
                # Processar documento
                api_logger.info(f"[{i}/{total_files}] Iniciando: {file_name}")
                
                api_logger.info(f"  [1/3] Extraindo texto e criando chunks...")
                chunks = process_document(doc_path)
                
                if not chunks:
                    api_logger.warning(f"  [!] Nenhum texto extraído de {file_name}")
                    docs_failed += 1
                    register_ingested_document(file_path_str, file_hash, file_size, collection_id, 0, "error")
                    with _bulk_ingestion_lock:
                        _bulk_ingestion_status["results"].append({
                            "file": file_name,
                            "status": "error",
                            "message": "Nenhum texto extraído"
                        })
                    continue
                
                api_logger.info(f"  [2/3] Gerando embeddings para {len(chunks)} chunks...")
                # Gerar embeddings
                texts = [chunk["content"] for chunk in chunks]
                embeddings = get_embeddings_batch(texts)
                
                if len(embeddings) != len(chunks):
                    raise ValueError(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")

                # Preparar e inserir
                api_logger.info(f"  [3/3] Inserindo no banco de dados...")
                documents_to_insert = []
                for chunk, embedding in zip(chunks, embeddings):
                    documents_to_insert.append({
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        "embedding": embedding,
                        "collection_id": collection_id
                    })
                
                inserted = insert_documents_batch(documents_to_insert)
                
                # Registrar como ingerido
                register_ingested_document(file_path_str, file_hash, file_size, collection_id, inserted, "success")
                
                docs_processed += 1
                api_logger.info(f"  [V] Concluído: {file_name} ({inserted} chunks)")
                
                with _bulk_ingestion_lock:
                    _bulk_ingestion_status["results"].append({
                        "file": file_name,
                        "status": "success",
                        "chunks": inserted,
                        "total_chunks": len(chunks)
                    })
                    
            except Exception as e:
                docs_failed += 1
                api_logger.error(f"  [X] ERRO ao processar {file_name}: {e}", exc_info=True)
                with _bulk_ingestion_lock:
                    _bulk_ingestion_status["results"].append({
                        "file": file_name,
                        "status": "error",
                        "message": str(e)
                    })
        
        with _bulk_ingestion_lock:
            _bulk_ingestion_status["running"] = False
            _bulk_ingestion_status["current_file"] = None
            _bulk_ingestion_status["message"] = f"Concluído: {docs_processed} processados, {docs_skipped} ignorados, {docs_failed} erros"
            
    except Exception as e:
        api_logger.error(f"Bulk ingestion failed: {e}")
        with _bulk_ingestion_lock:
            _bulk_ingestion_status["running"] = False
            _bulk_ingestion_status["message"] = f"Erro: {str(e)}"


def _scan_documents():
    """Escaneia diretório buscando arquivos novos ou modificados."""
    document_files = get_all_documents(DOCUMENTS_DIR)
    pending = []
    
    for doc_path in document_files:
        file_path_str = str(doc_path)
        try:
            file_hash = _calculate_file_hash(doc_path)
            file_size = doc_path.stat().st_size
            
            existing = get_ingested_document(file_path_str)
            
            if not existing:
                pending.append({
                    "file": doc_path.name,
                    "path": file_path_str,
                    "reason": "new",
                    "size": file_size
                })
            elif existing["file_hash"] != file_hash:
                pending.append({
                    "file": doc_path.name,
                    "path": file_path_str,
                    "reason": "modified",
                    "size": file_size
                })
        except Exception as e:
            api_logger.warning(f"Could not scan {doc_path}: {e}")
            
    return pending


@api.route("/documents/scan", methods=["GET"])
def scan_pending_documents():
    """Retorna lista de documentos que precisam de atualização."""
    start_time = time.time()
    log_api_request("/api/documents/scan", "GET")
    
    try:
        pending = _scan_documents()
        duration = time.time() - start_time
        log_api_response("/api/documents/scan", 200, duration)
        
        return jsonify({
            "pending": pending,
            "count": len(pending)
        }), 200
    except Exception as e:
        api_logger.error(f"Error scanning documents: {e}")
        log_api_response("/api/documents/scan", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/documents/ingest-all", methods=["POST"])
def start_bulk_ingestion():
    """
    Inicia ingestão em massa de todos os documentos do diretório.
    
    Body:
        {
            "force": false  // Se true, re-ingere todos mesmo que já existam
        }
        
    Response:
        {
            "message": "Ingestão iniciada",
            "total_files": 10
        }
    """
    global _bulk_ingestion_status
    
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/documents/ingest-all", "POST", data)
    
    force = data.get("force", False)
    files_to_ingest = data.get("files", None)
    
    # Contar arquivos que serão realmente processados (antes do lock para evitar NameError)
    if files_to_ingest:
        total_to_process = len(files_to_ingest)
    elif force:
        all_document_files = get_all_documents(DOCUMENTS_DIR)
        total_to_process = len(all_document_files)
    else:
        pending = _scan_documents()
        total_to_process = len(pending)
        
    with _bulk_ingestion_lock:
        if _bulk_ingestion_status["running"]:
            log_api_response("/api/documents/ingest-all", 409, time.time() - start_time)
            return jsonify({"error": "Ingestão já está em andamento"}), 409
        
        _bulk_ingestion_status["running"] = True
        _bulk_ingestion_status["progress"] = 0
        _bulk_ingestion_status["total"] = total_to_process
        _bulk_ingestion_status["current_file"] = None
        _bulk_ingestion_status["message"] = "Iniciando..."
        _bulk_ingestion_status["results"] = []
    
    # Iniciar em background
    thread = threading.Thread(target=_run_bulk_ingestion, args=(force, files_to_ingest))
    thread.daemon = True
    thread.start()
    
    api_logger.info(f"Bulk ingestion started: {total_to_process} files to process (force={force})")
    log_api_response("/api/documents/ingest-all", 202, time.time() - start_time)
    
    return jsonify({
        "message": "Ingestão iniciada",
        "total_files": total_to_process
    }), 202


@api.route("/documents/ingest-status", methods=["GET"])
def get_bulk_ingestion_status():
    """
    Retorna o status da ingestão em massa.
    
    Response:
        {
            "running": true,
            "progress": 5,
            "total": 10,
            "current_file": "documento.pdf",
            "message": "Processando: documento.pdf",
            "results": [...]
        }
    """
    start_time = time.time()
    # Log removido para reduzir ruído, a menos que haja algo importante
    # log_api_request("/api/documents/ingest-status", "GET")
    
    with _bulk_ingestion_lock:
        status = dict(_bulk_ingestion_status)
    
    # log_api_response("/api/documents/ingest-status", 200, time.time() - start_time)
    return jsonify(status), 200


@api.route("/documents/reprocess", methods=["POST"])
def reprocess_knowledge_base():
    """
    Limpa toda a base de conhecimento e reinicia ingestão.
    
    Response:
        {
            "message": "Reprocessamento iniciado",
            "cleared": {...},
            "total_files": 10
        }
    """
    global _bulk_ingestion_status
    
    start_time = time.time()
    log_api_request("/api/documents/reprocess", "POST")
    
    with _bulk_ingestion_lock:
        if _bulk_ingestion_status["running"]:
            log_api_response("/api/documents/reprocess", 409, time.time() - start_time)
            return jsonify({"error": "Ingestão já está em andamento"}), 409
    
    try:
        # Limpar todas as tabelas
        cleared = clear_all_documents()
        
        # Iniciar reingestão
        with _bulk_ingestion_lock:
            _bulk_ingestion_status["running"] = True
            _bulk_ingestion_status["progress"] = 0
            _bulk_ingestion_status["total"] = 0
            _bulk_ingestion_status["current_file"] = None
            _bulk_ingestion_status["message"] = "Base limpa. Iniciando reprocessamento..."
            _bulk_ingestion_status["results"] = []
        
        # Contar arquivos
        document_files = get_all_documents(DOCUMENTS_DIR)
        
        # Iniciar em background com force=True (ignora verificação de hash já que limpamos tudo)
        thread = threading.Thread(target=_run_bulk_ingestion, args=(True,))
        thread.daemon = True
        thread.start()
        
        api_logger.info(f"Reprocessing started: cleared {cleared}, processing {len(document_files)} files")
        log_api_response("/api/documents/reprocess", 202, time.time() - start_time)
        
        return jsonify({
            "message": "Reprocessamento iniciado",
            "cleared": cleared,
            "total_files": len(document_files)
        }), 202
        
    except Exception as e:
        api_logger.error(f"Error starting reprocess: {e}")
        log_api_response("/api/documents/reprocess", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Endpoints Phase 1 - Cache e Classificador
# =============================================================================

@api.route("/cache/stats", methods=["GET"])
def cache_stats():
    """
    Retorna estatísticas do cache de embeddings.
    
    Response:
        {
            "size": 50,
            "max_size": 1000,
            "hits": 100,
            "misses": 25,
            "hit_rate_percent": 80.0,
            "uptime_seconds": 3600.5
        }
    """
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


@api.route("/cache/clear", methods=["POST"])
def cache_clear():
    """
    Limpa o cache de embeddings.
    
    Response:
        {"message": "Cache limpo com sucesso"}
    """
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


@api.route("/classify", methods=["POST"])
def classify_question_endpoint():
    """
    Classifica uma pergunta em um tipo.
    
    Body:
        {"question": "O que é GWPRP?"}
        
    Response:
        {
            "question": "O que é GWPRP?",
            "type": "definition",
            "description": "Pergunta de definição/explicação"
        }
    """
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


# =============================================================================
# Endpoints Phase 3 - Avaliação
# =============================================================================

@api.route("/evaluate", methods=["POST"])
def evaluate_response():
    """
    Avalia qualidade de uma resposta RAG usando métricas RAGAS.
    
    Body:
        {
            "question": "Pergunta original",
            "answer": "Resposta gerada",
            "context": "Contexto usado"
        }
        
    Response:
        {
            "faithfulness": 0.85,
            "answer_relevancy": 0.90,
            "context_precision": 0.80,
            "overall_score": 0.85,
            "summary": "Qualidade: Excelente (Score: 85%)"
        }
    """
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


@api.route("/hyde/test", methods=["POST"])
def test_hyde():
    """
    Testa geração de documento hipotético (HyDE).
    
    Body:
        {"question": "O que é GWPRP?"}
        
    Response:
        {
            "question": "O que é GWPRP?",
            "hypothetical_document": "GWPRP é um protocolo..."
        }
    """
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


# =============================================================================
# Endpoints de Observabilidade (Phase: Metrics)
# =============================================================================

@api.route("/metrics", methods=["GET"])
def metrics():
    """
    Endpoint de métricas Prometheus.
    
    Retorna métricas no formato esperado pelo Prometheus para scraping.
    
    Response:
        Content-Type: text/plain
        Métricas no formato Prometheus
    """
    from src.core.metrics import get_metrics, check_metrics_available
    
    content, content_type = get_metrics()
    return Response(content, mimetype=content_type)


@api.route("/metrics/status", methods=["GET"])
def metrics_status():
    """
    Verifica status do módulo de métricas.
    
    Response:
        {
            "prometheus_available": true,
            "metrics_enabled": true
        }
    """
    start_time = time.time()
    log_api_request("/api/metrics/status", "GET")
    
    from src.core.metrics import check_metrics_available
    
    status = check_metrics_available()
    log_api_response("/api/metrics/status", 200, time.time() - start_time)
    
    return jsonify(status)


# =============================================================================
# Endpoints de Gerenciamento de Prompts
# =============================================================================

from src.data.database import (
    list_prompts,
    get_prompt_by_id,
    get_prompts_by_category,
    create_prompt,
    update_prompt_full,
    delete_prompt_safe,
    can_delete_prompt
)


@api.route("/prompts", methods=["GET"])
def get_all_prompts():
    """
    Lista todos os prompts disponíveis.
    
    Response:
        {
            "prompts": [
                {
                    "id": 1,
                    "name": "rag_prompt_enhanced",
                    "category": "rag_main",
                    "priority": 100,
                    "tags": ["default"],
                    "description": "Prompt RAG principal",
                    "use_case": "...",
                    "is_active": true
                }
            ],
            "count": 13
        }
    """
    start_time = time.time()
    log_api_request("/api/prompts", "GET")
    
    try:
        prompts = list_prompts()
        log_api_response("/api/prompts", 200, time.time() - start_time)
        
        return jsonify({
            "prompts": prompts,
            "count": len(prompts)
        })
    except Exception as e:
        api_logger.error(f"Error in /prompts: {e}")
        log_api_response("/api/prompts", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/prompts/<int:prompt_id>", methods=["GET"])
def get_prompt_detail(prompt_id: int):
    """
    Retorna detalhes completos de um prompt específico.
    
    Response:
        {
            "id": 1,
            "name": "rag_prompt_enhanced",
            "template": "Você é...",
            "category": "rag_main",
            "priority": 100,
            "tags": ["default"],
            "description": "...",
            "use_case": "...",
            "is_active": true,
            "created_at": "2025-12-26T00:00:00",
            "updated_at": "2025-12-26T00:00:00",
            "created_by": "system",
            "version": 1
        }
    """
    start_time = time.time()
    log_api_request(f"/api/prompts/{prompt_id}", "GET")
    
    try:
        prompt = get_prompt_by_id(prompt_id)
        
        if not prompt:
            log_api_response(f"/api/prompts/{prompt_id}", 404, time.time() - start_time)
            return jsonify({"error": "Prompt não encontrado"}), 404
        
        log_api_response(f"/api/prompts/{prompt_id}", 200, time.time() - start_time)
        return jsonify(prompt)
        
    except Exception as e:
        api_logger.error(f"Error in /prompts/{prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/prompts", methods=["POST"])
def create_new_prompt():
    """
    Cria um novo prompt.
    
    Body:
        {
            "name": "my_custom_prompt",
            "template": "Responda: {pergunta}...",
            "category": "rag_main",
            "description": "Meu prompt customizado",
            "priority": 120,
            "tags": ["custom", "quick"],
            "use_case": "Respostas rápidas"
        }
        
    Response:
        {
            "success": true,
            "prompt_id": 14,
            "message": "Prompt criado com sucesso"
        }
    """
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input("/api/prompts", "POST", {**data, "template": "..."})
    
    # Validar campos obrigatórios
    required_fields = ["name", "template", "category"]
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        log_api_response("/api/prompts", 400, time.time() - start_time)
        return jsonify({
            "error": "Campos obrigatórios faltando",
            "missing_fields": missing_fields
        }), 400
    
    try:
        success, prompt_id, error_msg = create_prompt(
            name=data["name"],
            template=data["template"],
            category=data["category"],
            description=data.get("description"),
            priority=data.get("priority", 100),
            tags=data.get("tags", []),
            use_case=data.get("use_case"),
            created_by="user"
        )
        
        if not success:
            log_api_response("/api/prompts", 400, time.time() - start_time)
            return jsonify({"error": error_msg}), 400
        
        log_api_response("/api/prompts", 201, time.time() - start_time)
        return jsonify({
            "success": True,
            "prompt_id": prompt_id,
            "message": "Prompt criado com sucesso"
        }), 201
        
    except Exception as e:
        api_logger.error(f"Error creating prompt: {e}")
        log_api_response("/api/prompts", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/prompts/<int:prompt_id>", methods=["PUT"])
def update_prompt_endpoint(prompt_id: int):
    """
    Atualiza um prompt existente.
    
    Body:
        {
            "template": "Novo template...",
            "description": "Nova descrição",
            "priority": 150,
            "tags": ["updated"],
            "use_case": "...",
            "is_active": true
        }
        
    Response:
        {
            "success": true,
            "message": "Prompt atualizado com sucesso"
        }
    """
    start_time = time.time()
    data = request.get_json() or {}
    log_api_input(f"/api/prompts/{prompt_id}", "PUT", data)
    
    try:
        success, error_msg = update_prompt_full(
            prompt_id=prompt_id,
            template=data.get("template"),
            description=data.get("description"),
            priority=data.get("priority"),
            tags=data.get("tags"),
            use_case=data.get("use_case"),
            is_active=data.get("is_active")
        )
        
        if not success:
            log_api_response(f"/api/prompts/{prompt_id}", 400, time.time() - start_time)
            return jsonify({"error": error_msg}), 400
        
        log_api_response(f"/api/prompts/{prompt_id}", 200, time.time() - start_time)
        return jsonify({
            "success": True,
            "message": "Prompt atualizado com sucesso"
        })
        
    except Exception as e:
        api_logger.error(f"Error updating prompt {prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/prompts/<int:prompt_id>/can-delete", methods=["GET"])
def check_can_delete_prompt(prompt_id: int):
    """
    Verifica se um prompt pode ser deletado (sem deletar).
    
    Response:
        {
            "can_delete": false,
            "reason": "Não é possível deletar o último prompt..."
        }
    """
    start_time = time.time()
    log_api_request(f"/api/prompts/{prompt_id}/can-delete", "GET")
    
    try:
        can_delete, reason = can_delete_prompt(prompt_id)
        
        log_api_response(f"/api/prompts/{prompt_id}/can-delete", 200, time.time() - start_time)
        
        return jsonify({
            "can_delete": can_delete,
            "reason": reason
        })
    except Exception as e:
        api_logger.error(f"Error checking delete permission for prompt {prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}/can-delete", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/prompts/<int:prompt_id>", methods=["DELETE"])
def delete_prompt_endpoint(prompt_id: int):
    """
    Deleta um prompt (com validação).
    
    Response:
        {
            "success": true,
            "message": "Prompt deletado com sucesso"
        }
        
    Ou erro se não puder deletar:
        {
            "error": "Não é possível deletar..."
        }
    """
    start_time = time.time()
    log_api_request(f"/api/prompts/{prompt_id}", "DELETE")
    
    try:
        success, error_msg = delete_prompt_safe(prompt_id)
        
        if not success:
            log_api_response(f"/api/prompts/{prompt_id}", 400, time.time() - start_time)
            return jsonify({"error": error_msg}), 400
        
        log_api_response(f"/api/prompts/{prompt_id}", 200, time.time() - start_time)
        return jsonify({
            "success": True,
            "message": "Prompt deletado com sucesso"
        })
        
    except Exception as e:
        api_logger.error(f"Error deleting prompt {prompt_id}: {e}")
        log_api_response(f"/api/prompts/{prompt_id}", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/prompts/categories", methods=["GET"])
def get_prompt_categories():
    """
    Retorna as categorias disponíveis e suas descrições.
    
    Response:
        {
            "categories": {
                "rag_main": "Prompt principal para RAG",
                "hyde": "Geração de documentos hipotéticos",
                "query_expansion": "Expansão de queries"
            }
        }
    """
    from src.data.database import CRITICAL_CATEGORIES
    
    start_time = time.time()
    log_api_request("/api/prompts/categories", "GET")
    
    categories = {
        **CRITICAL_CATEGORIES,
        "instruction": "Instruções específicas por tipo de pergunta"
    }
    
    log_api_response("/api/prompts/categories", 200, time.time() - start_time)
    
    return jsonify({"categories": categories})
