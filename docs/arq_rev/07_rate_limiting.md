# 07 - Rate Limiting

## Objetivo
Implementar rate limiting para prevenir abuso da API e garantir fair-use.

---

## Arquivos a Modificar/Criar

| Arquivo | Modificação |
|---------|-------------|
| `requirements.txt` | Adicionar flask-limiter |
| `src/config.py` | Configurações de rate limit |
| `src/app.py` | Inicializar limiter |
| `src/api/routes/*.py` | Aplicar decorators |

---

## Passos de Implementação

### Passo 1: Adicionar Dependência

```bash
pip install flask-limiter
```

Adicionar ao `requirements.txt`:
```txt
flask-limiter>=3.5.0
```

### Passo 2: Adicionar Configurações

Editar `src/config.py`:

```python
class Settings(BaseSettings):
    # ... configurações existentes ...
    
    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE: str = "memory://"  # ou "redis://localhost:6379"
    
    # Limites padrão
    RATE_LIMIT_DEFAULT: str = "200 per day, 50 per hour"
    
    # Limites específicos por endpoint
    RATE_LIMIT_QUERY: str = "30 per minute"        # Queries RAG (pesadas)
    RATE_LIMIT_SEARCH: str = "60 per minute"       # Busca sem LLM
    RATE_LIMIT_INGEST: str = "10 per minute"       # Ingestão de docs
    RATE_LIMIT_HEALTH: str = "120 per minute"      # Health checks
```

### Passo 3: Criar Módulo de Rate Limiting

Criar `src/api/middleware/rate_limiter.py`:

```python
"""
Configuração de Rate Limiting para a API.
"""
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_STORAGE,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_QUERY,
    RATE_LIMIT_SEARCH,
    RATE_LIMIT_INGEST,
    RATE_LIMIT_HEALTH
)
from src.core.logger import api_logger


def get_client_identifier():
    """
    Identifica o cliente para rate limiting.
    Usa API Key se presente, senão usa IP.
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:8]}"  # Primeiros 8 chars
    return get_remote_address()


# Instância global do limiter
limiter = Limiter(
    key_func=get_client_identifier,
    storage_uri=RATE_LIMIT_STORAGE,
    default_limits=[RATE_LIMIT_DEFAULT] if RATE_LIMIT_ENABLED else [],
    enabled=RATE_LIMIT_ENABLED
)


def handle_rate_limit_exceeded(e):
    """Handler para quando limite é excedido."""
    api_logger.warning(
        "rate_limit_exceeded",
        client=get_client_identifier(),
        limit=str(e.description)
    )
    return jsonify({
        "error": "Rate limit exceeded",
        "message": str(e.description),
        "retry_after": e.retry_after
    }), 429


def init_rate_limiter(app: Flask):
    """Inicializa rate limiter na aplicação."""
    limiter.init_app(app)
    app.register_error_handler(429, handle_rate_limit_exceeded)
    
    api_logger.info(
        "rate_limiter_initialized",
        enabled=RATE_LIMIT_ENABLED,
        storage=RATE_LIMIT_STORAGE
    )


# Exportar limites configurados
LIMITS = {
    "query": RATE_LIMIT_QUERY,
    "search": RATE_LIMIT_SEARCH,
    "ingest": RATE_LIMIT_INGEST,
    "health": RATE_LIMIT_HEALTH
}
```

### Passo 4: Inicializar no App

Editar `src/app.py`:

```python
from src.api.middleware.rate_limiter import init_rate_limiter


def create_app() -> Flask:
    app = Flask(__name__)
    
    # ... configurações existentes ...
    
    # Inicializar Rate Limiter
    init_rate_limiter(app)
    
    # ... resto do código ...
```

### Passo 5: Aplicar nos Endpoints

Editar `src/api/routes/query.py`:

```python
from src.api.middleware.rate_limiter import limiter, LIMITS


@query_bp.route("/query", methods=["POST"])
@limiter.limit(LIMITS["query"])
def query():
    # ... código existente ...
    pass


@query_bp.route("/search", methods=["POST"])
@limiter.limit(LIMITS["search"])
def search():
    # ... código existente ...
    pass
```

Editar `src/api/routes/documents.py`:

```python
@documents_bp.route("/ingest", methods=["POST"])
@limiter.limit(LIMITS["ingest"])
def ingest():
    # ... código existente ...
    pass
```

### Passo 6: Exemptions para Health Checks

```python
@health_bp.route("/health")
@limiter.limit(LIMITS["health"])
def health_check():
    pass


# Ou isentar completamente:
@health_bp.route("/metrics")
@limiter.exempt
def get_metrics():
    pass
```

---

## Configuração com Redis (Produção)

Para ambientes multi-instância, usar Redis:

```bash
# .env.production
RATE_LIMIT_STORAGE=redis://redis:6379/0
```

---

## Verificação

### Teste de Limite
```bash
# Fazer muitas requisições rápidas
for i in {1..35}; do
  curl -s http://localhost:5000/api/query \
    -X POST -H "Content-Type: application/json" \
    -d '{"question": "teste"}' &
done
wait

# Última requisição deve retornar 429
```

### Teste de Headers
```bash
curl -v http://localhost:5000/api/query -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "teste"}'

# Headers esperados:
# X-RateLimit-Limit: 30
# X-RateLimit-Remaining: 29
# X-RateLimit-Reset: 1735520000
```

---

## Monitoramento

Adicionar métricas Prometheus:

```python
from prometheus_client import Counter

rate_limit_hits = Counter(
    'api_rate_limit_hits_total',
    'Total de requisições bloqueadas por rate limit',
    ['endpoint']
)
```
