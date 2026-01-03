"""
Blueprint de ingestão e gerenciamento de documentos.

Endpoints:
- POST /ingest - Upload de documento individual
- GET /ingest/status/<job_id> - Status de job de ingestão
- GET /ingest/jobs - Lista jobs de ingestão
- GET /ingest/formats - Formatos suportados
- GET /documents/stats - Estatísticas de documentos
- GET /documents/ingested - Lista documentos ingeridos
- POST /documents/delete - Deleta documento
- GET /documents/scan - Escaneia documentos pendentes
- POST /documents/ingest-all - Ingestão em massa
- GET /documents/ingest-status - Status da ingestão em massa
- POST /documents/reprocess - Reprocessa base de conhecimento
"""
import hashlib
import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify

from src.config import DOCUMENTS_DIR
from src.core.embeddings import get_embeddings_batch
from src.api.middleware.rate_limiter import limiter, LIMITS
from src.data.repositories import DocumentRepository, IngestionRepository
from src.data.ingestion import (
    SUPPORTED_EXTENSIONS,
    process_document,
    process_document_with_chunking_type,
    get_document_stats,
    get_all_documents
)

api_logger = logging.getLogger("rag.api")
ingestion_logger = logging.getLogger("rag.ingestion")

# Instâncias dos repositories
_doc_repo = DocumentRepository()
_ingestion_repo = IngestionRepository()

documents_bp = Blueprint("documents", __name__)

# =============================================================================
# Estado Global
# =============================================================================
_ingestion_jobs: dict[str, dict] = {}
_ingestion_lock = threading.Lock()

_bulk_ingestion_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_file": None,
    "message": "",
    "results": []
}
_bulk_ingestion_lock = threading.Lock()

UPLOAD_DIR = Path(DOCUMENTS_DIR) / "_uploads"


# =============================================================================
# Funções Auxiliares
# =============================================================================
def _calculate_file_hash(file_path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def _process_ingestion_job(job_id: str, file_path: Path, original_filename: str):
    """Processa um documento em background."""
    start_time = time.time()
    ingestion_logger.info("Ingestion started | file=%s | type=upload", str(file_path))
    
    try:
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "processing"
            _ingestion_jobs[job_id]["message"] = "Extraindo texto e dividindo em chunks..."
        
        chunks = process_document(file_path)
        
        with _ingestion_lock:
            _ingestion_jobs[job_id]["chunks_created"] = len(chunks)
            _ingestion_jobs[job_id]["message"] = f"Gerando embeddings para {len(chunks)} chunks..."
        
        if not chunks:
            with _ingestion_lock:
                _ingestion_jobs[job_id]["status"] = "failed"
                _ingestion_jobs[job_id]["error"] = "Nenhum texto extraído do documento"
            ingestion_logger.warning("Job %s failed: No text extracted from %s", job_id[:8], original_filename)
            return
        
        texts = [chunk["content"] for chunk in chunks]
        embeddings = get_embeddings_batch(texts, document_name=original_filename)
        
        with _ingestion_lock:
            _ingestion_jobs[job_id]["message"] = "Inserindo no banco de dados..."
        
        documents_to_insert = []
        for chunk, embedding in zip(chunks, embeddings):
            documents_to_insert.append({
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "embedding": embedding
            })
        
        inserted = _doc_repo.create_batch(documents_to_insert)
        
        duration = time.time() - start_time
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "completed"
            _ingestion_jobs[job_id]["chunks_inserted"] = inserted
            _ingestion_jobs[job_id]["message"] = f"Sucesso! {inserted} chunks indexados."
            _ingestion_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        ingestion_logger.info("Ingestion complete | file=%s | chunks=%d | duration=%.3fs", str(file_path), inserted, duration)
        
    except Exception as e:
        ingestion_logger.exception("Ingestion job %s... failed: %s", job_id[:8], e)
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "failed"
            _ingestion_jobs[job_id]["error"] = str(e)
    
    finally:
        try:
            if file_path.exists():
                file_path.unlink()
        except:
            pass


def _scan_documents():
    """Escaneia diretório buscando arquivos novos ou modificados."""
    document_files = get_all_documents(DOCUMENTS_DIR)
    pending = []
    
    for doc_path in document_files:
        file_path_str = str(doc_path)
        try:
            file_hash = _calculate_file_hash(doc_path)
            file_size = doc_path.stat().st_size
            
            existing = _ingestion_repo.find_by_path(file_path_str)
            
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
            api_logger.warning("Could not scan %s: %s", doc_path, e)
            
    return pending


def _run_bulk_ingestion(
    force: bool = False,
    specific_files: list[str] = None,
    files_with_chunking: list[dict] = None,
    clear_database: bool = False
):
    """
    Executa ingestão em massa em background.
    
    Args:
        force: Se True, ignora verificação de hash e processa tudo
        specific_files: Lista de caminhos específicos para processar (formato string)
        files_with_chunking: Lista de dicts com 'file_path' e 'chunking_type'
                           (usado quando frontend envia seleção de chunking)
        clear_database: Se True, limpa toda a base antes de processar
    """
    global _bulk_ingestion_status
    
    # Limpar base se solicitado
    if clear_database:
        doc_cleared = _doc_repo.clear_all()
        ing_cleared = _ingestion_repo.clear_all()
        api_logger.info("Database cleared: %d chunks, %d records", doc_cleared, ing_cleared)
    
    try:
        all_document_files = get_all_documents(DOCUMENTS_DIR)
        
        if files_with_chunking:
            # Frontend enviou seleção de chunking
            files_to_process = []
            chunking_map = {}  # {file_path: chunking_type}
            
            for fw in files_with_chunking:
                file_path = fw.get("file_path")
                chunking_type = fw.get("chunking_type", "hierarchical")
                
                # Encontrar o documento na lista de todos
                for dp in all_document_files:
                    if str(dp) == file_path:
                        files_to_process.append(dp)
                        chunking_map[str(dp)] = chunking_type
                        break
            
            force = True
        elif specific_files:
            files_to_process = [dp for dp in all_document_files if str(dp) in specific_files]
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
                file_hash = _calculate_file_hash(doc_path)
                file_size = doc_path.stat().st_size
                
                existing = _ingestion_repo.find_by_path(file_path_str)
                
                if existing:
                    _doc_repo.delete_by_source(file_path_str)
                
                try:
                    relative_path = doc_path.relative_to(DOCUMENTS_DIR)
                    collection_id = relative_path.parts[0] if len(relative_path.parts) > 1 else "default"
                except ValueError:
                    collection_id = "default"
                
                api_logger.info("[%d/%d] Iniciando: %s", i, total_files, file_name)
                
                # Determinar chunking type
                chunking_type = "hierarchical"
                if files_with_chunking and file_path_str in chunking_map:
                    chunking_type = chunking_map[file_path_str]
                    api_logger.info("  → Using chunking type: %s", chunking_type)
                
                chunks = process_document_with_chunking_type(doc_path, chunking_type)
                
                if not chunks:
                    api_logger.warning("  [!] Nenhum texto extraído de %s", file_name)
                    docs_failed += 1
                    _ingestion_repo.create(file_path_str, file_hash, file_size, collection_id, 0, "error", chunking_type)
                    with _bulk_ingestion_lock:
                        _bulk_ingestion_status["results"].append({
                            "file": file_name,
                            "status": "error",
                            "message": "Nenhum texto extraído"
                        })
                    continue
                
                texts = [chunk["content"] for chunk in chunks]
                embeddings = get_embeddings_batch(texts, document_name=file_name)
                
                if len(embeddings) != len(chunks):
                    raise ValueError(f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")

                documents_to_insert = []
                for chunk, embedding in zip(chunks, embeddings):
                    documents_to_insert.append({
                        "content": chunk["content"],
                        "metadata": chunk["metadata"],
                        "embedding": embedding,
                        "collection_id": collection_id
                    })
                
                inserted = _doc_repo.create_batch(documents_to_insert)
                
                _ingestion_repo.create(file_path_str, file_hash, file_size, collection_id, inserted, "success", chunking_type)
                
                docs_processed += 1
                api_logger.info("  [V] Concluído: %s (%d chunks)", file_name, inserted)
                
                with _bulk_ingestion_lock:
                    _bulk_ingestion_status["results"].append({
                        "file": file_name,
                        "status": "success",
                        "chunks": inserted,
                        "total_chunks": len(chunks)
                    })
                    
            except Exception as e:
                docs_failed += 1
                api_logger.exception("  [X] ERRO ao processar %s: %s", file_name, e)
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
        api_logger.exception("Bulk ingestion failed: %s", e)
        with _bulk_ingestion_lock:
            _bulk_ingestion_status["running"] = False
            _bulk_ingestion_status["message"] = f"Erro: {str(e)}"


# =============================================================================
# Endpoints de Upload Individual
# =============================================================================
@documents_bp.route("/ingest", methods=["POST"])
@limiter.limit(LIMITS["ingest"])
def ingest_document():
    """Upload e ingestão de um documento."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/ingest", "POST")
    
    if "file" not in request.files:
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/ingest", 400, time.time() - start_time)
        return jsonify({"error": "Nenhum arquivo enviado. Use 'file' no form-data."}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/ingest", 400, time.time() - start_time)
        return jsonify({"error": "Nome do arquivo vazio"}), 400
    
    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    if ext not in SUPPORTED_EXTENSIONS:
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/ingest", 400, time.time() - start_time)
        return jsonify({
            "error": f"Formato não suportado: {ext}",
            "supported_formats": list(SUPPORTED_EXTENSIONS)
        }), 400
    
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        job_id = str(uuid.uuid4())
        safe_filename = f"{job_id}_{filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        file.save(str(file_path))
        
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
        
        thread = threading.Thread(
            target=_process_ingestion_job,
            args=(job_id, file_path, filename)
        )
        thread.daemon = True
        thread.start()
        
        api_logger.info("Ingestion job started: %s... for %s", job_id[:8], filename)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/ingest", 202, time.time() - start_time)
        
        return jsonify({
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "message": "Documento recebido, processamento iniciado"
        }), 202
        
    except Exception as e:
        api_logger.exception("Error starting ingestion: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/ingest", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/ingest/status/<job_id>", methods=["GET"])
def get_ingestion_status(job_id: str):
    """Verifica o status de um job de ingestão."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", f"/api/ingest/status/{job_id[:8]}...", "GET")
    
    with _ingestion_lock:
        job = _ingestion_jobs.get(job_id)
    
    if job is None:
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       f"/api/ingest/status/{job_id[:8]}...", 404, time.time() - start_time)
        return jsonify({"error": "Job não encontrado"}), 404
    
    api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                   f"/api/ingest/status/{job_id[:8]}...", 200, time.time() - start_time)
    return jsonify(job)


@documents_bp.route("/ingest/jobs", methods=["GET"])
def list_ingestion_jobs():
    """Lista todos os jobs de ingestão."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/ingest/jobs", "GET")
    
    status_filter = request.args.get("status")
    
    with _ingestion_lock:
        jobs = list(_ingestion_jobs.values())
    
    if status_filter:
        jobs = [j for j in jobs if j["status"] == status_filter]
    
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                   "/api/ingest/jobs", 200, time.time() - start_time)
    
    return jsonify({
        "jobs": jobs,
        "count": len(jobs)
    })


@documents_bp.route("/ingest/formats", methods=["GET"])
def get_supported_formats():
    """Retorna os formatos de arquivo suportados para ingestão."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/ingest/formats", "GET")
    
    api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                   "/api/ingest/formats", 200, time.time() - start_time)
    
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


# =============================================================================
# Endpoints de Estatísticas e Gerenciamento
# =============================================================================
@documents_bp.route("/documents/stats", methods=["GET"])
def documents_stats():
    """Retorna estatísticas dos documentos no diretório de ingestão."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/stats", "GET")
    
    try:
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
        
        indexed_chunks = _doc_repo.count()
        
        result = {
            **dir_stats,
            "indexed_chunks": indexed_chunks,
            "documents_dir": str(DOCUMENTS_DIR)
        }
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/stats", 200, time.time() - start_time)
        return jsonify(result)
        
    except Exception as e:
        api_logger.exception("Error in /documents/stats: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/documents/ingested", methods=["GET"])
def get_ingested_documents():
    """Lista todos os documentos já ingeridos."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/ingested", "GET")
    
    try:
        collection_filter = request.args.get("collection")
        documents = _ingestion_repo.list_all(collection_filter)
        
        for doc in documents:
            doc["file_name"] = Path(doc["file_path"]).name
            if hasattr(doc.get("ingested_at"), "isoformat"):
                doc["ingested_at"] = doc["ingested_at"].isoformat()
            if hasattr(doc.get("updated_at"), "isoformat"):
                doc["updated_at"] = doc["updated_at"].isoformat()
        
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/ingested", 200, time.time() - start_time)
        return jsonify({
            "documents": documents,
            "count": len(documents)
        })
        
    except Exception as e:
        api_logger.exception("Error in /documents/ingested: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/ingested", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/documents/directory", methods=["GET"])
def get_directory_documents():
    """Lista todos os documentos no diretório com seu status de ingestão."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/directory", "GET")
    
    try:
        document_files = get_all_documents(DOCUMENTS_DIR)
        ingested_docs = _ingestion_repo.list_all()
        
        # Criar mapa de caminhos para busca rápida
        ingested_map = {doc["file_path"]: doc for doc in ingested_docs}
        
        results = []
        for doc_path in document_files:
            file_path_str = str(doc_path)
            file_name = doc_path.name
            
            try:
                file_size = doc_path.stat().st_size
            except:
                file_size = 0
            
            existing = ingested_map.get(file_path_str)
            
            status = "not_processed"
            collection_id = "default"
            chunks_count = 0
            ingested_at = None
            
            if existing:
                try:
                    current_hash = _calculate_file_hash(doc_path)
                    if existing["file_hash"] == current_hash:
                        status = "ok"
                    else:
                        status = "outdated"
                except Exception as e:
                    api_logger.warning("Could not calculate hash for %s: %s", file_name, e)
                    status = "error"
                
                collection_id = existing.get("collection_id", "default")
                chunks_count = existing.get("chunks_count", 0)
                ingested_at = existing.get("ingested_at")
                if hasattr(ingested_at, "isoformat"):
                    ingested_at = ingested_at.isoformat()
            else:
                # Tentar determinar coleção pelo path mesmo se não ingerido
                try:
                    relative_path = doc_path.relative_to(DOCUMENTS_DIR)
                    collection_id = relative_path.parts[0] if len(relative_path.parts) > 1 else "default"
                except ValueError:
                    collection_id = "default"

            results.append({
                "file_name": file_name,
                "file_path": file_path_str,
                "file_size": file_size,
                "status": status,
                "collection_id": collection_id,
                "chunks_count": chunks_count,
                "ingested_at": ingested_at
            })
            
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/directory", 200, time.time() - start_time)
        return jsonify({
            "documents": results,
            "count": len(results)
        })
        
    except Exception as e:
        api_logger.exception("Error in /documents/directory: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/directory", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/documents/delete", methods=["POST"])
def delete_ingested_document():
    """Deleta um documento e todos os seus chunks do banco."""
    start_time = time.time()
    data = request.get_json() or {}
    api_logger.info("API Request | endpoint=%s | method=%s | body=%s", "/api/documents/delete", "POST", data)
    
    if "file_path" not in data:
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/delete", 400, time.time() - start_time)
        return jsonify({"error": "Campo 'file_path' é obrigatório"}), 400
    
    file_path = data["file_path"]
    
    try:
        existing = _ingestion_repo.find_by_path(file_path)
        if not existing:
            api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                           "/api/documents/delete", 404, time.time() - start_time)
            return jsonify({"error": "Documento não encontrado"}), 404
        
        chunks_removed = _doc_repo.delete_by_source(file_path)
        _ingestion_repo.delete_by_path(file_path)
        
        api_logger.info("Document deleted: %s, %d chunks removed", file_path, chunks_removed)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/delete", 200, time.time() - start_time)
        
        return jsonify({
            "message": "Documento removido com sucesso",
            "file_path": file_path,
            "chunks_removed": chunks_removed
        })
        
    except Exception as e:
        api_logger.exception("Error deleting document: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/delete", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/documents/scan", methods=["GET"])
def scan_pending_documents():
    """Retorna lista de documentos que precisam de atualização."""
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/scan", "GET")
    
    try:
        pending = _scan_documents()
        duration = time.time() - start_time
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/scan", 200, duration)
        
        return jsonify({
            "pending": pending,
            "count": len(pending)
        }), 200
    except Exception as e:
        api_logger.exception("Error scanning documents: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/scan", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/documents/scan-with-selection", methods=["GET"])
def scan_with_selection():
    """
    Retorna lista de documentos pendentes para seleção de chunking type.
    
    Similar ao /scan, mas inclui campo 'chunkingType' com valor padrão 'hierarchical'.
    Usado pelo frontend para mostrar modal onde usuário escolhe tipo de chunking.
    """
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/scan-with-selection", "GET")
    
    try:
        pending = _scan_documents()
        
        # Adicionar campo chunkingType (default: hierarchical)
        pending_with_chunking = [
            {
                "file": p["file"],
                "path": p["path"],
                "reason": p["reason"],
                "size": p["size"],
                "chunkingType": "hierarchical"  # Default
            }
            for p in pending
        ]
        
        duration = time.time() - start_time
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/scan-with-selection", 200, duration)
        
        return jsonify({
            "pending": pending_with_chunking,
            "count": len(pending_with_chunking)
        }), 200
    except Exception as e:
        api_logger.exception("Error scanning documents with selection: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/scan-with-selection", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@documents_bp.route("/documents/scan-all", methods=["GET"])
def scan_all_documents():
    """
    Retorna lista de TODOS os documentos no diretório para seleção de chunking type.
    
    Usado no fluxo de 'Reprocessar Base' para mostrar todos os documentos antes
    de limpar a base de conhecimento e reiniciar a ingestão.
    """
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/scan-all", "GET")
    
    try:
        all_document_files = get_all_documents(DOCUMENTS_DIR)
        
        # Adicionar campo chunkingType (default: hierarchical)
        all_with_chunking = []
        for doc_path in all_document_files:
            try:
                file_size = doc_path.stat().st_size
                all_with_chunking.append({
                    "file": doc_path.name,
                    "path": str(doc_path),
                    "reason": "reprocess",  # Indica que é para reprocessamento completo
                    "size": file_size,
                    "chunkingType": "hierarchical"  # Default
                })
            except Exception as e:
                api_logger.warning("Could not scan %s: %s", doc_path, e)
    
        duration = time.time() - start_time
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/scan-all", 200, duration)
        
        return jsonify({
            "pending": all_with_chunking,
            "count": len(all_with_chunking)
        })
    
    except Exception as e:
        api_logger.exception("Error scanning all documents: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/scan-all", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Endpoints de Ingestão em Massa
# =============================================================================
@documents_bp.route("/documents/ingest-all", methods=["POST"])
@limiter.limit(LIMITS["ingest"])
def start_bulk_ingestion():
    """
    Inicia ingestão em massa de todos os documentos do diretório.
    
    Body:
    {
        "force": false,
        "files": [  // Opcional: lista de arquivos específicos com chunking_type
            {"file_path": "/path/to/file.pdf", "chunking_type": "hierarchical"},
            {"file_path": "/path/to/file2.pdf", "chunking_type": "sentence"}
        ]
    }
    """
    global _bulk_ingestion_status
    
    start_time = time.time()
    data = request.get_json() or {}
    api_logger.info("API Request | endpoint=%s | method=%s | body=%s", "/api/documents/ingest-all", "POST", data)
    
    force = data.get("force", False)
    files_with_chunking = data.get("files", None)
    
    # Verificar se files_with_chunking está no formato correto
    if files_with_chunking and isinstance(files_with_chunking, list):
        # Verificar se é formato antigo (lista de strings) ou novo (lista de dicts)
        if files_with_chunking and isinstance(files_with_chunking[0], str):
            # Formato antigo: converter para novo
            files_with_chunking = [
                {"file_path": f, "chunking_type": "hierarchical"}
                for f in files_with_chunking
            ]
        total_to_process = len(files_with_chunking)
    elif force:
        all_document_files = get_all_documents(DOCUMENTS_DIR)
        total_to_process = len(all_document_files)
    else:
        pending = _scan_documents()
        total_to_process = len(pending)
        
    with _bulk_ingestion_lock:
        if _bulk_ingestion_status["running"]:
            api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                           "/api/documents/ingest-all", 409, time.time() - start_time)
            return jsonify({"error": "Ingestão já está em andamento"}), 409
        
        _bulk_ingestion_status["running"] = True
        _bulk_ingestion_status["progress"] = 0
        _bulk_ingestion_status["total"] = total_to_process
        _bulk_ingestion_status["current_file"] = None
        _bulk_ingestion_status["message"] = "Iniciando..."
        _bulk_ingestion_status["results"] = []
    
    thread = threading.Thread(target=_run_bulk_ingestion, args=(force, None, files_with_chunking))
    thread.daemon = True
    thread.start()
    
    api_logger.info("Bulk ingestion started: %d files to process (force=%s)", total_to_process, force)
    api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                   "/api/documents/ingest-all", 202, time.time() - start_time)
    
    return jsonify({
        "message": "Ingestão iniciada",
        "total_files": total_to_process
    }), 202


@documents_bp.route("/documents/ingest-status", methods=["GET"])
def get_bulk_ingestion_status():
    """Retorna o status da ingestão em massa."""
    with _bulk_ingestion_lock:
        status = dict(_bulk_ingestion_status)
    
    return jsonify(status), 200


@documents_bp.route("/documents/reprocess", methods=["POST"])
def reprocess_knowledge_base():
    """
    Limpa toda a base de conhecimento e reinicia ingestão.
    
    Body:
    {
        "files": [  // Opcional: lista de arquivos específicos com chunking_type
            {"file_path": "/path/to/file.pdf", "chunking_type": "hierarchical"},
            {"file_path": "/path/to/file2.pdf", "chunking_type": "sentence"}
        ]
    }
    """
    global _bulk_ingestion_status
    
    start_time = time.time()
    api_logger.info("API Request | endpoint=%s | method=%s", "/api/documents/reprocess", "POST")
    
    with _bulk_ingestion_lock:
        if _bulk_ingestion_status["running"]:
            api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                           "/api/documents/reprocess", 409, time.time() - start_time)
            return jsonify({"error": "Ingestão já está em andamento"}), 409
    
    data = request.get_json() or {}
    files_with_chunking = data.get("files", None)
    
    try:
        # Limpar base de dados
        doc_cleared = _doc_repo.clear_all()
        ing_cleared = _ingestion_repo.clear_all()
        cleared = {"chunks_deleted": doc_cleared, "control_records_deleted": ing_cleared}
        
        with _bulk_ingestion_lock:
            _bulk_ingestion_status["running"] = True
            _bulk_ingestion_status["progress"] = 0
            _bulk_ingestion_status["total"] = 0
            _bulk_ingestion_status["current_file"] = None
            _bulk_ingestion_status["message"] = "Base limpa. Iniciando reprocessamento..."
            _bulk_ingestion_status["results"] = []
        
        # Iniciar thread de ingestão com clear_database=True
        thread = threading.Thread(
            target=_run_bulk_ingestion,
            args=(True, None, files_with_chunking, True)
        )
        thread.daemon = True
        thread.start()
        
        total_files = len(get_all_documents(DOCUMENTS_DIR))
        api_logger.info("Reprocessing started: cleared %s, processing %d files", cleared, total_files)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/reprocess", 202, time.time() - start_time)
        
        return jsonify({
            "message": "Reprocessamento iniciado",
            "cleared": cleared,
            "total_files": total_files
        }), 202
        
    except Exception as e:
        api_logger.exception("Error starting reprocess: %s", e)
        api_logger.info("API Response | endpoint=%s | status_code=%d | duration=%.3fs",
                       "/api/documents/reprocess", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
