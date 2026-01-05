# Implementação de Logging Estruturado - Resumo

## Overview
Sistema de logging estruturado implementado para rastrear todo o fluxo das requisições RAG, desde a entrada na API até a geração da resposta pelo LLM, permitindo fácil diagnóstico de problemas.

## Arquitetura do Sistema

### 1. Request ID (Rastreamento)
- **Geração**: Cada requisição recebe um `request_id` único no endpoint da API
- **Formatação**: `[timestamp]-[random_chars]` (ex: `1704227123-abc123xyz`)
- **Propagação**: O `request_id` é propagado por toda a stack (API → Pipeline → Services)
- **Benefício**: Permite correlacionar todos os logs de uma única requisição

### 2. Helpers de Logging (`src/core/logger.py`)

#### Funções Auxiliares
- **`generate_request_id()`**: Gera IDs únicos para requisições
- **`log_step(logger, step_name, **data)`**: Loga um passo específico do fluxo
- **`log_error(logger, component, error, **context)`**: Loga erros com contexto completo

#### Context Manager
- **`log_stage(stage_name, logger, **extra_data)`**: Envolve código para logar início/fim
  ```python
  with log_stage("Embedding", logger, request_id="abc-123"):
      embedding = get_embedding(text)
  # Loga automaticamente: [Embedding] Started | request_id=abc-123
  #                       [Embedding] Completed | request_id=abc-123 | duration=0.234s
  ```

#### Decorators
- **`@log_flow(flow_name)`**: Loga início/fim de um fluxo completo
- **`@log_exceptions(logger)`**: Loga exceções com contexto detalhado

## Fluxo de Logging por Componente

### 1. API Routes (`src/api/routes/query.py`)

**Endpoints implementados:**
- `POST /api/query` - Query RAG principal
- `POST /api/query/stream` - Query com streaming
- `POST /api/search` - Apenas busca
- `POST /api/chat` - Chat com histórico

**Logs gerados:**
```
[API Request Received] | request_id=1704227123-abc123 | endpoint=/api/query | method=POST
[Validation Passed] | request_id=1704227123-abc123
[Query Success] | request_id=1704227123-abc123 | status_code=200 | total_duration=2.456s
```

**Exceções:**
```
[Query Failed] | request_id=1704227123-abc123 | error_type=ConnectionError | error_message=...
```

### 2. RAG Pipeline (`src/core/rag/pipeline.py`)

**Fases com logging:**

1. **Query Started**
   - question, top_k, collection_id

2. **Strategy Determined**
   - strategy (hierarchical/sentence)
   - use_sentence_window

3. **Classification**
   - question_type

4. **Adaptive Retrieval**
   - adaptive_params (complexity_score, word_count, top_k, min_similarity)

5. **Embedding**
   - dimension (768)

6. **Search**
   - search_type (hybrid/vector/sentence)
   - documents_found

7. **Reranking**
   - documents_after_rerank

8. **Context Building**
   - context_chars
   - was_compressed

9. **Prompt Building**
   - prompt_length

10. **LLM**
    - answer_length

11. **Query Complete**
    - total_duration
    - status

**Exemplo de log completo:**
```
[Query Started] | request_id=1704227123-abc123 | question=Como funciona o sistema? | top_k=5
[Strategy Determined] | request_id=1704227123-abc123 | strategy=hierarchical | use_sentence_window=False
[Classification] Started | request_id=1704227123-abc123
[Classification] Completed | request_id=1704227123-abc123 | duration=0.012s
[Classification Complete] | request_id=1704227123-abc123 | question_type=explanation
[Adaptive Retrieval] Started | request_id=1704227123-abc123
[Adaptive Applied] | request_id=1704227123-abc123 | adaptive_params={...}
[Adaptive Retrieval] Completed | request_id=1704227123-abc123 | duration=0.045s
[Embedding] Started | request_id=1704227123-abc123
[Embedding] Completed | request_id=1704227123-abc123 | duration=0.123s
[Embedding Generated] | request_id=1704227123-abc123 | dimension=768
[Search] Started | request_id=1704227123-abc123
[Search] Completed | request_id=1704227123-abc123 | duration=0.456s
[Search Complete] | request_id=1704227123-abc123 | documents_found=15
[Reranking] Started | request_id=1704227123-abc123
[Reranking] Completed | request_id=1704227123-abc123 | duration=0.234s
[Reranking Complete] | request_id=1704227123-abc123 | documents_after_rerank=5
[Context Building] Started | request_id=1704227123-abc123
[Context Building] Completed | request_id=1704227123-abc123 | duration=0.023s
[Context Ready] | request_id=1704227123-abc123 | context_chars=2500 | was_compressed=false
[Prompt Building] Started | request_id=1704227123-abc123
[Prompt Building] Completed | request_id=1704227123-abc123 | duration=0.001s
[Prompt Built] | request_id=1704227123-abc123 | prompt_length=2800
[LLM] Started | request_id=1704227123-abc123
[LLM] Completed | request_id=1704227123-abc123 | duration=1.234s
[LLM Complete] | request_id=1704227123-abc123 | answer_length=450
[Query Complete] | request_id=1704227123-abc123 | total_duration=2.500s | status=success
```

### 3. Search Service (`src/core/rag/services/search_service.py`)

**Operações com logging:**
- **Search Started**: search_type, top_k, alpha, chunking_type, collection_id
- **Hybrid Search / Vector Search**: Resultados da busca vetorial/híbrida
- **Sentence Window Search**: Fases específicas para busca com janela de sentenças
  - Sentence Search
  - Grouping by Document
  - Window Expansion
  - Window Expansion Complete

**Exemplo:**
```
[Search Started] | request_id=1704227123-abc123 | search_type=hybrid | top_k=5 | alpha=0.7
[Hybrid Search] Started | request_id=1704227123-abc123
[Hybrid Search] Completed | request_id=1704227123-abc123 | duration=0.456s
[Hybrid Search Complete] | request_id=1704227123-abc123 | results=15
```

### 4. LLM Service (`src/core/llm.py`)

**Logs implementados:**
- **LLM Request Started**: model, prompt_length, max_tokens, temperature, stream
- **LLM Response Received**: response_length, duration
- **LLM Complete**: total_duration, status
- **LLM Stream Started**: model
- **LLM Stream Complete**: status
- Logs existentes mantidos: `log_llm_request`, `log_llm_response`, `log_llm_full_request`, `log_llm_full_response`

**Exemplo:**
```
[LLM Request Started] | request_id=1704227123-abc123 | model=phi-3.5-mini | prompt_length=2800 | max_tokens=1024 | temperature=0.7
[LLM Response Received] | request_id=1704227123-abc123 | response_length=450 | duration=1.234s
[LLM Complete] | request_id=1704227123-abc123 | total_duration=1.234s | status=success
```

### 5. Embeddings (`src/core/embeddings.py`)

**Logs implementados:**
- **Embedding from Cache**: text_length (se recuperado do cache)
- **Embedding Generation Started**: text_length
- **Embedding Generated**: dimension, duration, was_cached
- **Embedding Cached**: (quando salvo no cache)
- **Batch Embedding Started**: document_name, texts_count, batch_size
- **Batch Embedding Complete**: document_name, total_embeddings, total_duration

**Exemplo:**
```
[Embedding Generation Started] | request_id=1704227123-abc123 | text_length=120
[Embedding Generated] | request_id=1704227123-abc123 | dimension=768 | duration=0.123s | was_cached=false
[Embedding Cached] | request_id=1704227123-abc123
```

### 6. Hybrid Search (`src/data/hybrid_search.py`)

**Logs implementados:**
- **Hybrid Search Started**: alpha, top_k, collection_id
- **Vector Search Results**: results (quantidade de resultados vetoriais)
- **FTS Search Results**: results (quantidade de resultados FTS)
- **Hybrid Search Complete**: vector_results, fts_results, final_results, total_duration

**Exemplo:**
```
[Hybrid Search Started] | request_id=1704227123-abc123 | alpha=0.7 | top_k=5
[Vector Search Results] | request_id=1704227123-abc123 | results=15
[FTS Search Results] | request_id=1704227123-abc123 | results=20
[Hybrid Search Complete] | request_id=1704227123-abc123 | vector_results=15 fts_results=20 final_results=5 | total_duration=0.456s
```

### 7. Reranker (`src/core/reranker.py`)

**LLM Reranker:**
- **LLM Reranking Started**: chunks_count, top_k, model
- **LLM Rerank Scored**: model, score (para cada chunk)
- **LLM Reranking Complete**: results_returned
- **Reranking Skipped (No Chunks)**: quando não há chunks

**Cross-Encoder Reranker:**
- **Cross-Encoder Reranking Started**: chunks_count, top_k, model, api_url
- **Cross-Encoder Reranking Complete**: results_returned
- Erros são logados com contexto completo

**Exemplo:**
```
[LLM Reranking Started] | request_id=1704227123-abc123 | chunks_count=15 | top_k=5 | model=phi-3.5-mini
[LLM Rerank Scored] | request_id=1704227123-abc123 | model=phi-3.5-mini | score=0.85
...
[LLM Reranking Complete] | request_id=1704227123-abc123 | results_returned=5
```

### 8. Context Service (`src/core/rag/services/context_service.py`)

**Logs implementados:**
- **Context Building Started**: documents_count, max_chars
- **Context Built**: documents_included, context_chars
- **Compression Check**: original_tokens, compression_enabled, threshold
- **Compression Skipped**: reason (disabled ou below_threshold)
- **Compression Started**: method, original_tokens
- **Compression Complete**: method, original_tokens, final_tokens, compression_ratio

**Exemplo:**
```
[Context Building Started] | request_id=1704227123-abc123 | documents_count=5 | max_chars=12000
[Context Built] | request_id=1704227123-abc123 | documents_included=5 | context_chars=2500
[Compression Check] | request_id=1704227123-abc123 | original_tokens=625 | compression_enabled=true | threshold=1000
[Compression Skipped] | request_id=1704227123-abc123 | reason=below_threshold
```

**Exemplo com compressão:**
```
[Compression Check] | request_id=1704227123-abc123 | original_tokens=3000 | compression_enabled=true | threshold=1000
[Compression Started] | request_id=1704227123-abc123 | method=llm | original_tokens=3000
[Compression Complete] | request_id=1704227123-abc123 | method=llm | original_tokens=3000 final_tokens=1200 | compression_ratio=0.40
```

## Formato dos Logs

### Estrutura Básica
```
timestamp level logger_name mensagem | request_id=X | chave1=valor1 chave2=valor2 ...
```

### Níveis de Log
- **INFO**: Fluxo normal (início/completação de fases)
- **DEBUG**: Informações detalhadas (cache hits, etc.)
- **WARNING**: Situações não críticas mas dignas de atenção
- **ERROR**: Falhas com stacktrace completo

### Arquivo de Log
- **Caminho**: `logs/server.log`
- **Formato**: JSON estruturado para fácil parsing
- **Consolidação**: Todos os logs do backend em um único arquivo

## Benefícios do Sistema

### 1. Rastreamento Completo
- Cada requisição tem um ID único
- Todas as operações são logadas com o mesmo ID
- Fácil seguir o fluxo de ponta a ponta

### 2. Diagnóstico de Problemas
- **Tempo de cada fase**: Identificar gargalos de performance
- **Contexto de erros**: Saber exatamente onde e por que falhou
- **Dados estruturados**: Facilita análise com ferramentas (jq, grep, ELK, etc.)

### 3. Exemplos de Diagnóstico

#### Problema: Query demorando muito
```
# Buscar request_id nos logs
grep "request_id=1704227123-abc123" logs/server.log

# Identificar fase mais lenta
[Embedding] Completed | request_id=1704227123-abc123 | duration=0.500s  # LENTO
[Search] Completed | request_id=1704227123-abc123 | duration=0.200s
[LLM] Completed | request_id=1704227123-abc123 | duration=0.800s
```
→ Problema no serviço de embeddings!

#### Problema: Nenhum resultado encontrado
```
[Search Complete] | request_id=1704227123-abc123 | documents_found=0
[No Results Found] | request_id=1704227123-abc123 | question=Como funciona o X?
```
→ Verificar embedding da pergunta ou similaridade mínima

#### Problema: Erro no LLM
```
[LLM] Failed | request_id=1704227123-abc123 | duration=5.000s | error=Connection timeout
[LLM Request] LLM Request Started | request_id=1704227123-abc123 | model=phi-3.5-mini | prompt_length=2800
```
→ Serviço LLM indisponível ou timeout

## Próximas Melhorias (Opcional)

### 1. Dashboard de Logs
- Interface web para visualizar logs em tempo real
- Filtros por request_id, componente, nível de log
- Gráficos de performance

### 2. Alertas Automáticos
- Monitorar erros frequentes
- Alertar se tempo médio de uma fase aumenta
- Detectar anomalias de performance

### 3. Análise de Logs
- Scripts para análise de performance
- Identificação de padrões de erro
- Métricas agregadas (P50, P95, P99)

## Como Usar

### Para Diagnosticar uma Requisição Específica

1. **Encontrar o request_id**:
   ```bash
   tail -f logs/server.log | grep "API Request Received"
   ```

2. **Seguir o fluxo completo**:
   ```bash
   grep "request_id=1704227123-abc123" logs/server.log | tail -50
   ```

3. **Analisar erro específico**:
   ```bash
   grep "request_id=1704227123-abc123" logs/server.log | grep ERROR
   ```

### Para Monitorar em Tempo Real

```bash
tail -f logs/server.log
```

### Para Filtrar por Componente

```bash
# Apenas API
grep "\[API Request Received\]" logs/server.log

# Apenas Pipeline RAG
grep "Query Started" logs/server.log

# Apenas Erros
grep ERROR logs/server.log
```

## Conclusão

O sistema de logging estruturado implementado permite:
- ✅ Rastreamento completo de cada requisição
- ✅ Diagnóstico rápido de problemas
- ✅ Análise de performance por fase
- ✅ Contexto detalhado em erros
- ✅ Facilidade de manutenção e debugging

Os logs agora são profissionais, estruturados e prontos para uso em produção!
