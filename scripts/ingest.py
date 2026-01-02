"""
Script CLI para ingestão de documentos.

Uso:
    python -m scripts.ingest                    # Processa todos os PDFs
    python -m scripts.ingest --stats            # Mostra estatísticas
    python -m scripts.ingest --clear            # Limpa o banco
    python -m scripts.ingest --check            # Verifica serviços
    python -m scripts.ingest --force            # Força re-ingestão de todos
    python -m scripts.ingest --list-ingested    # Lista documentos já ingeridos
"""
import sys
import argparse
import hashlib
import time
import logging
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DOCUMENTS_DIR
from src.core.logger import ingestion_logger as logger, setup_logger, log_execution_time
from src.data.database import (
    init_database,
    insert_documents_batch,
    get_document_count,
    clear_documents,
    check_connection,
    get_ingested_document,
    register_ingested_document,
    remove_document_chunks_by_source,
    list_ingested_documents
)
from src.data.ingestion import (
    process_document,
    process_document_with_chunking_type,
    get_document_stats, 
    get_all_documents, 
    SUPPORTED_EXTENSIONS
)
from src.data.repositories.ingestion_repository import IngestionRepository
from src.data.repositories.document_repository import DocumentRepository
from src.core.embeddings import get_embeddings_batch, check_embedding_service


def calculate_file_hash(file_path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def check_services():
    """Verifica se todos os serviços estão funcionando."""
    logger.info("🔍 Verificando serviços...")
    
    # Banco de dados
    logger.info("📊 PostgreSQL + pgvector:")
    if check_connection():
        logger.info("   ✅ Conectado!")
    else:
        logger.error("   ❌ Não conectado. Verifique se o container está rodando.")
        return False
    
    # LM Studio - Embeddings
    logger.info("🔢 LM Studio (Embeddings):")
    if check_embedding_service():
        logger.info("   ✅ Serviço de embeddings funcionando!")
    else:
        logger.error("   ❌ Serviço de embeddings não disponível.")
        logger.error("   Verifique se o LM Studio está rodando com o modelo Nomic Embed.")
        return False
    
    logger.info("✅ Todos os serviços estão funcionando!")
    return True


def show_stats():
    """Mostra estatísticas dos documentos."""
    logger.info("📊 Estatísticas")
    
    # Documentos no diretório
    logger.info(f"📁 Diretório: {DOCUMENTS_DIR}")
    
    if DOCUMENTS_DIR.exists():
        stats = get_document_stats()
        logger.info(f"   Total de arquivos: {stats['total_files']}")
        
        # Mostrar por tipo
        if stats.get('files_by_type'):
            logger.info("   Por formato:")
            for ext, count in sorted(stats['files_by_type'].items()):
                logger.info(f"     - {ext}: {count}")
        
        logger.info(f"   Tamanho total: {stats['total_size_mb']} MB")
        logger.info(f"   Formatos suportados: {', '.join(stats.get('supported_formats', []))}")
        
        if stats['files']:
            logger.info("   Arquivos:")
            for f in stats['files'][:10]:
                logger.info(f"     - {f}")
            if len(stats['files']) > 10:
                logger.info(f"     ... e mais {len(stats['files']) - 10} arquivos")
    else:
        logger.warning("   ⚠️ Diretório não encontrado!")
    
    # Documentos no banco
    logger.info("💾 Banco de dados:")
    try:
        count = get_document_count()
        logger.info(f"   Chunks indexados: {count}")
    except Exception as e:
        logger.error(f"   ❌ Erro ao consultar banco: {e}")


def show_ingested_documents():
    """Mostra lista de documentos já ingeridos."""
    logger.info("📋 Documentos Ingeridos")
    
    try:
        ingestion_repo = IngestionRepository()
        documents = ingestion_repo.list_all()
        
        if not documents:
            logger.info("   Nenhum documento registrado ainda.")
            return
        
        logger.info(f"   Total: {len(documents)} documento(s)")
        
        for doc in documents:
            file_name = Path(doc['file_path']).name
            size_mb = doc['file_size'] / (1024 * 1024)
            ingested_at = doc['ingested_at'].strftime("%Y-%m-%d %H:%M")
            status_icon = "✅" if doc['status'] == 'success' else "⚠️"
            chunking_type = doc.get('chunking_type', 'N/A')
            
            logger.info(f"   {status_icon} {file_name}")
            logger.info(f"      Coleção: {doc['collection_id']} | Chunks: {doc['chunks_count']} | {size_mb:.2f} MB")
            logger.info(f"      Tipo: {chunking_type} | Ingerido em: {ingested_at}")
            
    except Exception as e:
        logger.error(f"   ❌ Erro ao listar documentos: {e}")


def run_ingestion(force: bool = False, chunking_type: str = "hierarchical"):
    """Executa o processo de ingestão completo.
    
    Args:
        force: Força re-ingestão de todos os documentos
        chunking_type: Tipo de chunking a usar ('hierarchical' ou 'sentence')
    """
    start_total = time.time()
    logger.info("🚀 Iniciando ingestão de documentos")
    
    if force:
        logger.warning("⚠️  Modo FORCE ativado - todos os documentos serão re-processados")
    
    # Verificar serviços
    if not check_services():
        logger.error("❌ Abortando: serviços não estão disponíveis.")
        return
    
    # Inicializar banco
    logger.info("🔧 Inicializando banco de dados...")
    init_database()
    
    # Verificar diretório
    if not DOCUMENTS_DIR.exists():
        logger.error(f"❌ Diretório não encontrado: {DOCUMENTS_DIR}")
        return
    
    # Listar todos os documentos
    document_files = get_all_documents(DOCUMENTS_DIR)
    
    if not document_files:
        logger.warning(f"⚠️ Nenhum documento encontrado em: {DOCUMENTS_DIR}")
        return
    
    logger.info(f"🔧 Modo de chunking: {chunking_type}")
    logger.info(f"📂 Encontrados {len(document_files)} documento(s) no diretório")
    
    # Separar documentos: novos, modificados, já ingeridos
    docs_to_process = []
    docs_skipped = []
    docs_modified = []
    
    # Usar repositórios novos
    ingestion_repo = IngestionRepository()
    doc_repo = DocumentRepository()
    
    for doc_path in document_files:
        file_path_str = str(doc_path)
        file_hash = calculate_file_hash(doc_path)
        file_size = doc_path.stat().st_size
        
        existing = ingestion_repo.find_by_path(file_path_str)
        
        if existing:
            if force:
                # Forçar re-ingestão
                docs_modified.append((doc_path, file_hash, file_size, existing))
            elif existing['file_hash'] != file_hash:
                # Arquivo foi modificado
                docs_modified.append((doc_path, file_hash, file_size, existing))
            else:
                # Já ingerido e não modificado
                docs_skipped.append(doc_path)
        else:
            # Novo documento
            docs_to_process.append((doc_path, file_hash, file_size))
    
    # Resumo
    if docs_skipped:
        logger.info(f"⏭️  Pulando {len(docs_skipped)} documento(s) já ingerido(s)")
    if docs_modified:
        logger.info(f"🔄 Re-ingerindo {len(docs_modified)} documento(s) modificado(s)")
    if docs_to_process:
        logger.info(f"📥 Processando {len(docs_to_process)} novo(s) documento(s)")
    
    if not docs_to_process and not docs_modified:
        logger.info("✅ Nenhum documento novo ou modificado para processar.")
        return
    
    # Processar documentos modificados (remover chunks antigos primeiro)
    for doc_path, file_hash, file_size, existing in docs_modified:
        logger.info(f"🔄 Removendo chunks antigos de: {doc_path.name}")
        removed = doc_repo.delete_by_source(str(doc_path))
        logger.debug(f"   Removidos {removed} chunk(s)")
        docs_to_process.append((doc_path, file_hash, file_size))
    
    logger.info(f"📋 Total a processar: {len(docs_to_process)} documento(s)")
    
    # Processar documentos
    all_chunks = []
    doc_chunk_counts = {}  # Para registrar quantos chunks cada documento gerou
    
    for i, (doc_path, file_hash, file_size) in enumerate(docs_to_process, start=1):
        # Determinar collection_id
        try:
            relative_path = doc_path.relative_to(DOCUMENTS_DIR)
            if len(relative_path.parts) > 1:
                collection_id = relative_path.parts[0]
            else:
                collection_id = "default"
        except ValueError:
            collection_id = "default"
        
        logger.info(f"📄 [{i}/{len(docs_to_process)}] Processando: {doc_path.name} (Coleção: {collection_id})")
        start_doc = time.time()
        
        try:
            chunks = process_document_with_chunking_type(doc_path, chunking_type)
            
            # Adicionar collection_id a cada chunk
            for chunk in chunks:
                chunk["collection_id"] = collection_id
            
            all_chunks.extend(chunks)
            doc_chunk_counts[str(doc_path)] = {
                "chunks": len(chunks),
                "hash": file_hash,
                "size": file_size,
                "collection_id": collection_id
            }
            
            duration_doc = time.time() - start_doc
            logger.info(f"   ✂️ Gerados {len(chunks)} chunks em {duration_doc:.2f}s")
            
        except Exception as e:
            logger.error(f"   ❌ Erro ao processar {doc_path.name}: {e}")
            # Registrar como erro
            ingestion_repo.create_or_update(
                file_path=str(doc_path),
                file_hash=file_hash,
                file_size=file_size,
                collection_id=collection_id,
                chunks_count=0,
                status="error",
                chunking_type=chunking_type
            )
            continue
    
    if not all_chunks:
        logger.warning("⚠️ Nenhum chunk gerado. Verifique os documentos.")
        return
    
    logger.info(f"📊 Total de chunks gerados: {len(all_chunks)}")
    
    # Gerar embeddings em batch
    logger.info("🔢 Gerando embeddings...")
    start_emb = time.time()
    texts = [chunk["content"] for chunk in all_chunks]
    embeddings = get_embeddings_batch(texts)
    duration_emb = time.time() - start_emb
    logger.info(f"   ✅ Embeddings gerados em {duration_emb:.2f}s")
    
    # Preparar para inserção
    logger.info("💾 Inserindo no banco de dados...")
    start_db = time.time()
    documents_to_insert = []
    for chunk, embedding in zip(all_chunks, embeddings):
        documents_to_insert.append({
            "content": chunk["content"],
            "metadata": chunk["metadata"],
            "embedding": embedding,
            "collection_id": chunk.get("collection_id", "default")
        })
    
    # Inserir em batches usando repositório novo
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(documents_to_insert), batch_size):
        batch = documents_to_insert[i:i + batch_size]
        inserted = doc_repo.create_batch(batch)
        total_inserted += inserted
        logger.info(f"   Inseridos: {total_inserted}/{len(documents_to_insert)}")
    
    duration_db = time.time() - start_db
    logger.info(f"   ✅ Inserção concluída em {duration_db:.2f}s")
    
    # Registrar documentos como ingeridos
    logger.info("📝 Registrando documentos processados...")
    for file_path_str, info in doc_chunk_counts.items():
        ingestion_repo.create_or_update(
            file_path=file_path_str,
            file_hash=info["hash"],
            file_size=info["size"],
            collection_id=info["collection_id"],
            chunks_count=info["chunks"],
            status="success",
            chunking_type=chunking_type
        )
    
    duration_total = time.time() - start_total
    logger.info(f"✅ Ingestão completa em {duration_total:.2f}s!")
    logger.info(f"   📄 Documentos processados: {len(doc_chunk_counts)}")
    logger.info(f"   📦 Chunks indexados: {total_inserted}")


def clear_database():
    """Limpa todos os documentos do banco."""
    logger.warning("⚠️ ATENÇÃO: Isso irá remover TODOS os documentos do banco!")
    confirm = input("Digite 'CONFIRMAR' para continuar: ")
    
    if confirm == "CONFIRMAR":
        clear_documents()
        logger.info("✅ Banco limpo!")
    else:
        logger.warning("❌ Operação cancelada.")


def main():
    parser = argparse.ArgumentParser(description="Script de ingestão de documentos RAG")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas")
    parser.add_argument("--clear", action="store_true", help="Limpar banco de dados")
    parser.add_argument("--check", action="store_true", help="Verificar serviços")
    parser.add_argument("--force", action="store_true", help="Forçar re-ingestão de todos os documentos")
    parser.add_argument("--list-ingested", action="store_true", help="Listar documentos já ingeridos")
    parser.add_argument("--debug", action="store_true", help="Ativar logs de debug")
    parser.add_argument("--chunking-type", choices=["hierarchical", "sentence"], 
                       default="hierarchical", help="Tipo de chunking: hierarchical (parent-child) ou sentence (sentence window)")
    
    args = parser.parse_args()
    
    # Configurar nível de log
    if args.debug:
        # Configurar todos os loggers relevantes para DEBUG
        for logger_name in ["rag", "rag.ingestion", "rag.database", "rag.embeddings"]:
            l = logging.getLogger(logger_name)
            l.setLevel(logging.DEBUG)
            for handler in l.handlers:
                if isinstance(handler, logging.StreamHandler):
                    handler.setLevel(logging.DEBUG)
        logger.debug("Logs de DEBUG ativados")
    
    if args.stats:
        show_stats()
    elif args.clear:
        clear_database()
    elif args.check:
        check_services()
    elif args.list_ingested:
        show_ingested_documents()
    else:
        run_ingestion(force=args.force, chunking_type=args.chunking_type)


if __name__ == "__main__":
    main()
