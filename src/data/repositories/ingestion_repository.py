"""
Repository para controle de ingestão de documentos.
"""
import time
from typing import Optional, List

from src.data.repositories.base import BaseRepository


class IngestionRepository(BaseRepository):
    """Gerencia registros de ingestão na tabela documentos_ingeridos."""
    
    def find_by_path(self, file_path: str) -> Optional[dict]:
        """
        Verifica se um documento já foi ingerido.
        
        Args:
            file_path: Caminho absoluto do arquivo
            
        Returns:
            Dict com informações do documento se existir, None caso contrário
        """
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute(
                """
                SELECT id, file_path, file_hash, file_size, collection_id, 
                       chunks_count, status, ingested_at, updated_at, chunking_type
                FROM documentos_ingeridos
                WHERE file_path = %s
                """,
                (file_path,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """
        Busca um registro de ingestão pelo ID.
        
        Args:
            id: ID do registro
            
        Returns:
            Dict com informações do documento se existir, None caso contrário
        """
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute(
                """
                SELECT id, file_path, file_hash, file_size, collection_id, 
                       chunks_count, status, ingested_at, updated_at, chunking_type
                FROM documentos_ingeridos
                WHERE id = %s
                """,
                (id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    
    def create(self, file_path: str, file_hash: str, file_size: int,
               collection_id: str = "default", chunks_count: int = 0,
               status: str = "success", chunking_type: Optional[str] = None) -> int:
        """
        Registra um novo documento como ingerido.
        
        Args:
            file_path: Caminho absoluto do arquivo
            file_hash: Hash SHA-256 do conteúdo
            file_size: Tamanho em bytes
            collection_id: ID da coleção
            chunks_count: Número de chunks gerados
            status: Status da ingestão (success, error, partial)
            chunking_type: Tipo de chunking usado (hierarchical, sentence, ou None)
            
        Returns:
            ID do registro criado
        """
        start_time = time.time()
        print(f"DB INSERT | table=documentos_ingeridos | file_path={file_path}")
        
        with self._get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO documentos_ingeridos 
                    (file_path, file_hash, file_size, collection_id, chunks_count, status, chunking_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (file_path, file_hash, file_size, collection_id, chunks_count, status, chunking_type)
            )
            doc_id = cur.fetchone()[0]
        
        duration = time.time() - start_time
        print(f"DB INSERT Result | affected_rows=1 | duration={duration:.3f}s")
        print(f"Registered ingested document: {file_path} (ID: {doc_id}) in {duration:.2f}s")
        
        return doc_id
    
    def update(self, file_path: str, file_hash: str, file_size: int,
               collection_id: str = "default", chunks_count: int = 0,
               status: str = "success", chunking_type: Optional[str] = None) -> bool:
        """
        Atualiza um registro de documento existente.
        
        Args:
            file_path: Caminho absoluto do arquivo
            file_hash: Hash SHA-256 do conteúdo
            file_size: Tamanho em bytes
            collection_id: ID da coleção
            chunks_count: Número de chunks gerados
            status: Status da ingestão (success, error, partial)
            chunking_type: Tipo de chunking usado (hierarchical, sentence, ou None)
            
        Returns:
            True se atualizado, False se não encontrado
        """
        start_time = time.time()
        print(f"DB UPDATE | table=documentos_ingeridos | file_path={file_path}")
        
        with self._get_cursor() as cur:
            cur.execute(
                """
                UPDATE documentos_ingeridos
                SET file_hash = %s,
                    file_size = %s,
                    collection_id = %s,
                    chunks_count = %s,
                    status = %s,
                    chunking_type = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE file_path = %s
                """,
                (file_hash, file_size, collection_id, chunks_count, status, chunking_type, file_path)
            )
            updated = cur.rowcount > 0
        
        duration = time.time() - start_time
        if updated:
            print(f"DB UPDATE Result | affected_rows=1 | duration={duration:.3f}s")
            print(f"Updated ingested document: {file_path} in {duration:.2f}s")
        
        return updated
    
    def create_or_update(self, file_path: str, file_hash: str, file_size: int,
                        collection_id: str = "default", chunks_count: int = 0,
                        status: str = "success", chunking_type: Optional[str] = None) -> int:
        """
        Registra ou atualiza um documento ingerido.
        
        Args:
            file_path: Caminho absoluto do arquivo
            file_hash: Hash SHA-256 do conteúdo
            file_size: Tamanho em bytes
            collection_id: ID da coleção
            chunks_count: Número de chunks gerados
            status: Status da ingestão (success, error, partial)
            chunking_type: Tipo de chunking usado (hierarchical, sentence, ou None)
            
        Returns:
            ID do registro
        """
        # Verificar se já existe
        existing = self.find_by_path(file_path)
        
        if existing:
            # Atualizar
            self.update(
                file_path, file_hash, file_size, collection_id,
                chunks_count, status, chunking_type
            )
            return existing['id']
        else:
            # Criar novo
            return self.create(
                file_path, file_hash, file_size, collection_id,
                chunks_count, status, chunking_type
            )
    
    def list_all(self, collection_id: Optional[str] = None,
                 chunking_type: Optional[str] = None,
                 limit: Optional[int] = None) -> List[dict]:
        """
        Lista documentos ingeridos com filtros opcionais.
        
        Args:
            collection_id: Filtrar por coleção (opcional)
            chunking_type: Filtrar por tipo de chunking (opcional)
            limit: Limite de resultados (opcional)
            
        Returns:
            Lista de documentos ingeridos
        """
        with self._get_cursor(dict_cursor=True) as cur:
            conditions = []
            params = []
            
            if collection_id:
                conditions.append("collection_id = %s")
                params.append(collection_id)
            
            if chunking_type:
                conditions.append("chunking_type = %s")
                params.append(chunking_type)
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            limit_clause = ""
            if limit:
                limit_clause = f"LIMIT {limit}"
            
            query = f"""
                SELECT id, file_path, file_hash, file_size, collection_id, 
                       chunks_count, status, ingested_at, updated_at, chunking_type
                FROM documentos_ingeridos
                {where_clause}
                ORDER BY ingested_at DESC
                {limit_clause}
            """
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    
    def find_by_chunking_type(self, chunking_type: str,
                               collection_id: Optional[str] = None) -> List[str]:
        """
        Lista caminhos de arquivos por tipo de chunking.
        
        Útil para filtrar buscas apenas em documentos com chunking específico.
        
        Args:
            chunking_type: Tipo de chunking ('hierarchical' ou 'sentence')
            collection_id: Filtrar por coleção (opcional)
            
        Returns:
            Lista de file_paths dos documentos com esse tipo
        """
        with self._get_cursor() as cur:
            if collection_id:
                cur.execute(
                    """
                    SELECT file_path
                    FROM documentos_ingeridos
                    WHERE chunking_type = %s
                    AND collection_id = %s
                    """,
                    (chunking_type, collection_id)
                )
            else:
                cur.execute(
                    """
                    SELECT file_path
                    FROM documentos_ingeridos
                    WHERE chunking_type = %s
                    """,
                    (chunking_type,)
                )
            
            return [row[0] for row in cur.fetchall()]
    
    def count_by_chunking_type(self, collection_id: Optional[str] = None) -> dict:
        """
        Conta documentos por tipo de chunking.
        
        Args:
            collection_id: Filtrar por coleção (opcional)
            
        Returns:
            Dict com contagens por tipo (hierarchical, sentence, null)
        """
        with self._get_cursor(dict_cursor=True) as cur:
            if collection_id:
                cur.execute(
                    """
                    SELECT 
                        chunking_type,
                        COUNT(*) as count
                    FROM documentos_ingeridos
                    WHERE collection_id = %s
                    GROUP BY chunking_type
                    """,
                    (collection_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT 
                        chunking_type,
                        COUNT(*) as count
                    FROM documentos_ingeridos
                    GROUP BY chunking_type
                    """
                )
            
            return {row['chunking_type']: row['count'] for row in cur.fetchall()}
    
    def delete_by_path(self, file_path: str) -> bool:
        """
        Remove o registro de um documento ingerido.
        
        Args:
            file_path: Caminho absoluto do arquivo
            
        Returns:
            True se removido, False se não encontrado
        """
        start_time = time.time()
        
        with self._get_cursor() as cur:
            cur.execute(
                """
                DELETE FROM documentos_ingeridos
                WHERE file_path = %s
                """,
                (file_path,)
            )
            deleted = cur.rowcount > 0
        
        duration = time.time() - start_time
        if deleted:
            print(f"Deleted ingestion record for {file_path} in {duration:.2f}s")
        
        return deleted
    
    def clear_all(self) -> int:
        """
        Remove todos os registros de ingestão.
        
        Returns:
            Número de registros removidos
        """
        start_time = time.time()
        
        with self._get_cursor() as cur:
            cur.execute("DELETE FROM documentos_ingeridos")
            deleted = cur.rowcount
        
        duration = time.time() - start_time
        print(f"Cleared all ingestion records ({deleted} records) in {duration:.2f}s")
        
        return deleted
    
    def get_stats(self, collection_id: Optional[str] = None) -> dict:
        """
        Retorna estatísticas de ingestão.
        
        Args:
            collection_id: Filtrar por coleção (opcional)
            
        Returns:
            Dict com estatísticas
        """
        with self._get_cursor(dict_cursor=True) as cur:
            if collection_id:
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as total_documents,
                        SUM(chunks_count) as total_chunks,
                        SUM(file_size) as total_size,
                        COUNT(CASE WHEN chunking_type = 'hierarchical' THEN 1 END) as hierarchical_count,
                        COUNT(CASE WHEN chunking_type = 'sentence' THEN 1 END) as sentence_count
                    FROM documentos_ingeridos
                    WHERE collection_id = %s
                    """,
                    (collection_id,)
                )
            else:
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as total_documents,
                        SUM(chunks_count) as total_chunks,
                        SUM(file_size) as total_size,
                        COUNT(CASE WHEN chunking_type = 'hierarchical' THEN 1 END) as hierarchical_count,
                        COUNT(CASE WHEN chunking_type = 'sentence' THEN 1 END) as sentence_count
                    FROM documentos_ingeridos
                    """
                )
            
            row = cur.fetchone()
            
            return {
                'total_documents': row['total_documents'] or 0,
                'total_chunks': row['total_chunks'] or 0,
                'total_size_mb': round((row['total_size'] or 0) / (1024 * 1024), 2),
                'hierarchical_count': row['hierarchical_count'] or 0,
                'sentence_count': row['sentence_count'] or 0
            }


# Instância global para uso
_ingestion_repo = IngestionRepository()
