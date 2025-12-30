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
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DOCUMENTS_DIR
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
from src.data.ingestion import process_document, get_document_stats, get_all_documents, SUPPORTED_EXTENSIONS
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
    print("🔍 Verificando serviços...\n")
    
    # Banco de dados
    print("📊 PostgreSQL + pgvector:")
    if check_connection():
        print("   ✅ Conectado!")
    else:
        print("   ❌ Não conectado. Verifique se o container está rodando.")
        return False
    
    # LM Studio - Embeddings
    print("\n🔢 LM Studio (Embeddings):")
    if check_embedding_service():
        print("   ✅ Serviço de embeddings funcionando!")
    else:
        print("   ❌ Serviço de embeddings não disponível.")
        print("   Verifique se o LM Studio está rodando com o modelo Nomic Embed.")
        return False
    
    print("\n✅ Todos os serviços estão funcionando!")
    return True


def show_stats():
    """Mostra estatísticas dos documentos."""
    print("📊 Estatísticas\n")
    
    # Documentos no diretório
    print(f"📁 Diretório: {DOCUMENTS_DIR}")
    
    if DOCUMENTS_DIR.exists():
        stats = get_document_stats()
        print(f"   Total de arquivos: {stats['total_files']}")
        
        # Mostrar por tipo
        if stats.get('files_by_type'):
            print("   Por formato:")
            for ext, count in sorted(stats['files_by_type'].items()):
                print(f"     - {ext}: {count}")
        
        print(f"   Tamanho total: {stats['total_size_mb']} MB")
        print(f"   Formatos suportados: {', '.join(stats.get('supported_formats', []))}")
        
        if stats['files']:
            print("\n   Arquivos:")
            for f in stats['files'][:10]:
                print(f"     - {f}")
            if len(stats['files']) > 10:
                print(f"     ... e mais {len(stats['files']) - 10} arquivos")
    else:
        print("   ⚠️ Diretório não encontrado!")
    
    # Documentos no banco
    print(f"\n💾 Banco de dados:")
    try:
        count = get_document_count()
        print(f"   Chunks indexados: {count}")
    except Exception as e:
        print(f"   ❌ Erro ao consultar banco: {e}")


def show_ingested_documents():
    """Mostra lista de documentos já ingeridos."""
    print("📋 Documentos Ingeridos\n")
    
    try:
        documents = list_ingested_documents()
        
        if not documents:
            print("   Nenhum documento registrado ainda.")
            return
        
        print(f"   Total: {len(documents)} documento(s)\n")
        
        for doc in documents:
            file_name = Path(doc['file_path']).name
            size_mb = doc['file_size'] / (1024 * 1024)
            ingested_at = doc['ingested_at'].strftime("%Y-%m-%d %H:%M")
            status_icon = "✅" if doc['status'] == 'success' else "⚠️"
            
            print(f"   {status_icon} {file_name}")
            print(f"      Coleção: {doc['collection_id']} | Chunks: {doc['chunks_count']} | {size_mb:.2f} MB")
            print(f"      Ingerido em: {ingested_at}")
            print()
            
    except Exception as e:
        print(f"   ❌ Erro ao listar documentos: {e}")


def run_ingestion(force: bool = False):
    """Executa o processo de ingestão completo."""
    print("🚀 Iniciando ingestão de documentos\n")
    
    if force:
        print("⚠️  Modo FORCE ativado - todos os documentos serão re-processados\n")
    
    # Verificar serviços
    if not check_services():
        print("\n❌ Abortando: serviços não estão disponíveis.")
        return
    
    # Inicializar banco
    print("\n🔧 Inicializando banco de dados...")
    init_database()
    
    # Verificar diretório
    if not DOCUMENTS_DIR.exists():
        print(f"\n❌ Diretório não encontrado: {DOCUMENTS_DIR}")
        return
    
    # Listar todos os documentos
    document_files = get_all_documents(DOCUMENTS_DIR)
    
    if not document_files:
        print(f"\n⚠️ Nenhum documento encontrado em: {DOCUMENTS_DIR}")
        return
    
    print(f"\n📂 Encontrados {len(document_files)} documento(s) no diretório\n")
    
    # Separar documentos: novos, modificados, já ingeridos
    docs_to_process = []
    docs_skipped = []
    docs_modified = []
    
    for doc_path in document_files:
        file_path_str = str(doc_path)
        file_hash = calculate_file_hash(doc_path)
        file_size = doc_path.stat().st_size
        
        existing = get_ingested_document(file_path_str)
        
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
        print(f"⏭️  Pulando {len(docs_skipped)} documento(s) já ingerido(s)")
    if docs_modified:
        print(f"🔄 Re-ingerindo {len(docs_modified)} documento(s) modificado(s)")
    if docs_to_process:
        print(f"📥 Processando {len(docs_to_process)} novo(s) documento(s)")
    
    if not docs_to_process and not docs_modified:
        print("\n✅ Nenhum documento novo ou modificado para processar.")
        return
    
    # Processar documentos modificados (remover chunks antigos primeiro)
    for doc_path, file_hash, file_size, existing in docs_modified:
        print(f"\n🔄 Removendo chunks antigos de: {doc_path.name}")
        removed = remove_document_chunks_by_source(str(doc_path))
        print(f"   Removidos {removed} chunk(s)")
        docs_to_process.append((doc_path, file_hash, file_size))
    
    print(f"\n� Total a processar: {len(docs_to_process)} documento(s)\n")
    
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
        
        print(f"📄 [{i}/{len(docs_to_process)}] Processando: {doc_path.name} (Coleção: {collection_id})")
        
        try:
            chunks = process_document(doc_path)
            
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
            
            print(f"   ✂️ Gerados {len(chunks)} chunks")
            
        except Exception as e:
            print(f"   ❌ Erro ao processar: {e}")
            # Registrar como erro
            register_ingested_document(
                file_path=str(doc_path),
                file_hash=file_hash,
                file_size=file_size,
                collection_id=collection_id,
                chunks_count=0,
                status="error"
            )
            continue
    
    if not all_chunks:
        print("\n⚠️ Nenhum chunk gerado. Verifique os documentos.")
        return
    
    print(f"\n📊 Total de chunks: {len(all_chunks)}")
    
    # Gerar embeddings em batch
    print("\n🔢 Gerando embeddings...")
    texts = [chunk["content"] for chunk in all_chunks]
    embeddings = get_embeddings_batch(texts)
    
    # Preparar para inserção
    print("\n💾 Inserindo no banco de dados...")
    documents_to_insert = []
    for chunk, embedding in zip(all_chunks, embeddings):
        documents_to_insert.append({
            "content": chunk["content"],
            "metadata": chunk["metadata"],
            "embedding": embedding,
            "collection_id": chunk.get("collection_id", "default")
        })
    
    # Inserir em batches
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(documents_to_insert), batch_size):
        batch = documents_to_insert[i:i + batch_size]
        inserted = insert_documents_batch(batch)
        total_inserted += inserted
        print(f"   Inseridos: {total_inserted}/{len(documents_to_insert)}")
    
    # Registrar documentos como ingeridos
    print("\n📝 Registrando documentos processados...")
    for file_path_str, info in doc_chunk_counts.items():
        register_ingested_document(
            file_path=file_path_str,
            file_hash=info["hash"],
            file_size=info["size"],
            collection_id=info["collection_id"],
            chunks_count=info["chunks"],
            status="success"
        )
    
    print(f"\n✅ Ingestão completa!")
    print(f"   📄 Documentos processados: {len(doc_chunk_counts)}")
    print(f"   📦 Chunks indexados: {total_inserted}")


def clear_database():
    """Limpa todos os documentos do banco."""
    print("⚠️ ATENÇÃO: Isso irá remover TODOS os documentos do banco!")
    confirm = input("Digite 'CONFIRMAR' para continuar: ")
    
    if confirm == "CONFIRMAR":
        clear_documents()
        print("✅ Banco limpo!")
    else:
        print("❌ Operação cancelada.")


def main():
    parser = argparse.ArgumentParser(description="Script de ingestão de documentos RAG")
    parser.add_argument("--stats", action="store_true", help="Mostrar estatísticas")
    parser.add_argument("--clear", action="store_true", help="Limpar banco de dados")
    parser.add_argument("--check", action="store_true", help="Verificar serviços")
    parser.add_argument("--force", action="store_true", help="Forçar re-ingestão de todos os documentos")
    parser.add_argument("--list-ingested", action="store_true", help="Listar documentos já ingeridos")
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.clear:
        clear_database()
    elif args.check:
        check_services()
    elif args.list_ingested:
        show_ingested_documents()
    else:
        run_ingestion(force=args.force)


if __name__ == "__main__":
    main()
