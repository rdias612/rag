
import sys
import os
import time

# Adicionar root ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.embeddings import get_embedding
from src.core.rag import _search_documents
from src.core.llm import generate_response
from src.core.rag import query_rag_with_history

def test_embeddings():
    print("\n--- Testando Embeddings ---")
    start = time.time()
    try:
        emb = get_embedding("O que é o protocolo gwprp?")
        print(f"Sucesso! Dimensão: {len(emb)}")
        print(f"Tempo: {time.time() - start:.2f}s")
        return emb
    except Exception as e:
        print(f"ERRO: {e}")
        return None

def test_retrieval(embedding):
    print("\n--- Testando Recuperação ---")
    start = time.time()
    try:
        docs, metrics = _search_documents("O que é o protocolo gwprp?", embedding, top_k=5)
        print(f"Sucesso! {len(docs)} documentos encontrados.")
        print(f"Métricas: {metrics}")
        for i, doc in enumerate(docs):
            print(f"  {i+1}. {doc['metadata'].get('source')} (Similarity: {doc.get('similarity', 0):.4f})")
        print(f"Tempo: {time.time() - start:.2f}s")
        return docs
    except Exception as e:
        print(f"ERRO: {e}")
        return None

def test_llm():
    print("\n--- Testando LLM ---")
    start = time.time()
    try:
        response = generate_response("Responda apenas 'OK' se você estiver funcionando.")
        print(f"Resposta: {response}")
        print(f"Tempo: {time.time() - start:.2f}s")
        return response
    except Exception as e:
        print(f"ERRO: {e}")
        return None

if __name__ == "__main__":
    print("Iniciando diagnósticos RAG...")
    
    emb = test_embeddings()
    if emb:
        docs = test_retrieval(emb)
    
    test_llm()
    
    print("\n--- Teste Completo (Chat) ---")
    start = time.time()
    try:
        # Tentar a função completa
        result = query_rag_with_history("O que é o protocolo gwprp?")
        print("Sucesso no pipeline completo!")
        print(f"Resposta curta: {result['answer'][:100]}...")
        print(f"Tempo total: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"ERRO no pipeline completo: {e}")
