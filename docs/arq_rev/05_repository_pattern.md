# 05 - Repository Pattern em database.py

## Objetivo
Refatorar `src/data/database.py` (1066 linhas) em múltiplos repositories seguindo o padrão Repository.

---

## Problema Atual
- Mistura conexão, queries SQL e lógica de negócio
- Arquivo gigante dificulta manutenção
- Acoplamento alto entre componentes

---

## Arquivos a Criar

| Arquivo | Descrição |
|---------|-----------|
| `src/data/repositories/__init__.py` | Exportações |
| `src/data/repositories/base.py` | BaseRepository abstrato |
| `src/data/repositories/document_repository.py` | CRUD de documentos |
| `src/data/repositories/prompt_repository.py` | CRUD de prompts |
| `src/data/repositories/session_repository.py` | Sessões de conversa |
| `src/data/repositories/feedback_repository.py` | Feedback de usuários |
| `src/data/repositories/ingestion_repository.py` | Controle de ingestão |

---

## Passos de Implementação

### Passo 1: Criar Estrutura

```bash
mkdir src\data\repositories
```

### Passo 2: Criar `base.py`

```python
"""
Base Repository com métodos comuns a todos os repositories.
"""
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, TypeVar, Generic

from src.data.connection import get_connection

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Classe base para todos os repositories."""
    
    def __init__(self, connection=None):
        self._external_connection = connection
    
    @contextmanager
    def _get_cursor(self):
        """Obtém cursor com conexão gerenciada."""
        if self._external_connection:
            with self._external_connection.cursor() as cur:
                yield cur
        else:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    yield cur
                    conn.commit()
    
    @abstractmethod
    def create(self, entity: T) -> int:
        """Cria uma entidade e retorna seu ID."""
        pass
    
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[T]:
        """Busca entidade por ID."""
        pass
    
    def delete_by_id(self, id: int) -> bool:
        """Remove entidade por ID."""
        raise NotImplementedError
```

### Passo 3: Criar `document_repository.py`

```python
"""
Repository para operações com documentos (chunks).
"""
from typing import Optional
from src.data.repositories.base import BaseRepository
from src.core.encryption import EncryptionManager


class DocumentRepository(BaseRepository):
    """Gerencia documentos/chunks no banco de dados."""
    
    def __init__(self, connection=None):
        super().__init__(connection)
        self._encryption = EncryptionManager()
    
    def create(self, content: str, metadata: dict, embedding: list[float], 
               collection_id: str = "default") -> int:
        """Insere um documento com embedding."""
        encrypted_content = self._encryption.encrypt_if_enabled(content)
        encrypted_metadata = self._encryption.encrypt_if_enabled(str(metadata))
        
        with self._get_cursor() as cur:
            cur.execute("""
                INSERT INTO documentos (content, metadata, embedding, collection_id)
                VALUES (%s, %s, %s::vector, %s)
                RETURNING id
            """, (encrypted_content, encrypted_metadata, embedding, collection_id))
            return cur.fetchone()[0]
    
    def create_batch(self, documents: list[dict]) -> int:
        """Insere múltiplos documentos em batch."""
        # Migrar código de insert_documents_batch()
        pass
    
    def find_similar(self, query_embedding: list[float], top_k: int = 5,
                     min_similarity: float = 0.0, 
                     collection_id: Optional[str] = None) -> list[dict]:
        """Busca documentos similares por embedding."""
        # Migrar código de search_similar()
        pass
    
    def find_by_id(self, id: int) -> Optional[dict]:
        """Busca documento por ID."""
        with self._get_cursor() as cur:
            cur.execute("SELECT * FROM documentos WHERE id = %s", (id,))
            return cur.fetchone()
    
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
        # Migrar código de remove_document_chunks_by_source()
        pass
    
    def list_collections(self) -> list[str]:
        """Lista todas as coleções."""
        # Migrar código de list_collections()
        pass
```

### Passo 4: Criar Outros Repositories

Seguir padrão similar para:
- `prompt_repository.py` - métodos de prompts
- `session_repository.py` - sessões e histórico
- `feedback_repository.py` - user_feedback
- `ingestion_repository.py` - ingestion_control

### Passo 5: Atualizar Imports

Criar `src/data/repositories/__init__.py`:

```python
from .document_repository import DocumentRepository
from .prompt_repository import PromptRepository
from .session_repository import SessionRepository
from .feedback_repository import FeedbackRepository
from .ingestion_repository import IngestionRepository

__all__ = [
    "DocumentRepository",
    "PromptRepository", 
    "SessionRepository",
    "FeedbackRepository",
    "IngestionRepository"
]
```

### Passo 6: Manter Compatibilidade

Atualizar `src/data/database.py` para usar repositories internamente:

```python
# Manter funções antigas como wrappers
from src.data.repositories import DocumentRepository

_doc_repo = DocumentRepository()

def insert_document(content, metadata, embedding, collection_id="default"):
    """Wrapper para manter compatibilidade."""
    return _doc_repo.create(content, metadata, embedding, collection_id)

def search_similar(query_embedding, top_k=5, min_similarity=None, collection_id=None):
    """Wrapper para manter compatibilidade."""
    return _doc_repo.find_similar(query_embedding, top_k, min_similarity, collection_id)
```

---

## Verificação

```bash
# Testar que funcionalidades existentes continuam funcionando
curl http://localhost:5000/api/stats
curl -X POST http://localhost:5000/api/query -d '{"question": "teste"}'
```

---

## Migração Gradual

1. Criar repositories com código novo
2. Adicionar wrappers em `database.py`
3. Migrar consumidores um a um
4. Depreciar funções antigas
5. Remover wrappers após migração completa
