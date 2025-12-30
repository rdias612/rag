# 12 - Autenticação (API Keys / JWT)

## Objetivo
Implementar autenticação para proteger a API em produção.

---

## Opções de Autenticação

| Método | Complexidade | Caso de Uso |
|--------|--------------|-------------|
| **API Keys** | Baixa | Apps server-to-server, scripts |
| **JWT** | Média | Apps com usuários, mobile |
| **OAuth2** | Alta | Integração com SSO corporativo |

Recomendação: **Começar com API Keys**, migrar para JWT se necessário.

---

## Arquivos a Criar/Modificar

| Arquivo | Descrição |
|---------|-----------|
| `src/api/middleware/auth.py` | Lógica de autenticação |
| `src/data/repositories/api_key_repository.py` | CRUD de API Keys |
| `src/api/routes/admin.py` | Endpoints de gestão de keys |
| `alembic/versions/xxx_add_api_keys.py` | Migração do banco |
| `src/config.py` | Configurações de auth |

---

## Passos de Implementação

### Passo 1: Criar Migração do Banco

```bash
alembic revision --autogenerate -m "add api keys table"
```

```python
# alembic/versions/xxx_add_api_keys.py
def upgrade():
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('rate_limit', sa.String(50), nullable=True),  # ex: "100/hour"
        sa.Column('scopes', sa.JSON(), nullable=True),  # ["read", "write", "admin"]
    )
    
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])

def downgrade():
    op.drop_table('api_keys')
```

### Passo 2: Criar Middleware de Autenticação

```python
# src/api/middleware/auth.py
"""
Middleware de autenticação para a API.
"""
import hashlib
import secrets
from functools import wraps
from datetime import datetime
from typing import Optional

from flask import request, jsonify, g

from src.data.repositories.api_key_repository import APIKeyRepository
from src.core.logger import api_logger
from src.config import AUTH_ENABLED, AUTH_EXEMPT_PATHS


api_key_repo = APIKeyRepository()


def hash_api_key(key: str) -> str:
    """Gera hash SHA-256 da API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """
    Gera nova API key.
    
    Returns:
        Tuple de (plain_key, hashed_key)
        A plain_key deve ser mostrada apenas uma vez ao usuário.
    """
    plain_key = f"rag_{secrets.token_urlsafe(32)}"
    hashed_key = hash_api_key(plain_key)
    return plain_key, hashed_key


def validate_api_key(key: str) -> Optional[dict]:
    """
    Valida API key e retorna dados associados.
    
    Returns:
        Dict com dados da key ou None se inválida
    """
    if not key:
        return None
    
    hashed = hash_api_key(key)
    key_data = api_key_repo.find_by_hash(hashed)
    
    if not key_data:
        return None
    
    if not key_data["is_active"]:
        return None
    
    if key_data["expires_at"] and key_data["expires_at"] < datetime.utcnow():
        return None
    
    # Atualizar last_used_at
    api_key_repo.update_last_used(key_data["id"])
    
    return key_data


def require_api_key(f):
    """
    Decorator que exige API key válida.
    
    Usage:
        @api.route("/protected")
        @require_api_key
        def protected_endpoint():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not AUTH_ENABLED:
            return f(*args, **kwargs)
        
        # Checar se path está isento
        if request.path in AUTH_EXEMPT_PATHS:
            return f(*args, **kwargs)
        
        # Extrair API key do header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            api_logger.warning("auth_failed", reason="missing_api_key", path=request.path)
            return jsonify({"error": "API key required"}), 401
        
        # Validar key
        key_data = validate_api_key(api_key)
        
        if not key_data:
            api_logger.warning("auth_failed", reason="invalid_api_key", path=request.path)
            return jsonify({"error": "Invalid API key"}), 401
        
        # Armazenar dados da key no contexto
        g.api_key_id = key_data["id"]
        g.api_key_name = key_data["name"]
        g.api_key_scopes = key_data.get("scopes", [])
        
        api_logger.info("auth_success", key_name=key_data["name"], path=request.path)
        
        return f(*args, **kwargs)
    
    return decorated


def require_scope(scope: str):
    """
    Decorator adicional que exige scope específico.
    
    Usage:
        @require_api_key
        @require_scope("admin")
        def admin_only():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            scopes = getattr(g, 'api_key_scopes', [])
            
            if scope not in scopes and "admin" not in scopes:
                return jsonify({"error": f"Scope '{scope}' required"}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### Passo 3: Criar Endpoints de Gestão

```python
# src/api/routes/admin.py
"""
Endpoints administrativos para gestão de API keys.
"""
from flask import Blueprint, request, jsonify

from src.api.middleware.auth import (
    require_api_key,
    require_scope,
    generate_api_key
)
from src.data.repositories.api_key_repository import APIKeyRepository


admin_bp = Blueprint("admin", __name__)
api_key_repo = APIKeyRepository()


@admin_bp.route("/api-keys", methods=["POST"])
@require_api_key
@require_scope("admin")
def create_api_key():
    """
    Cria nova API key.
    
    Body:
        {
            "name": "Nome descritivo",
            "expires_in_days": 365,  // opcional
            "scopes": ["read", "write"]  // opcional
        }
    """
    data = request.get_json()
    name = data.get("name")
    
    if not name:
        return jsonify({"error": "Name is required"}), 400
    
    plain_key, hashed_key = generate_api_key()
    
    key_id = api_key_repo.create(
        name=name,
        key_hash=hashed_key,
        expires_in_days=data.get("expires_in_days"),
        scopes=data.get("scopes", ["read"])
    )
    
    return jsonify({
        "id": key_id,
        "name": name,
        "key": plain_key,  # Mostrar apenas uma vez!
        "message": "Guarde esta chave! Ela não será mostrada novamente."
    }), 201


@admin_bp.route("/api-keys", methods=["GET"])
@require_api_key
@require_scope("admin")
def list_api_keys():
    """Lista todas as API keys (sem mostrar as chaves)."""
    keys = api_key_repo.list_all()
    return jsonify({"keys": keys})


@admin_bp.route("/api-keys/<int:key_id>", methods=["DELETE"])
@require_api_key
@require_scope("admin")
def revoke_api_key(key_id: int):
    """Revoga uma API key."""
    success = api_key_repo.deactivate(key_id)
    
    if not success:
        return jsonify({"error": "Key not found"}), 404
    
    return jsonify({"message": "Key revoked"})
```

### Passo 4: Configuração

Adicionar ao `src/config.py`:

```python
class Settings(BaseSettings):
    # Authentication
    AUTH_ENABLED: bool = False  # Habilitar em produção
    AUTH_EXEMPT_PATHS: list[str] = ["/api/health", "/api/metrics"]
    
    # Bootstrap admin key (para primeira configuração)
    BOOTSTRAP_API_KEY: str = ""  # Definir via env var

# Exportar
AUTH_ENABLED = settings.AUTH_ENABLED
AUTH_EXEMPT_PATHS = settings.AUTH_EXEMPT_PATHS
```

### Passo 5: Aplicar nos Endpoints

```python
# src/api/routes/query.py
from src.api.middleware.auth import require_api_key


@query_bp.route("/query", methods=["POST"])
@require_api_key
def query():
    ...


@query_bp.route("/search", methods=["POST"])
@require_api_key
def search():
    ...
```

---

## Uso

### Criar Primeira Key (Bootstrap)

```bash
# Definir key de bootstrap
export BOOTSTRAP_API_KEY="rag_initial_admin_key_change_me"

# Criar key de admin via curl
curl -X POST http://localhost:5000/api/admin/api-keys \
  -H "X-API-Key: $BOOTSTRAP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Admin Principal", "scopes": ["read", "write", "admin"]}'
```

### Usar API com Key

```bash
curl -X POST http://localhost:5000/api/query \
  -H "X-API-Key: rag_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"question": "O que é RAG?"}'
```

---

## Verificação

```bash
# Sem key (deve retornar 401)
curl http://localhost:5000/api/query -X POST -d '{}'

# Com key inválida (deve retornar 401)
curl http://localhost:5000/api/query -X POST \
  -H "X-API-Key: invalid_key" \
  -d '{}'

# Com key válida (deve funcionar)
curl http://localhost:5000/api/query -X POST \
  -H "X-API-Key: rag_sua_key_valida" \
  -H "Content-Type: application/json" \
  -d '{"question": "teste"}'
```

---

## Migração para JWT (Futuro)

Se precisar de autenticação de usuários, adicionar:
- `flask-jwt-extended`
- Endpoints de login/refresh
- Token storage (Redis)
