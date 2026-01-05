# 04 - CORS Restritivo

## Objetivo
Substituir a configuração CORS permissiva (`"*"`) por uma configuração segura para produção.

---

## Problema Atual

```python
# src/app.py linha 24
CORS(app, resources={r"/*": {"origins": "*"}})
```

**Riscos:**
- Qualquer site pode fazer requisições à API
- Possível exfiltração de dados via CSRF
- Não adequado para produção

---

## Arquivos a Modificar

| Arquivo | Modificação |
|---------|-------------|
| `src/config.py` | Adicionar configuração ALLOWED_ORIGINS |
| `src/app.py` | Usar origens configuráveis |
| `.env.example` | Documentar variável |

---

## Passos de Implementação

### Passo 1: Adicionar Configuração

Editar `src/config.py`:

```python
class Settings(BaseSettings):
    # ... configurações existentes ...
    
    # ==========================================================================
    # CORS Configuration
    # ==========================================================================
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    CORS_MAX_AGE: int = 3600  # 1 hora de cache para preflight
    
    @property
    def ALLOWED_ORIGINS_LIST(self) -> list[str]:
        """Retorna lista de origens permitidas."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

# Exportar para compatibilidade
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS
ALLOWED_ORIGINS_LIST = settings.ALLOWED_ORIGINS_LIST
CORS_MAX_AGE = settings.CORS_MAX_AGE
```

### Passo 2: Atualizar `app.py`

```python
from flask import Flask
from flask_cors import CORS

from src.config import ALLOWED_ORIGINS_LIST, CORS_MAX_AGE


def create_app() -> Flask:
    app = Flask(__name__)
    
    # Configurar JSON para não escapar caracteres Unicode
    app.json.ensure_ascii = False
    
    # CORS restritivo para produção
    CORS(app, resources={
        r"/api/*": {
            "origins": ALLOWED_ORIGINS_LIST,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
            "expose_headers": ["Content-Disposition"],
            "supports_credentials": True,
            "max_age": CORS_MAX_AGE
        }
    })
    
    # ... resto do código ...
```

### Passo 3: Atualizar `.env.example`

```bash
# =============================================================================
# CORS Configuration
# =============================================================================
# Lista de origens permitidas (separadas por vírgula)
# Desenvolvimento: http://localhost:5173
# Produção: https://seu-dominio.com
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_MAX_AGE=3600
```

### Passo 4: Configuração por Ambiente

**`.env` (desenvolvimento):**
```bash
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

**`.env.sit`:**
```bash
ALLOWED_ORIGINS=https://rag-sit.internal.company.com
```

**`.env.uat`:**
```bash
ALLOWED_ORIGINS=https://rag-uat.internal.company.com
```

**Produção (via variável de ambiente):**
```bash
export ALLOWED_ORIGINS=https://rag.company.com,https://www.rag.company.com
```

---

## Verificação

### Teste 1: Origem Permitida
```bash
curl -X OPTIONS http://localhost:5000/api/health \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Deve retornar:
# Access-Control-Allow-Origin: http://localhost:5173
```

### Teste 2: Origem Bloqueada
```bash
curl -X OPTIONS http://localhost:5000/api/health \
  -H "Origin: http://malicious-site.com" \
  -H "Access-Control-Request-Method: GET" \
  -v

# NÃO deve retornar Access-Control-Allow-Origin
```

### Teste 3: Frontend Funcional
```bash
# Subir frontend e testar chamadas
cd frontend && npm run dev
# Testar queries no chat
```

---

## Rollback

Se necessário reverter temporariamente:

```python
# Modo debug apenas
import os

if os.getenv("DEBUG_CORS", "false").lower() == "true":
    CORS(app, resources={r"/*": {"origins": "*"}})
else:
    CORS(app, resources={...})  # Configuração restritiva
```

---

## Checklist Final

- [ ] Configuração adicionada em `config.py`
- [ ] `app.py` usando origens configuráveis
- [ ] `.env.example` documentado
- [ ] Testado com frontend local
- [ ] Testado bloqueio de origem externa
