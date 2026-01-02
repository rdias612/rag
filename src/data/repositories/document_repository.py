"""
Repository para operações com documentos (chunks).
"""
import json
import time
from typing import Optional

from src.data.repositories.base import BaseRepository
from src.core.logger import db_logger, log_db_query, log_db_result, log_db_search_with_embedding, log_db_search_results
from src.config import (
    TOP_K_RESULTS,
    MIN_SIMILARITY_THRESHOLD,
    ENABLE_ENCRYPTION,
    ENCRYPT_DOCUMENT_CONTENT,
    ENCRYPT_METADATA
)

# Importar funções de criptografia
try:
    from src.core.encryption import (
        encrypt_data,
        decrypt_data,
        encrypt_metadata,
        decrypt_metadata
    )
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

    # Importar IngestionRepository (usado em métodos específicos)
    from src.data.repositories.ingestion_repository import IngestionRepository


class DocumentRepository(BaseRepository):
    """Gerencia documentos/chunks no banco de dados."""
    
    def create(self, content: str, metadata: dict, embedding: list[float], 
               collection_id: str = "default") -> int:
        """Insere um documento com embedding."""
        start_time = time.time()
        
        # Criptografar se habilitado
        if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION:
            if ENCRYPT_DOCUMENT_CONTENT:
                content = encrypt_data(content)
            if ENCRYPT_METADATA:
                metadata_str = encrypt_metadata(metadata)
            else:
                metadata_str = json.dumps(metadata)
        else:
            metadata_str = json.dumps(metadata)
        
        with self._get_cursor() as cur:
            if not isinstance(embedding, list) or any(v is None for v in embedding):
                raise ValueError(f"Embedding inválido: contém valores nulos ou tipo incorreto")
            
            cur.execute("""
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s::vector, %s)
                RETURNING id
            """, (content, metadata_str, embedding, collection_id))
            doc_id = cur.fetchone()[0]
        
        duration = time.time() - start_time
        log_db_result("INSERT", 1, duration)
        return doc_id
    
    def create_batch(self, documents: list[dict]) -> int:
        """Insere múltiplos documentos em batch."""
        start_time = time.time()
        log_db_query("INSERT BATCH", f"Inserting {len(documents)} documents")
        
        with self._get_cursor() as cur:
            values = []
            for doc in documents:
                # Validar embedding
                if doc["embedding"] is None or not isinstance(doc["embedding"], list):
                    continue
                if any(v is None for v in doc["embedding"]):
                    continue
                
                content = doc["content"]
                metadata = doc["metadata"]
                
                if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION:
                    if ENCRYPT_DOCUMENT_CONTENT:
                        content = encrypt_data(content)
                    if ENCRYPT_METADATA:
                        metadata_str = encrypt_metadata(metadata)
                    else:
                        metadata_str = json.dumps(metadata)
                else:
                    metadata_str = json.dumps(metadata)
                
                values.append((
                    content,
                    metadata_str,
                    doc["embedding"],
                    doc.get("collection_id", "default")
                ))
            
            if not values:
                return 0
            
            cur.executemany("""
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s::vector, %s)
            """, values)
            inserted_count = len(values)
        
        duration = time.time() - start_time
        log_db_result("INSERT BATCH", inserted_count, duration)
        return inserted_count
    
    def find_similar(self, query_embedding: list[float], top_k: int = TOP_K_RESULTS,
                     min_similarity: Optional[float] = None,
                     collection_id: Optional[str] = None,
                     chunking_type: Optional[str] = None,
                     source_paths: Optional[list[str]] = None) -> list[dict]:
        """Busca documentos similares por embedding."""
        start_time = time.time()
        
        if min_similarity is None:
            min_similarity = MIN_SIMILARITY_THRESHOLD
        
        log_db_search_with_embedding(query_embedding, top_k)
        
        with self._get_cursor(dict_cursor=True) as cur:
            where_conditions = ["(metadata->>'chunk_type' != 'parent' OR metadata->>'chunk_type' IS NULL)"]
            params = [query_embedding]
            
            if collection_id:
                where_conditions.append("collection_id = %s")
                params.append(collection_id)
            
            if chunking_type:
                # Filtrar por tipo de chunking no metadata
                # Para hierarchical: buscar chunks do tipo 'child'
                # Para sentence: buscar chunks do tipo 'sentence'
                if chunking_type == "hierarchical":
                    where_conditions.append("metadata->>'chunk_type' = 'child'")
                elif chunking_type == "sentence":
                    where_conditions.append("metadata->>'chunk_type' = 'sentence'")
            
            if source_paths:
                placeholders = ",".join(["%s"] * len(source_paths))
                where_conditions.append(f"metadata->>'source_path' IN ({placeholders})")
                params.extend(source_paths)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            params.extend([query_embedding, top_k])
            
            query = f"""
                SELECT 
                    id, content, metadata, collection_id,
                    1 - (embedding <=> %s::vector) as similarity
                FROM documentos
                {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            
            cur.execute(query, tuple(params))
            results = cur.fetchall()
        
        duration = time.time() - start_time
        
        # Descriptografar se necessário
        results_list = []
        for row in results:
            row_dict = dict(row)
            
            if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION:
                if ENCRYPT_DOCUMENT_CONTENT and row_dict.get("content"):
                    try:
                        row_dict["content"] = decrypt_data(row_dict["content"])
                    except Exception:
                        pass
                
                if ENCRYPT_METADATA and row_dict.get("metadata"):
                    try:
                        row_dict["metadata"] = decrypt_metadata(row_dict["metadata"])
                    except Exception:
                        row_dict["metadata"] = json.loads(row_dict["metadata"]) if row_dict["metadata"] else {}
            
            results_list.append(row_dict)
        
        # Filtrar por similaridade mínima
        if min_similarity > 0:
            results_list = [r for r in results_list if r["similarity"] >= min_similarity]
        
        log_db_search_results(results_list, duration)
        return results_list
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """Busca documento por ID."""
        with self._get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM documentos WHERE id = %s", (id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def count(self, collection_id: Optional[str] = None) -> int:
        """Conta documentos, opcionalmente filtrados por coleção."""
        with self._get_cursor() as cur:
            if collection_id:
                cur.execute(
                    "SELECT COUNT(*) FROM documentos WHERE collection_id = %s",
                    (collection_id,)
                )
            else:
                cur.execute("SELECT COUNT(*) FROM documentos")
            return cur.fetchone()[0]
    
    def delete_by_source(self, source_path: str) -> int:
        """Remove chunks por source_path."""
        start_time = time.time()
        
        with self._get_cursor() as cur:
            cur.execute("""
                DELETE FROM documentos
                WHERE metadata->>'source_path' = %s
            """, (source_path,))
            deleted = cur.rowcount
        
        duration = time.time() - start_time
        db_logger.info(f"Removed {deleted} chunks from {source_path} in {duration:.2f}s")
        return deleted
    
    def list_collections(self) -> list[str]:
        """Lista todas as coleções."""
        with self._get_cursor() as cur:
            cur.execute("""
                SELECT DISTINCT collection_id
                FROM documentos
                WHERE collection_id IS NOT NULL
                ORDER BY collection_id
            """)
            return [row[0] for row in cur.fetchall()]
    
    def clear_all(self) -> int:
        """Remove todos os documentos."""
        with self._get_cursor() as cur:
            cur.execute("DELETE FROM documentos")
            return cur.rowcount
    
    def find_similar_by_chunking_type(self, query_embedding: list[float], 
                                      chunking_type: str,
                                      top_k: int = TOP_K_RESULTS,
                                      min_similarity: Optional[float] = None,
                                      collection_id: Optional[str] = None) -> list[dict]:
        """
        Busca documentos similares filtrando especificamente por tipo de chunking.
        
        Método otimizado que usa a tabela documentos_ingeridos para
        identificar quais arquivos usaram determinado tipo de chunking
        e busca apenas nesses documentos.
        
        Args:
            query_embedding: Vetor de embedding da query
            chunking_type: Tipo de chunking ('hierarchical' ou 'sentence')
            top_k: Número de resultados
            min_similarity: Similaridade mínima
            collection_id: Filtrar por coleção
            
        Returns:
            Lista de documentos encontrados
        """
        # Buscar paths de documentos com este tipo de chunking
        ingestion_repo = IngestionRepository()
        source_paths = ingestion_repo.find_by_chunking_type(chunking_type, collection_id)
        
        if not source_paths:
            # Nenhum documento com este tipo de chunking
            return []
        
        # Buscar apenas nesses documentos
        return self.find_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            min_similarity=min_similarity,
            collection_id=None,  # Já filtrado por source_paths
            chunking_type=chunking_type,
            source_paths=source_paths
        )
    
    def get_parent_content(self, source_path: str, parent_index: int) -> Optional[str]:
        """Recupera o texto de um chunk pai baseado no caminho do arquivo e índice."""
        with self._get_cursor() as cur:
            cur.execute("""
                SELECT content
                FROM documentos
                WHERE metadata->>'source_path' = %s
                AND (metadata->>'chunk_index')::int = %s
                AND metadata->>'chunk_type' = 'parent'
                LIMIT 1
            """, (source_path, parent_index))
            row = cur.fetchone()
        
        if not row:
            return None
        
        content = row[0]
        
        # Descriptografar se necessário
        if ENCRYPTION_AVAILABLE and ENABLE_ENCRYPTION and ENCRYPT_DOCUMENT_CONTENT:
            try:
                content = decrypt_data(content)
            except Exception:
                pass
        
        return content
