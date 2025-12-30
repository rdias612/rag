"""
Repository para operações de ingestão de documentos.
"""
import time
from typing import Optional

from src.data.repositories.base import BaseRepository
from src.core.logger import db_logger


class IngestionRepository(BaseRepository):
    """Gerencia controle de ingestão de documentos."""
    
    def create(self, file_path: str, file_hash: str, file_size: int,
               collection_id: str = "default", chunks_count: int = 0,
               status: str = "success") -> int:
        """Registra um documento como ingerido (ou atualiza se já existir)."""
        start_time = time.time()
        
        with self._get_cursor() as cur:
            cur.execute("""
                INSERT INTO documentos_ingeridos 
                    (file_path, file_hash, file_size, collection_id, chunks_count, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_path) DO UPDATE SET
                    file_hash = EXCLUDED.file_hash,
                    file_size = EXCLUDED.file_size,
                    collection_id = EXCLUDED.collection_id,
                    chunks_count = EXCLUDED.chunks_count,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (file_path, file_hash, file_size, collection_id, chunks_count, status))
            doc_id = cur.fetchone()[0]
        
        duration = time.time() - start_time
        db_logger.info(f"Registered ingested document: {file_path} (ID: {doc_id}) in {duration:.2f}s")
        return doc_id
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """Busca documento ingerido por ID."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT id, file_path, file_hash, file_size, collection_id,
                       chunks_count, status, ingested_at, updated_at
                FROM documentos_ingeridos
                WHERE id = %s
            """, (id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def find_by_path(self, file_path: str) -> Optional[dict]:
        """Busca documento ingerido por caminho do arquivo."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("""
                SELECT id, file_path, file_hash, file_size, collection_id,
                       chunks_count, status, ingested_at, updated_at
                FROM documentos_ingeridos
                WHERE file_path = %s
            """, (file_path,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def list_all(self, collection_id: Optional[str] = None) -> list[dict]:
        """Lista todos os documentos ingeridos."""
        with self._get_cursor(dict_cursor=True) as cur:
            if collection_id:
                cur.execute("""
                    SELECT id, file_path, file_hash, file_size, collection_id,
                           chunks_count, status, ingested_at, updated_at
                    FROM documentos_ingeridos
                    WHERE collection_id = %s
                    ORDER BY ingested_at DESC
                """, (collection_id,))
            else:
                cur.execute("""
                    SELECT id, file_path, file_hash, file_size, collection_id,
                           chunks_count, status, ingested_at, updated_at
                    FROM documentos_ingeridos
                    ORDER BY ingested_at DESC
                """)
            return [dict(row) for row in cur.fetchall()]
    
    def delete_by_path(self, file_path: str) -> bool:
        """Remove o registro de um documento ingerido."""
        with self._get_cursor() as cur:
            cur.execute("""
                DELETE FROM documentos_ingeridos
                WHERE file_path = %s
            """, (file_path,))
            return cur.rowcount > 0
    
    def clear_all(self) -> int:
        """Remove todos os registros de ingestão."""
        with self._get_cursor() as cur:
            cur.execute("DELETE FROM documentos_ingeridos")
            return cur.rowcount
