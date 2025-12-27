
import sys
import os

# Adicionar root ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.database import get_connection

def inspect_indexes():
    print("Inspecionando índices da tabela 'documentos'...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    i.relname as index_name,
                    a.attname as column_name,
                    am.amname as index_type
                FROM
                    pg_class t,
                    pg_class i,
                    pg_index ix,
                    pg_attribute a,
                    pg_am am
                WHERE
                    t.oid = ix.indrelid
                    AND i.oid = ix.indexrelid
                    AND a.attrelid = t.oid
                    AND a.attnum = ANY(ix.indkey)
                    AND t.relkind = 'r'
                    AND t.relname = 'documentos'
                    AND i.relam = am.oid;
            """)
            for row in cur.fetchall():
                print(f"Índice: {row[0]} | Coluna: {row[1]} | Tipo: {row[2]}")

if __name__ == "__main__":
    inspect_indexes()
