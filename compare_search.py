
import sys
import os
import time

# Adicionar root ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.embeddings import get_embedding
from src.core.rag import _search_documents
from src.data.database import search_similar
from src.data.hybrid_search import search_hybrid, check_fulltext_ready

def compare_searches(question):
    print(f"\nComparando buscas para: '{question}'")
    emb = get_embedding(question)
    
    # 1. Busca Vetorial (Coleção específica 'mestrado')
    print("\n--- 1. Busca Vetorial (Filtro 'mestrado') ---")
    start = time.time()
    results_v = search_similar(emb, top_k=5, min_similarity=0.4, collection_id="mestrado")
    print(f"Resultados: {len(results_v)}")
    for r in results_v:
        print(f"  - Score: {r['similarity']:.4f} | Text: {r['content'][:100]}...")
    print(f"Tempo: {time.time() - start:.2f}s")

    # 2. Busca Híbrida (Todas as coleções)
    print("\n--- 2. Busca Híbrida (Global - Todas as coleções) ---")
    start = time.time()
    results_h_global = search_hybrid(question, emb, top_k=5, min_similarity=0.4)
    print(f"Resultados: {len(results_h_global)}")
    for r in results_h_global:
        print(f"  - Hybrid Score: {r['hybrid_score']:.4f} | Similarity: {r['similarity']:.4f} | Text: {r['content'][:100]}...")
    print(f"Tempo: {time.time() - start:.2f}s")
    
    # 3. Busca Híbrida (Filtro 'mestrado')
    print("\n--- 3. Busca Híbrida (Filtro 'mestrado') ---")
    start = time.time()
    results_h_local = search_hybrid(question, emb, top_k=5, min_similarity=0.4, collection_id="mestrado")
    print(f"Resultados: {len(results_h_local)}")
    for r in results_h_local:
        print(f"  - Hybrid Score: {r['hybrid_score']:.4f} | Similarity: {r['similarity']:.4f} | Text: {r['content'][:100]}...")
    print(f"Tempo: {time.time() - start:.2f}s")

if __name__ == "__main__":
    compare_searches("o que é o protocolo gwprp?")
