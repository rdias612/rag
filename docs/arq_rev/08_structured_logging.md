# 08 - Structured Logging (JSON)

## Objetivo
Migrar para logs estruturados em JSON para facilitar agregação e análise em ferramentas como ELK, Datadog ou CloudWatch.

---

## Arquivos a Modificar

| Arquivo | Modificação |
|---------|-------------|
| `requirements.txt` | Adicionar structlog |
| `src/core/logger.py` | Reconfigurar para JSON |
| `src/api/routes/*.py` | Atualizar chamadas de log |

---

## Passos de Implementação

### Passo 1: Adicionar Dependência

```bash
pip install structlog
```

Adicionar ao `requirements.txt`:
```txt
structlog>=24.0.0
```

### Passo 2: Reescrever `logger.py`

```python
"""
Logging estruturado com structlog.

Produz logs em formato JSON para fácil integração com:
- ELK Stack
- Datadog
- CloudWatch
- Grafana Loki
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from src.config import APP_ENV


def add_app_context(
    logger: logging.Logger, 
    method_name: str, 
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Adiciona contexto da aplicação a todos os logs."""
    event_dict["app"] = "rag-api"
    event_dict["env"] = APP_ENV
    return event_dict


def setup_logging() -> None:
    """Configura logging estruturado."""
    
    # Processadores compartilhados
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if APP_ENV == "dev":
        # Desenvolvimento: logs coloridos e legíveis
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Produção: JSON puro
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configurar logging padrão também
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


# Inicializar na importação
setup_logging()


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Retorna logger configurado."""
    return structlog.get_logger(name)


# Loggers pré-configurados para cada módulo
api_logger = get_logger("api")
rag_logger = get_logger("rag")
db_logger = get_logger("database")
ingestion_logger = get_logger("ingestion")


# =============================================================================
# Helpers para logging de requests
# =============================================================================

def log_api_request(endpoint: str, method: str, **kwargs) -> None:
    """Log de entrada de request."""
    api_logger.info(
        "request_received",
        endpoint=endpoint,
        method=method,
        **kwargs
    )


def log_api_response(
    endpoint: str, 
    status_code: int, 
    duration_ms: float,
    **kwargs
) -> None:
    """Log de resposta."""
    level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
    getattr(api_logger, level)(
        "request_completed",
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=round(duration_ms, 2),
        **kwargs
    )


def bind_request_context(request_id: str, session_id: str = None) -> None:
    """Vincula contexto ao request atual."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        session_id=session_id
    )
```

### Passo 3: Atualizar Uso nos Endpoints

**Antes:**
```python
api_logger.info(f"Query recebida: {question}")
```

**Depois:**
```python
api_logger.info(
    "query_received",
    question=question[:100],  # Truncar para não poluir logs
    top_k=top_k,
    session_id=session_id
)
```

### Passo 4: Middleware de Request ID

Criar `src/api/middleware/request_context.py`:

```python
"""
Middleware para injetar request_id em todos os logs.
"""
import uuid
from flask import Flask, g, request

from src.core.logger import bind_request_context


def init_request_context(app: Flask) -> None:
    """Inicializa middleware de contexto de request."""
    
    @app.before_request
    def before_request():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.start_time = time.time()
        
        bind_request_context(
            request_id=g.request_id,
            session_id=request.headers.get("X-Session-ID")
        )
    
    @app.after_request
    def after_request(response):
        response.headers["X-Request-ID"] = g.request_id
        return response
```

### Passo 5: Atualizar `app.py`

```python
from src.api.middleware.request_context import init_request_context


def create_app() -> Flask:
    app = Flask(__name__)
    
    # ... configurações existentes ...
    
    # Inicializar contexto de request
    init_request_context(app)
    
    # ... resto do código ...
```

---

## Output Esperado

### Desenvolvimento
```
2025-12-30 00:40:00 [info] request_received   endpoint=/api/query method=POST request_id=abc-123
2025-12-30 00:40:01 [info] query_processed    chunks_found=5 duration_ms=850.5
2025-12-30 00:40:01 [info] request_completed  endpoint=/api/query status_code=200 duration_ms=920.3
```

### Produção (JSON)
```json
{"timestamp": "2025-12-30T00:40:00Z", "level": "info", "event": "request_received", "endpoint": "/api/query", "method": "POST", "request_id": "abc-123", "app": "rag-api", "env": "production"}
{"timestamp": "2025-12-30T00:40:01Z", "level": "info", "event": "query_processed", "chunks_found": 5, "duration_ms": 850.5, "request_id": "abc-123"}
{"timestamp": "2025-12-30T00:40:01Z", "level": "info", "event": "request_completed", "endpoint": "/api/query", "status_code": 200, "duration_ms": 920.3, "request_id": "abc-123"}
```

---

## Verificação

```bash
# Definir ambiente
export APP_ENV=production

# Fazer request e ver logs
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "teste"}'

# Validar JSON
python -c "import json; json.loads(...)"
```
