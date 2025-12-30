
import sys
import os
from pathlib import Path

# Adicionar root ao path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.ingestion import process_document
from src.data.database import insert_documents_batch, get_parent_content, search_similar
from src.core.embeddings import get_embedding
from src.core.rag import query_rag

def verify():
    test_file = Path('test_hierarchical.txt')
    print(f"--- Verificando Ingestão de {test_file} ---")
    
    # 1. Processar documento
    chunks = process_document(test_file)
    print(f"Gerados {len(chunks)} chunks no total.")
    
    parents = [c for c in chunks if c['metadata'].get('chunk_type') == 'parent']
    children = [c for c in chunks if c['metadata'].get('chunk_type') == 'child']
    
    print(f"Chunks Pais: {len(parents)}")
    print(f"Chunks Filhos: {len(children)}")
    
    if len(parents) == 0 or len(children) == 0:
        print("ERRO: Hierarchical chunking não gerou pais ou filhos.")
        return
    
    # 2. Inserir no Banco (precisa de embeddings)
    print("\n--- Gerando embeddings e inserindo no banco ---")
    texts = [c['content'] for c in chunks]
    from src.core.embeddings import get_embeddings_batch
    embeddings = get_embeddings_batch(texts)
    
    for chunk, emb in zip(chunks, embeddings):
        chunk['embedding'] = emb
        chunk['collection_id'] = 'test_hierarchical'
        
    success, msg = insert_documents_batch(chunks)
    if not success:
        print(f"ERRO ao inserir no banco: {msg}")
        return
    print("Inserção concluída com sucesso.")
    
    # 3. Testar Recuperação de Pai
    print("\n--- Testando Recuperação de Contexto Expandido ---")
    child = children[0]
    parent_idx = child['metadata']['parent_index']
    source_path = child['metadata']['source_path']
    
    parent_text = get_parent_content(source_path, parent_idx)
    if parent_text:
        print(f"SUCESSO: Conteúdo do pai recuperado ({len(parent_text)} chars).")
        print(f"Snippet do pai: {parent_text[:100]}...")
    else:
        print("ERRO: Não foi possível recuperar o conteúdo do pai.")
        
    # 4. Testar Pipeline RAG (End-to-End)
    print("\n--- Testando Pipeline RAG (End-to-End) ---")
    question = "O que é o Sol?"
    response = query_rag(question, collection_id='test_hierarchical', debug_mode=True)
    
    print(f"Pergunta: {question}")
    print(f"Resposta: {response['answer'][:200]}...")
    
    # Verificar se o contexto usado foi expandido
    context_used = response.get('debug_info', {}).get('context_used', '')
    if 'CONTEÚDO EXPANDIDO' in context_used:
        print("SUCESSO: O pipeline RAG usou o contexto expandido (Pai).")
    else:
        print("AVISO: 'CONTEÚDO EXPANDIDO' não encontrado no contexto usado. Verifique o log.")

if __name__ == "__main__":
    verify()
