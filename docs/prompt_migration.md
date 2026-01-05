# Migração de Prompts para Arquitetura Database-Driven

## 📋 Status Atual

**Data de início**: 2025-12-27  
**Status**: Backend 90% completo | Frontend 100% completo | Integração pendente

---

## 🎯 Objetivo

Migrar todos os prompts hardcoded do sistema para uma arquitetura flexível baseada em banco de dados, permitindo:
- ✅ Edição de prompts sem redeployment
- ✅ Múltiplos prompts por categoria (A/B testing)
- ✅ Sistema de prioridades
- ✅ Modo de seleção inteligente (Category vs LLM Router)
- ✅ Proteção contra deleção de prompts críticos

---

## ✅ O Que Já Foi Implementado

### 1. **Database Schema** ✅
**Arquivo**: `alembic/versions/20251227_01_add_prompt_metadata.py`

Campos adicionados à tabela `prompts`:
```sql
category VARCHAR(50)           -- Categorização (rag_main, hyde, etc)
priority INTEGER DEFAULT 100   -- Prioridade de seleção
tags TEXT[]                    -- Array de tags para filtragem
use_case TEXT                  -- Descrição de quando usar
created_by VARCHAR(100)        -- Rastreabilidade
version INTEGER DEFAULT 1      -- Versionamento automático
```

**Categorias críticas protegidas**:
- `rag_main` - Prompt principal RAG
- `hyde` - Geração de documentos hipotéticos
- `query_expansion` - Expansão de queries

### 2. **Backend - Database Functions** ✅
**Arquivo**: `src/data/database.py`

Funções implementadas:
- `list_prompts()` - Lista todos com metadados
- `get_prompt_by_id(id)` - Busca completa
- `get_prompts_by_category(category)` - Filtra por categoria
- `count_active_prompts_in_category(category)` - Contagem
- `create_prompt(...)` - Criação com validação
- `update_prompt_full(...)` - Atualização parcial + versionamento
- `can_delete_prompt(id)` - Validação de deleção
- `delete_prompt_safe(id)` - Deleção protegida

**Proteção**: Impede deletar o último prompt ativo em categorias críticas.

### 3. **Backend - PromptManager** ✅
**Arquivo**: `src/core/prompt_manager.py`

Classe centralizada com 2 modos de operação:

```python
class PromptManager:
    def get_prompt_for_category(
        self,
        category: str,
        mode: str = 'category',  # ou 'llm_router'
        context: dict = None
    ) -> str:
        # 1. Busca prompts da categoria
        # 2. Filtra por tags se context['question_type'] fornecido
        # 3. Seleciona baseado no modo
```

**Modo 'category'** (rápido, ~5ms):
- Retorna prompt de maior prioridade
- Ideal para produção

**Modo 'llm_router'** (inteligente, ~200ms):
- LLM escolhe entre múltiplos candidatos
- Baseado em query do usuário e metadados
- Ideal para experimentação

### 4. **Backend - REST API** ✅
**Arquivo**: `src/api/routes.py`

Endpoints implementados:
```
GET    /api/prompts              - Lista todos
GET    /api/prompts/:id          - Detalhes
POST   /api/prompts              - Criar
PUT    /api/prompts/:id          - Atualizar
GET    /api/prompts/:id/can-delete - Verificar deleção
DELETE /api/prompts/:id          - Deletar
GET    /api/prompts/categories   - Listar categorias
```

### 5. **Frontend - Admin Panel** ✅
**Arquivo**: `frontend/src/components/admin/PromptsManagement.tsx`

Features implementadas:
- Tabela profissional com 7 colunas
- Modal de criação/edição completo
- Validação de campos obrigatórios
- Confirmação de deleção com validação backend
- Template oculto (só visível ao editar)
- Suporte a ESC para fechar modal

### 6. **Frontend - Mode Selector** ✅
**Arquivo**: `frontend/src/components/Sidebar.tsx`

Toggle de modo em Configurações:
- 📂 Categoria (Rápido)
- 🤖 Inteligente (LLM)
- Persistência automática em `localStorage`

---

## ⚠️ O Que Ainda Precisa Ser Feito

### **Tarefa 1: Adicionar `prompt_mode` ao Schema de Request**

**Arquivo**: `src/api/schemas.py`

```python
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    top_k: int = 5
    temperature: Optional[float] = None
    include_sources: bool = True
    collection: Optional[str] = None
    debug: bool = False
    
    # ✅ ADICIONAR ESTE CAMPO
    prompt_mode: str = 'category'  # 'category' ou 'llm_router'
```

---

### **Tarefa 2: Integrar PromptManager em `query_rag_with_history`**

**Arquivo**: `src/core/rag.py`

**Localização**: Função `query_rag_with_history(...)` (aproximadamente linha 150)

**Substituir**:
```python
from src.core.prompts import get_active_prompt

# Linha atual (~160):
template = get_active_prompt('rag_prompt_enhanced_with_history')
```

**Por**:
```python
from src.core.prompt_manager import prompt_manager

# Nova implementação:
template = prompt_manager.get_prompt_for_category(
    category='rag_main',  # ou 'rag_main_with_history' se criada
    mode=prompt_mode,     # Vem do request
    context={
        'user_query': question,
        'question_type': question_type  # Se disponível
    }
)
```

**Onde pegar o `prompt_mode`**:
- Adicionar parâmetro `prompt_mode: str = 'category'` na assinatura da função
- Passar do endpoint `/api/chat` que já recebe do frontend

---

### **Tarefa 3: Integrar PromptManager na função `_build_prompt`**

**Arquivo**: `src/core/rag.py`

**Localização**: Função `_build_prompt(...)` (aproximadamente linha 80)

**Substituir**:
```python
from src.core.prompts import get_active_prompt

template = get_active_prompt('rag_prompt_enhanced')
```

**Por**:
```python
from src.core.prompt_manager import prompt_manager

template = prompt_manager.get_prompt_for_category(
    category='rag_main',
    mode=prompt_mode,
    context={
        'user_query': query,
        'question_type': question_type  # Se disponível
    }
)
```

---

### **Tarefa 4: Integrar PromptManager no HyDE**

**Arquivo**: `src/core/hyde.py`

**Localização**: Função `generate_hypothetical_document(...)` (aproximadamente linha 20)

**Substituir**:
```python
from src.core.prompts import get_active_prompt

template = get_active_prompt('hyde_prompt')
```

**Por**:
```python
from src.core.prompt_manager import prompt_manager

template = prompt_manager.get_prompt_for_category(
    category='hyde',
    mode=prompt_mode,
    context={'user_query': query}
)
```

**Nota**: Adicionar parâmetro `prompt_mode` na assinatura se necessário.

---

### **Tarefa 5: Integrar PromptManager no Query Expansion**

**Arquivo**: `src/core/query_expansion.py`

**Localização**: Função `expand_query(...)` (aproximadamente linha 15)

**Substituir**:
```python
from src.core.prompts import get_active_prompt

template = get_active_prompt('query_expansion_prompt')
```

**Por**:
```python
from src.core.prompt_manager import prompt_manager

template = prompt_manager.get_prompt_for_category(
    category='query_expansion',
    mode=prompt_mode,
    context={'user_query': query}
)
```

---

### **Tarefa 6: Atualizar Endpoint `/api/chat`**

**Arquivo**: `src/api/routes.py`

**Localização**: Endpoint `@api.route("/chat", methods=["POST"])` (aproximadamente linha 100)

**Adicionar extração do `prompt_mode`**:
```python
@api.route("/chat", methods=["POST"])
async def chat_endpoint():
    try:
        req = ChatRequest(**request.json)
        
        # ✅ ADICIONAR ESTA LINHA
        prompt_mode = req.prompt_mode  # Vem do schema atualizado
        
        # Passar para as funções RAG
        result = query_rag_with_history(
            question=req.question,
            session_id=req.session_id,
            prompt_mode=prompt_mode,  # ✅ PASSAR AQUI
            # ... outros parâmetros
        )
```

---

### **Tarefa 7: Frontend - Enviar `prompt_mode` no Request**

**Arquivo**: `frontend/src/api.ts`

**Localização**: Função `streamChat(...)` (aproximadamente linha 50)

**Atualizar**:
```typescript
export async function streamChat(
    question: string,
    sessionId: string | null,
    collection: string | null,
    onToken: (token: string) => void,
    debugMode: boolean = false,
    temperature?: number,
    promptMode: string = 'category'  // ✅ ADICIONAR PARÂMETRO
) {
    // ...
    
    body: JSON.stringify({
        question,
        session_id: sessionId,
        collection,
        debug: debugMode,
        temperature,
        prompt_mode: promptMode  // ✅ ENVIAR PARA BACKEND
    })
}
```

**E atualizar chamada em `App.tsx`**:
```typescript
// Passar promptMode do estado
const res = await streamChat(
    content, 
    currentSessionId, 
    selectedCollection, 
    onToken, 
    debugMode, 
    temperature,
    promptMode  // ✅ Estado já existe
);
```

---

## 🔍 Checklist de Integração

- [ ] 1. Adicionar `prompt_mode` ao `ChatRequest` schema
- [ ] 2. Integrar PromptManager em `query_rag_with_history()`
- [ ] 3. Integrar PromptManager em `_build_prompt()`
- [ ] 4. Integrar PromptManager em `generate_hypothetical_document()`
- [ ] 5. Integrar PromptManager em `expand_query()`
- [ ] 6. Atualizar endpoint `/api/chat` para extrair e passar `prompt_mode`
- [ ] 7. Atualizar `streamChat()` no frontend para enviar `prompt_mode`
- [ ] 8. Atualizar chamada em `App.tsx`
- [ ] 9. Testar modo 'category' end-to-end
- [ ] 10. Testar modo 'llm_router' end-to-end
- [ ] 11. Verificar fallbacks funcionando
- [ ] 12. Validar performance (~5ms category, ~200ms llm_router)

---

## 🧪 Como Testar Após Integração

### Teste 1: Modo Category
1. Abrir aplicação
2. Configurar modo "Categoria (Rápido)" na sidebar
3. Fazer uma pergunta
4. Verificar logs do backend:
   - `PromptManager: Using category mode`
   - Tempo de seleção ~5ms

### Teste 2: Modo LLM Router
1. Configurar modo "Inteligente (LLM)"
2. Fazer uma pergunta
3. Verificar logs do backend:
   - `PromptManager: Using LLM router mode`
   - Tempo de seleção ~200ms
   - Log da decisão do LLM

### Teste 3: Editar Prompt
1. Admin Panel → Tab "Prompts"
2. Editar `rag_prompt_enhanced`
3. Alterar template
4. Fazer pergunta no chat
5. Verificar que usa novo template

### Teste 4: Proteção de Deleção
1. Tentar deletar último prompt da categoria `rag_main`
2. Deve mostrar erro: "Não é possível deletar..."
3. Criar segundo prompt na categoria
4. Agora deletar primeiro deve funcionar

---

## 📊 Categorias de Prompts Atuais

| Categoria | Uso | Crítico? | Prompts Existentes |
|-----------|-----|----------|-------------------|
| `rag_main` | Prompt principal RAG | ✅ Sim | `rag_prompt_enhanced` |
| `hyde` | Geração doc hipotético | ✅ Sim | `hyde_prompt` |
| `query_expansion` | Expansão de queries | ✅ Sim | `query_expansion_prompt` |
| `instruction` | Classificação de perguntas | ❌ Não | 10 prompts `instruction_*` |

---

## 🚨 Pontos de Atenção

### 1. **Cache de Prompts**
- `PROMPT_CACHE` em `database.py` é thread-unsafe
- Para produção com multi-threading, adicionar lock:
```python
import threading
PROMPT_CACHE_LOCK = threading.Lock()
```

### 2. **Fallback Sempre Ativo**
- Se banco falhar, sistema usa prompts hardcoded de `config.py`
- Garante uptime mesmo com DB offline

### 3. **Performance do LLM Router**
- Adiciona ~200ms por request
- Considerar cache de decisões por hash de query para produção

### 4. **Validação de Categoria**
- Backend ainda aceita qualquer string como categoria
- Considerar adicionar validação:
```python
ALLOWED_CATEGORIES = {'rag_main', 'hyde', 'query_expansion', 'instruction', 'custom'}
```

---

## 📁 Estrutura de Arquivos Chave

```
rag/
├── alembic/versions/
│   └── 20251227_01_add_prompt_metadata.py  ✅ Migration
├── src/
│   ├── api/
│   │   ├── routes.py                       ⚠️ Precisa atualizar /chat
│   │   └── schemas.py                      ⚠️ Adicionar prompt_mode
│   ├── core/
│   │   ├── prompt_manager.py               ✅ Implementado
│   │   ├── rag.py                          ⚠️ Integrar PromptManager
│   │   ├── hyde.py                         ⚠️ Integrar PromptManager
│   │   └── query_expansion.py              ⚠️ Integrar PromptManager
│   └── data/
│       └── database.py                     ✅ CRUD completo
└── frontend/src/
    ├── api.ts                              ⚠️ Enviar prompt_mode
    ├── App.tsx                             ✅ Estado promptMode existe
    └── components/
        ├── Sidebar.tsx                     ✅ Mode selector
        └── admin/
            └── PromptsManagement.tsx       ✅ CRUD UI
```

---

## 💡 Melhorias Futuras (Opcional)

1. **Histórico de Versões**
   - Manter snapshots de versões anteriores
   - Rollback de prompts

2. **Analytics**
   - Rastrear qual prompt foi usado
   - Taxa de sucesso por prompt
   - A/B testing automático

3. **Importar/Exportar**
   - JSON export de prompts
   - Backup/restore

4. **Templates Dinâmicos**
   - Variáveis customizadas
   - Condicionais no template

5. **Modo Híbrido**
   - Category para primeira mensagem
   - LLM Router apenas quando múltiplos candidatos

---

## 📞 Contato & Suporte

Em caso de dúvidas durante a implementação, revisar:
- Este documento (`docs/prompt_migration.md`)
- Código existente em `src/core/prompt_manager.py`
- Backend review: `.gemini/antigravity/brain/[id]/backend_review.md`
- Walkthrough: `.gemini/antigravity/brain/[id]/walkthrough.md`

**Boa implementação! 🚀**
