# 🚀 Melhorias Planejadas para o Sistema RAG

Este documento lista as melhorias identificadas para o sistema RAG, organizadas por prioridade e impacto.

---

## 🔴 Alta Prioridade

### 1. Chunking Semântico
**Impacto:** ⭐⭐⭐⭐⭐ | **Esforço:** Médio

O chunking atual é baseado apenas em contagem de caracteres, o que pode resultar em:
- Frases cortadas no meio
- Perda de contexto semântico
- Chunks começando/terminando em locais inadequados

**Solução proposta:**
- Implementar chunking baseado em sentenças e parágrafos
- Respeitar limites naturais do texto (pontuação, quebras de linha)
- Manter a coesão semântica de cada chunk

**Bibliotecas sugeridas:** `langchain`, `spacy`, `nltk`

---

### 2. Re-ranking dos Resultados
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

### 3. Filtro de Similaridade Mínima
**Impacto:** ⭐⭐⭐ | **Esforço:** Baixo

Atualmente, o sistema retorna `top_k` resultados independentemente da similaridade.

**Problema:**
```python
# Atual: retorna 5 chunks mesmo que tenham baixa similaridade
similar_docs = search_similar(embedding, top_k=5)
```

**Solução:**
```python
# Proposto: filtrar por threshold
MIN_SIMILARITY = 0.5
similar_docs = [doc for doc in results if doc["similarity"] >= MIN_SIMILARITY]
```

---

### 4. Suporte a Mais Formatos de Documentos
**Impacto:** ⭐⭐⭐ | **Esforço:** Baixo

Expandir além de PDF para suportar:

| Formato | Biblioteca |
|---------|------------|
| `.docx` | `python-docx` |
| `.txt` | nativo |
| `.md` | `markdown` |
| `.html` | `beautifulsoup4` |

---

## 🟡 Média Prioridade

### 5. Cache de Embeddings
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

### 6. Histórico de Conversas
**Impacto:** ⭐⭐⭐⭐ | **Esforço:** Médio

Permitir perguntas de follow-up mantendo o contexto da conversa.

**Exemplo de uso:**
```
Usuário: "O que é GWPRP?"
Sistema: "GWPRP é um protocolo de roteamento..."
Usuário: "Quem desenvolveu?"  ← Entende que se refere ao GWPRP
```

**Estrutura proposta:**
```json
{
  "session_id": "uuid",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "created_at": "timestamp"
}
```

---

### 7. Validação e Segurança de Input
**Impacto:** ⭐⭐ | **Esforço:** Baixo

Implementar validações para:
- Limitar tamanho máximo da pergunta (ex: 2000 caracteres)
- Sanitizar inputs contra injeção
- Rate limiting por IP/sessão
- Validação de tipos de dados

---

### 8. Métricas e Monitoramento
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

### 9. Endpoint de Ingestão via API
**Impacto:** ⭐⭐ | **Esforço:** Baixo

Permitir upload de documentos pela API REST.

```http
POST /api/ingest
Content-Type: multipart/form-data

file: documento.pdf
```

**Funcionalidades:**
- Upload de arquivos
- Processamento assíncrono
- Status de ingestão
- Listagem de documentos

---

## 🟢 Baixa Prioridade

### 10. Busca Híbrida (Vetorial + Keyword)
**Impacto:** ⭐⭐⭐ | **Esforço:** Alto

Combinar busca semântica (vetorial) com busca por palavras-chave (BM25).

**Benefícios:**
- Captura termos exatos que a busca vetorial pode perder
- Melhor para siglas e nomes próprios
- Resultados mais completos

**Implementação:** PostgreSQL Full-Text Search + pgvector

---

### 11. Compressão de Contexto
**Impacto:** ⭐⭐ | **Esforço:** Médio

Quando o contexto for muito grande, resumir antes de enviar ao LLM.

**Cenário:**
```
5 chunks × 800 chars = 4000 chars de contexto
↓ Compressão
2000 chars mantendo informações essenciais
```

---

### 12. Sistema de Feedback
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

### 13. Modo Debug Avançado
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

### 14. Testes Automatizados
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

## 📊 Matriz de Priorização

| Melhoria | Impacto | Esforço | Prioridade |
|----------|---------|---------|------------|
| Chunking Semântico | ⭐⭐⭐⭐⭐ | Médio | 🔴 Alta |
| Re-ranking | ⭐⭐⭐⭐ | Médio | 🔴 Alta |
| Filtro de Similaridade | ⭐⭐⭐ | Baixo | 🔴 Alta |
| Mais Formatos | ⭐⭐⭐ | Baixo | 🔴 Alta |
| Cache de Embeddings | ⭐⭐⭐ | Baixo | 🟡 Média |
| Histórico de Conversas | ⭐⭐⭐⭐ | Médio | 🟡 Média |
| Validação de Input | ⭐⭐ | Baixo | 🟡 Média |
| Métricas | ⭐⭐⭐ | Médio | 🟡 Média |
| Upload via API | ⭐⭐ | Baixo | 🟡 Média |
| Busca Híbrida | ⭐⭐⭐ | Alto | 🟢 Baixa |
| Compressão de Contexto | ⭐⭐ | Médio | 🟢 Baixa |
| Feedback Loop | ⭐⭐⭐ | Médio | 🟢 Baixa |
| Modo Debug | ⭐⭐ | Baixo | 🟢 Baixa |
| Testes | ⭐⭐⭐⭐ | Alto | 🟢 Baixa |

---

## 🎯 Roadmap Sugerido

### Fase 1 - Qualidade (Semanas 1-2)
- [ ] Implementar filtro de similaridade mínima
- [ ] Melhorar chunking com divisão por sentenças
- [ ] Adicionar suporte a `.txt` e `.docx`

### Fase 2 - Usabilidade (Semanas 3-4)
- [ ] Cache de embeddings em memória
- [ ] Validação de inputs
- [ ] Endpoint de upload de documentos

### Fase 3 - Avançado (Semanas 5-6)
- [ ] Re-ranking com cross-encoder
- [ ] Histórico de conversas
- [ ] Métricas básicas

### Fase 4 - Refinamento (Semanas 7-8)
- [ ] Testes automatizados
- [ ] Modo debug
- [ ] Sistema de feedback

---

*Última atualização: Novembro 2025*
