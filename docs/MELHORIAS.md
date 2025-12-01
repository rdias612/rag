# 🚀 Melhorias Planejadas para o Sistema RAG

Este documento lista as melhorias identificadas para o sistema RAG, organizadas por prioridade e impacto.

---

## 🔴 Alta Prioridade

### 1. Re-ranking dos Resultados
**Impacto:** ⭐⭐⭐⭐ | **Esforço:** Médio

Aplicar um modelo de re-ranking após a busca vetorial para melhorar a precisão.

**Fluxo proposto:**
```
Query → Busca Vetorial (Top 20) → Re-ranker → Top 5 Finais
```

**Benefícios:**
- Maior precisão nos resultados retornados
- Melhor qualidade das respostas do LLM
- Redução de chunks irrelevantes no contexto

**Modelos sugeridos:** `cross-encoder/ms-marco-MiniLM-L-6-v2`

---

## 🟡 Média Prioridade

### 2. Cache de Embeddings
**Impacto:** ⭐⭐⭐ | **Esforço:** Baixo

Evitar recalcular embeddings para perguntas repetidas ou similares.

**Opções de implementação:**
- **Memória:** `functools.lru_cache` ou dict simples
- **PostgreSQL:** Tabela de cache com hash da query
- **Redis:** Para ambientes distribuídos

**Benefícios:**
- Redução de latência
- Menor uso da API de embeddings
- Melhor experiência do usuário

---

### 3. Métricas e Monitoramento
**Impacto:** ⭐⭐⭐ | **Esforço:** Médio

Coletar métricas para análise e melhoria contínua:

| Métrica | Descrição |
|---------|-----------|
| Tempo de resposta | Por componente (embedding, busca, LLM) |
| Taxa de "não encontrei" | Percentual de queries sem resultado |
| Similaridade média | Qualidade das buscas |
| Tokens utilizados | Custo de processamento |

**Ferramentas sugeridas:** Prometheus + Grafana, ou logging estruturado

---

## 🟢 Baixa Prioridade

### 4. Busca Híbrida (Vetorial + Keyword) ✅
**Impacto:** ⭐⭐⭐ | **Esforço:** Alto | **Status:** Implementado

Combinar busca semântica (vetorial) com busca por palavras-chave (BM25).

**Benefícios:**
- Captura termos exatos que a busca vetorial pode perder
- Melhor para siglas e nomes próprios
- Resultados mais completos

**Implementação:**
- Módulo `src/data/hybrid_search.py` com busca híbrida usando RRF (Reciprocal Rank Fusion)
- PostgreSQL Full-Text Search (tsvector + GIN index) + pgvector
- Configurações em `src/config.py`:
  - `ENABLE_HYBRID_SEARCH`: Habilita/desabilita busca híbrida
  - `HYBRID_SEARCH_ALPHA`: Peso da busca vetorial (0.7 = 70% vetorial, 30% FTS)
- Funções disponíveis:
  - `init_fulltext_search()`: Inicializa estruturas de FTS
  - `search_hybrid()`: Busca combinando vetorial + FTS
  - `search_fulltext()`: Busca apenas por palavras-chave
- Métricas de busca incluídas na resposta do RAG

---

### 6. Sistema de Feedback
**Impacto:** ⭐⭐⭐ | **Esforço:** Médio

Coletar feedback do usuário para melhorar o sistema.

```json
POST /api/feedback
{
  "query_id": "uuid",
  "rating": 4,
  "comment": "Resposta útil mas incompleta"
}
```

**Uso:** Retreinar embeddings, ajustar prompts, identificar gaps

---

### 7. Modo Debug Avançado
**Impacto:** ⭐⭐ | **Esforço:** Baixo

Endpoint que expõe todo o pipeline para debugging.

```json
GET /api/query?question=...&debug=true

Response:
{
  "answer": "...",
  "debug": {
    "embedding_time_ms": 45,
    "search_time_ms": 12,
    "llm_time_ms": 2300,
    "chunks_found": [...],
    "prompt_sent": "...",
    "similarities": [0.85, 0.72, ...]
  }
}
```

---

### 8. Testes Automatizados
**Impacto:** ⭐⭐⭐⭐ | **Esforço:** Alto

Implementar suíte de testes completa:

| Tipo | Cobertura |
|------|-----------|
| Unitários | Cada módulo isoladamente |
| Integração | Fluxo completo do RAG |
| Qualidade | Benchmark de respostas |
| Performance | Tempo de resposta |

**Ferramentas:** `pytest`, `pytest-asyncio`, `pytest-cov`

---

*Última atualização: Novembro 2025*
