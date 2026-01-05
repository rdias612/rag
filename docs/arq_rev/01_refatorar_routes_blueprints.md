# 01 - Refatorar routes.py em Blueprints

## Objetivo
Dividir o arquivo monolítico `src/api/routes.py` (1976 linhas) em múltiplos blueprints organizados por domínio.

---

## Arquivos Afetados

| Ação | Arquivo |
|------|---------|
| MODIFICAR | `src/api/routes.py` → será desmembrado |
| CRIAR | `src/api/routes/__init__.py` |
| CRIAR | `src/api/routes/query.py` |
| CRIAR | `src/api/routes/sessions.py` |
| CRIAR | `src/api/routes/documents.py` |
| CRIAR | `src/api/routes/prompts.py` |
| CRIAR | `src/api/routes/metrics.py` |
| CRIAR | `src/api/routes/health.py` |
| MODIFICAR | `src/app.py` → atualizar imports |

---

## Passos de Implementação

### Passo 1: Criar Estrutura de Diretórios
```bash
mkdir src\api\routes
```

### Passo 2: Criar `routes/__init__.py`
```python
"""
Registro centralizado de todos os blueprints da API.
"""
from flask import Blueprint

from .health import health_bp
from .query import query_bp
from .sessions import sessions_bp
from .documents import documents_bp
from .prompts import prompts_bp
from .metrics import metrics_bp


def register_blueprints(app):
    """Registra todos os blueprints na aplicação Flask."""
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(query_bp, url_prefix="/api")
    app.register_blueprint(sessions_bp, url_prefix="/api/chat")
    app.register_blueprint(documents_bp, url_prefix="/api")
    app.register_blueprint(prompts_bp, url_prefix="/api")
    app.register_blueprint(metrics_bp, url_prefix="/api")
```

### Passo 3: Criar `routes/health.py`
Mover endpoints: `/health`, `/stats`, `/collections`

```python
"""
Endpoints de saúde e estatísticas do sistema.
"""
from flask import Blueprint, jsonify
from src.data.database import get_document_count, list_collections, check_connection

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check():
    # ... código existente de health_check()
    pass


@health_bp.route("/stats")
def get_stats():
    # ... código existente de get_stats()
    pass


@health_bp.route("/collections")
def get_collections():
    # ... código existente de get_collections()
    pass
```

### Passo 4: Criar `routes/query.py`
Mover endpoints: `/query`, `/query/stream`, `/search`, `/chat`

```python
"""
Endpoints de query RAG e busca.
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
from src.core.rag import query_rag, query_rag_stream, search_only, query_rag_with_history

query_bp = Blueprint("query", __name__)


@query_bp.route("/query", methods=["POST"])
def query():
    # ... código existente
    pass


@query_bp.route("/query/stream", methods=["POST"])
def query_stream():
    # ... código existente
    pass


@query_bp.route("/search", methods=["POST"])
def search():
    # ... código existente
    pass


@query_bp.route("/chat", methods=["POST"])
def chat():
    # ... código existente
    pass
```

### Passo 5: Criar `routes/sessions.py`
Mover endpoints: `/chat/sessions`, `/chat/sessions/<id>`, `/chat/new`

```python
"""
Endpoints de gerenciamento de sessões de conversa.
"""
from flask import Blueprint, jsonify
from src.core.conversation import (
    list_all_sessions,
    get_session_messages,
    delete_session,
    create_session
)

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions")
def list_sessions():
    pass


@sessions_bp.route("/sessions/<session_id>")
def get_session(session_id: str):
    pass


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session_endpoint(session_id: str):
    pass


@sessions_bp.route("/new", methods=["POST"])
def new_session():
    pass
```

### Passo 6: Criar `routes/documents.py`
Mover endpoints: `/ingest/*`, `/documents/*`

### Passo 7: Criar `routes/prompts.py`
Mover endpoints: `/prompts/*`

### Passo 8: Criar `routes/metrics.py`
Mover endpoints: `/metrics/*`, `/cache/*`, `/classify`, `/evaluate`, `/hyde/test`

### Passo 9: Atualizar `app.py`
```python
# Antes
from src.api.routes import api
app.register_blueprint(api, url_prefix="/api")

# Depois
from src.api.routes import register_blueprints
register_blueprints(app)
```

### Passo 10: Mover Código Compartilhado
Criar `src/api/middleware/` para:
- `error_handler.py` - handlers de exceção
- `request_validation.py` - decorators de validação
- `logging_middleware.py` - log de requests/responses

---

## Ordem de Migração Sugerida

1. **health.py** (mais simples, para testar a estrutura)
2. **metrics.py** (dependências mínimas)
3. **prompts.py** (CRUD isolado)
4. **sessions.py** (lógica self-contained)
5. **documents.py** (ingestão, mais complexo)
6. **query.py** (core do sistema, migrar por último)

---

## Verificação

```bash
# Testar endpoints após cada migração
curl http://localhost:5000/api/health
curl http://localhost:5000/api/stats
curl -X POST http://localhost:5000/api/query -d '{"question": "teste"}'
```

---

## Rollback
Manter backup de `routes.py` original até validar todas as migrações.

```bash
copy src\api\routes.py src\api\routes_backup.py
```
