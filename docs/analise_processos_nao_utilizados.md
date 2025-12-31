# Análise de Processos Não Utilizados no Projeto RAG

**Data:** 31/12/2025  
**Objetivo:** Identificar processos que foram criados mas não estão sendo usados na aplicação

---

## Resumo Executivo

Foram identificados **3 processos principais** que foram criados mas **NÃO estão sendo utilizados** na aplicação, além de **1 recurso parcialmente implementado**.

---

## 📊 Processos NÃO Utilizados

### 1. ❌ Prompt Manager (`src/core/prompt_manager.py`)

**Status:** CRIADO MAS NÃO UTILIZADO

**Descrição:** Sistema de gerenciamento de prompts com seleção inteligente baseada em categoria, incluindo suporte para prompts dinâmicos via LLM.

**Funcionalidades Criadas:**
- `PromptManager` class com seleção inteligente de prompts
- `get_prompt_for_category()` - Seleciona prompt apropriado
- `get_instruction_prompt()` - Retorna instruções por tipo de pergunta
- Fallback para prompts padrão quando seleção falha

**Por que NÃO está sendo usado:**
- O sistema usa diretamente `src/core/prompts.py` e `src/core/rag/services/prompt_service.py`
- Não há imports ou chamadas ao `PromptManager` em nenhum lugar do código
- As funções de prompt estão hardcoded no `PromptService`

**Código Criado vs. Atual:**
```python
# CRIADO (src/core/prompt_manager.py):
prompt_manager = PromptManager()
instruction = prompt_manager.get_instruction_prompt(question_type)

# UTILIZADO ATUALMENTE (src/core/rag/services/prompt_service.py):
def build_prompt(self, ...):
    # Usa instruções fixas do question_classifier diretamente
    from src.core.question_classifier import get_instructions_for_type
    instruction = get_instructions_for_type(question_type)
```

**Impacto:** Não há impacto negativo, pois a funcionalidade está sendo implementada de outra forma.

---

### 2. ❌ Encryption Manager (`src/core/encryption.py`)

**Status:** CRIADO MAS NÃO UTILIZADO

**Descrição:** Sistema completo de criptografia de dados sensíveis (AES-256-GCM) com suporte a campos específicos.

**Funcionalidades Criadas:**
- `EncryptionManager` class
- `encrypt()` / `decrypt()` - Criptografia/descriptografia de strings
- `encrypt_dict()` / `decrypt_dict()` - Criptografia de dicionários
- `encrypt_if_sensitive()` / `decrypt_if_encrypted()` - Criptografia condicional
- Suporte para gerar chaves a partir de senhas
- Funções de conveniência: `encrypt_data()`, `decrypt_data()`, etc.

**Configuração:**
```python
# src/config.py:
ENABLE_ENCRYPTION: bool = False  # DESABILITADO POR PADRÃO
ENCRYPT_DOCUMENT_CONTENT: bool = True
ENCRYPT_METADATA: bool = True
ENCRYPT_FEEDBACK_COMMENTS: bool = True
```

**Por que NÃO está sendo usado:**
- `ENABLE_ENCRYPTION = False` no arquivo de configuração
- Não há imports de `encryption.py` nos módulos de dados
- Nenhum repositório ou serviço usa as funções de criptografia
- O banco de dados armazena texto em plain text

**Código Esperado vs. Realidade:**
```python
# DEVERIA SER USADO (exemplo hipotético):
from src.core.encryption import encrypt_if_sensitive, decrypt_if_encrypted

# Ao salvar documento:
document.content = encrypt_if_sensitive(content, is_sensitive=True)

# Ao recuperar documento:
content = decrypt_if_encrypted(document.content, is_encrypted=True)

# REALIDADE: Nada disso existe no código
```

**Impacto:** Dados sensíveis NÃO estão sendo criptografados, mesmo que a funcionalidade esteja implementada.

---

### 3. ❌ Evaluation System (`src/core/evaluation.py`)

**Status:** CRIADO MAS NÃO UTILIZADO

**Descrição:** Sistema de avaliação automática de respostas RAG com métricas de fidelidade, relevância e precisão do contexto.

**Funcionalidades Criadas:**
- `calculate_faithfulness()` - Verifica se resposta é fiel ao contexto
- `calculate_answer_relevancy()` - Mede relevância da resposta à pergunta
- `calculate_context_precision()` - Avalia precisão dos chunks recuperados
- `evaluate_rag_response()` - Avaliação completa com todas as métricas
- `get_evaluation_summary()` - Gera resumo textual das métricas

**Configuração:**
```python
# src/config.py:
ENABLE_AUTO_EVALUATION: bool = False  # DESABILITADO POR PADRÃO
```

**Uso Atual:**
```python
# src/api/routes/metrics.py:
@metrics_bp.route("/evaluate", methods=["POST"])
def evaluate():
    # Endpoint EXISTE para avaliação manual
    from src.core.evaluation import evaluate_rag_response
    # ...
```

**Por que NÃO está sendo usado:**
- `ENABLE_AUTO_EVALUATION = False` - Não está sendo executado automaticamente
- Não é chamado no pipeline RAG principal (`src/core/rag/pipeline.py`)
- Está disponível apenas via endpoint manual `/metrics/evaluate`

**Código Esperado vs. Realidade:**
```python
# DEVERIA SER USADO (automaticamente no pipeline):
if ENABLE_AUTO_EVALUATION:
    evaluation_scores = evaluate_rag_response(question, answer, context)
    metrics["evaluation"] = evaluation_scores

# REALIDADE: O pipeline NÃO chama evaluate_rag_response()
```

**Impacto:** O sistema não avalia automaticamente a qualidade das respostas geradas.

---

## 🔧 Recursos Parcialmente Implementados

### 4. ⚠️ Query Expansion (`src/core/query_expansion.py`)

**Status:** CRIADO E CONFIGURADO, MAS NÃO IMPLEMENTADO NO PIPELINE

**Descrição:** Sistema de expansão de queries para melhorar a recuperação de documentos.

**Funcionalidades Criadas:**
- `expand_query()` - Gera queries alternativas
- `merge_search_results()` - Mescla resultados de múltiplas queries

**Configuração:**
```python
# src/config.py:
ENABLE_QUERY_EXPANSION: bool = True  # HABILITADO
QUERY_EXPANSION_COUNT: int = 3
```

**Uso Atual:**
```python
# src/core/rag/strategies/retrieval_strategy.py:
def apply_phase2_pipeline(self, ...):
    # 1. Query Expansion (Simulado ou Real se disponível)
    if self._enable_query_expansion:
        # expander = _get_query_expansion()
        # ...  # CÓDIGO COMENTADO - NÃO IMPLEMENTADO
        pass
```

**Por que NÃO está sendo usado:**
- O código está comentado em `RetrievalStrategy.apply_phase2_pipeline()`
- Apesar de `ENABLE_QUERY_EXPANSION = True`, a funcionalidade não é executada

**Impacto:** O recurso está configurado mas não está funcionando de fato.

---

## 📈 Processos UTILIZADOS (Referência)

Para fins de comparação, estes processos **ESTÃO sendo usados**:

✅ **Adaptive Retrieval** (`src/core/adaptive_retrieval.py`)  
✅ **Advanced Batch Processor** (`src/core/advanced_batch_processor.py`)  
✅ **Connection Pool** (`src/core/connection_pool.py`)  
✅ **Context Compression** (`src/core/context_compression.py`)  
✅ **Conversation Manager** (`src/core/conversation.py`)  
✅ **Embeddings** (`src/core/embeddings.py`)  
✅ **Embedding Cache** (`src/core/embedding_cache.py`)  
✅ **HyDE** (`src/core/hyde.py`)  
✅ **Language Detector** (`src/core/language_detector.py`) - Usado no chunking  
✅ **LLM** (`src/core/llm.py`)  
✅ **Logger** (`src/core/logger.py`)  
✅ **Metrics** (`src/core/metrics.py`)  
✅ **MMR** (`src/core/mmr.py`)  
✅ **Prompts** (`src/core/prompts.py`)  
✅ **Question Classifier** (`src/core/question_classifier.py`)  
✅ **RAG Explainer** (`src/core/rag_explainer.py`)  
✅ **Reranker** (`src/core/reranker.py`)  
✅ **Security** (`src/core/security.py`)  
✅ **Self-RAG** (`src/core/self_rag.py`) - Parcialmente (configurado mas não usado ativamente)

---

## 🎯 Recomendações

### 1. Prompt Manager
**Ação:** Remover ou Integrar  
**Razão:** Não há necessidade imediata, pois o sistema atual funciona bem sem ele. Se quiser manter, deve substituir completamente o sistema atual de prompts.

### 2. Encryption Manager
**Ação:** Implementar ou Remover  
**Razão:** Se dados sensíveis precisam de criptografia, implementar imediatamente. Se não, remover para evitar confusão.

**Sugestão de implementação:**
```python
# src/data/repositories/document_repository.py
from src.core.encryption import encrypt_if_sensitive, decrypt_if_encrypted

# Ao salvar:
if ENABLE_ENCRYPTION:
    document.content = encrypt_if_sensitive(content, is_sensitive=True)
    
# Ao recuperar:
if ENABLE_ENCRYPTION:
    content = decrypt_if_encrypted(document.content, is_encrypted=True)
```

### 3. Evaluation System
**Ação:** Implementar avaliação automática ou manter apenas manual  
**Razão:** A avaliação manual via endpoint é útil, mas automatica seria melhor para qualidade.

**Sugestão de implementação:**
```python
# src/core/rag/pipeline.py
from src.core.evaluation import evaluate_rag_response

# No final do método query():
if ENABLE_AUTO_EVALUATION:
    evaluation_scores = evaluate_rag_response(
        question=question,
        answer=answer,
        context=raw_context
    )
    result["evaluation"] = evaluation_scores
```

### 4. Query Expansion
**Ação:** Implementar o código comentado ou desabilitar configuração  
**Razão:** Está configurado mas não funciona. Ou implementar ou desabilitar para não confundir.

**Sugestão de implementação:**
```python
# src/core/rag/strategies/retrieval_strategy.py
if self._enable_query_expansion:
    from src.core.query_expansion import expand_query, merge_search_results
    
    expanded_queries = expand_query(question)
    all_results = initial_results.copy()
    
    for eq in expanded_queries[:QUERY_EXPANSION_COUNT]:
        eq_embedding = get_embedding(eq)
        eq_results = self.search.search(eq, eq_embedding, top_k=5)
        all_results.extend(eq_results)
    
    # Mesclar e deduplicar
    results = merge_search_results(all_results, final_top_k * 2)
```

---

## 📊 Estatísticas

- **Total de processos em src/core/:** 23
- **Processos utilizados:** 19 (82.6%)
- **Processos não utilizados:** 3 (13.0%)
- **Processos parcialmente implementados:** 1 (4.4%)

---

## 🔍 Arquivos Analisados

### Configuração
- `src/config.py` - Variáveis de ambiente e configurações

### API Routes
- `src/app.py` - Aplicação Flask principal
- `src/api/routes/__init__.py` - Blueprint principal e scheduler
- `src/api/routes/query.py` - Endpoints de query RAG
- `src/api/routes/metrics.py` - Endpoints de métricas
- `src/api/routes/admin.py` - Endpoints administrativos
- `src/api/routes/sessions.py` - Endpoints de sessões
- `src/api/routes/documents.py` - Endpoints de documentos
- `src/api/routes/prompts.py` - Endpoints de prompts
- `src/api/routes/health.py` - Endpoints de health check

### Core
- `src/core/rag.py` - Fachada RAG
- `src/core/rag/pipeline.py` - Pipeline principal
- `src/core/rag/strategies/retrieval_strategy.py` - Estratégias de recuperação
- `src/core/rag/services/` - Serviços do RAG

### Data
- `src/data/ingestion.py` - Ingestão de documentos
- `src/data/chunking.py` - Chunking de textos
- `src/data/repositories/` - Repositórios de dados

---

## 📝 Conclusão

O projeto está bem estruturado com a maioria dos processos (82.6%) sendo utilizados adequadamente. Os 3 processos não utilizados representam funcionalidades que foram planejadas mas nunca integradas:

1. **Prompt Manager** - Sistema alternativo de gerenciamento de prompts não necessário
2. **Encryption Manager** - Criptografia não implementada apesar de estar pronta
3. **Evaluation System** - Avaliação automática não integrada ao pipeline

O **Query Expansion** merece atenção especial pois está configurado como habilitado mas o código está comentado.

**Recomendação geral:** Revisar esses processos não utilizados e decidir se devem ser implementados, removidos ou mantidos como recursos futuros.
