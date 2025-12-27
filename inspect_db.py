
import sys
import os

# Adicionar root ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.database import get_connection
from src.core.embeddings import get_embedding

def test_global_vs_local(question):
    print(f"\nTestando busca para: '{question}'")
    emb = get_embedding(question)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Busca Global sem filtro
            print("\n--- Top 10 Global (sem filtro) ---")
            cur.execute("""
                SELECT 
                    id, 
                    collection_id, 
                    1 - (embedding <=> %s::vector) as similarity,
                    LEFT(content, 100)
                FROM documentos
                ORDER BY embedding <=> %s::vector
                LIMIT 10
            """, (emb, emb))
            global_results = cur.fetchall()
            for row in global_results:
                print(f"ID: {row[0]:4} | Coll: {row[1]:10} | Sim: {row[2]:.4f} | Text: {row[3]}...")

            # 2. Busca na Coleção 'mestrado'
            print("\n--- Top 10 Coleção 'mestrado' ---")
            cur.execute("""
                SELECT 
                    id, 
                    collection_id, 
                    1 - (embedding <=> %s::vector) as similarity,
                    LEFT(content, 100)
                FROM documentos
                WHERE collection_id = 'mestrado'
                ORDER BY embedding <=> %s::vector
                LIMIT 10
            """, (emb, emb))
            local_results = cur.fetchall()
            for row in local_results:
                print(f"ID: {row[0]:4} | Coll: {row[1]:10} | Sim: {row[2]:.4f} | Text: {row[3]}...")
            
            # 3. Verificar se o melhor de 'mestrado' está no top 10 global
            if local_results and global_results:
                best_local_id = local_results[0][0]
                found_globally = any(row[0] == best_local_id for row in global_results)
                print(f"\nMelhor de 'mestrado' (ID {best_local_id}) está no Top 10 Global? {'SIM' if found_globally else 'NÃO'}")
                
                if not found_globally:
                    # Encontrar a posição global do melhor local
                    cur.execute("""
                        WITH ranked AS (
                            SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) as pos
                            FROM documentos
                        )
                        SELECT pos FROM ranked WHERE id = %s
                    """, (emb, best_local_id))
                    pos = cur.fetchone()
                    print(f"Posição global do melhor local: {pos[0] if pos else 'N/A'}")

if __name__ == "__main__":
    test_global_vs_local("o que é o protocolo gwprp?")
