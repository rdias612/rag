"""
Script CLI para ingestão de documentos.

Uso:
    python -m scripts.ingest                    # Processa todos os PDFs
    python -m scripts.ingest --stats            # Mostra estatísticas
    python -m scripts.ingest --clear            # Limpa o banco
    python -m scripts.ingest --check            # Verifica serviços
"""
import sys
import argparse
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DOCUMENTS_DIR
from src.data.database import (
    init_database,
    insert_documents_batch,
    get_document_count,
    clear_documents,
    check_connection
)
from src.data.ingestion import process_all_documents, get_document_stats
from src.core.embeddings import get_embeddings_batch, check_embedding_service


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
        print(f"   Arquivos PDF: {stats['total_files']}")
        print(f"   Total de páginas: {stats['total_pages']}")
        print(f"   Tamanho total: {stats['total_size_mb']} MB")
        
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


def run_ingestion():
    """Executa o processo de ingestão completo."""
    print("🚀 Iniciando ingestão de documentos\n")
    
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
    
    # Processar documentos
    print(f"\n📂 Processando documentos de: {DOCUMENTS_DIR}\n")
    
    # Coletar todos os chunks primeiro
    all_chunks = list(process_all_documents())
    
    if not all_chunks:
        print("\n⚠️ Nenhum chunk gerado. Verifique os PDFs.")
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
            "embedding": embedding
        })
    
    # Inserir em batches
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(documents_to_insert), batch_size):
        batch = documents_to_insert[i:i + batch_size]
        inserted = insert_documents_batch(batch)
        total_inserted += inserted
        print(f"   Inseridos: {total_inserted}/{len(documents_to_insert)}")
    
    print(f"\n✅ Ingestão completa! {total_inserted} chunks indexados.")


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
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
    elif args.clear:
        clear_database()
    elif args.check:
        check_services()
    else:
        run_ingestion()


if __name__ == "__main__":
    main()
