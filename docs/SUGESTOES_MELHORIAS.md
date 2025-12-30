# 🚀 Sugestões de Melhorias para o Sistema RAG

Este documento contém uma análise completa do sistema RAG e sugestões de melhorias para otimizar a qualidade do output, organizadas por área de impacto.

---

## 📊 Resumo da Análise

O sistema RAG atual já possui uma base sólida com:
- ✅ Busca híbrida (vetorial + FTS) com RRF fusion
- ✅ Compressão de contexto (LLM e heurística)
- ✅ Chunking semântico com spaCy
- ✅ Histórico de conversas
- ✅ Múltiplos formatos de documento

As sugestões abaixo focam em **melhorar a qualidade das respostas** além da troca de LLM/embeddings.

---

## 🔴 Alta Prioridade (Maior Impacto na Qualidade)

### 1. Re-ranking com Cross-Encoder

**Problema:** A busca vetorial pode retornar chunks que são semanticamente similares mas não necessariamente os mais relevantes para a pergunta específica.

**Solução:** Implementar uma etapa de re-ranking usando um modelo cross-encoder após a busca inicial.

```python
# Fluxo proposto:
Query → Busca Híbrida (Top 20) → Cross-Encoder Re-rank → Top 5 Finais
```

**Modelos recomendados:**
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (leve, rápido)
- `BAAI/bge-reranker-base` (melhor qualidade)

**Benefícios:**
- Aumento significativo na precisão (10-20% em métricas de relevância)
- Melhor ordenação dos chunks antes de enviar ao LLM
- Redução de ruído no contexto

---

### 3. Melhoria do Prompt Template

**Problema:** O prompt atual é genérico e pode ser otimizado para diferentes tipos de perguntas.

**Sugestões de melhoria:**

```python
# Prompt melhorado com Chain-of-Thought
RAG_PROMPT_TEMPLATE_ENHANCED = """Você é um assistente especializado. Analise o contexto cuidadosamente antes de responder.

[CONTEXTO]
{contexto}

[PERGUNTA]
{pergunta}

[INSTRUÇÕES]
1. Primeiro, identifique quais partes do contexto são relevantes para a pergunta.
2. Se a pergunta pedir comparação ou análise, organize a resposta de forma estruturada.
3. Cite informações específicas do contexto quando apropriado.
4. Se a resposta não estiver completamente no contexto, indique claramente o que está faltando.

[RESPOSTA]
"""
```

**Adicionar prompts especializados:**
- Prompt para perguntas comparativas
- Prompt para perguntas de definição
- Prompt para perguntas de listagem/enumeração

---

## 🟡 Média Prioridade

### 5. Parent-Child Chunking (Hierarchical RAG)

**Problema:** Chunks pequenos são bons para precisão de busca, mas podem perder contexto expandido.

**Solução:** Implementar estratégia de chunks hierárquicos:

```
Documento
├── Chunk Pai (grande, ~2000 chars) → Retornado ao LLM
│   ├── Chunk Filho 1 (pequeno, ~400 chars) → Usado na busca
│   ├── Chunk Filho 2 (pequeno, ~400 chars) → Usado na busca
│   └── Chunk Filho 3 (pequeno, ~400 chars) → Usado na busca
```

**Fluxo:**
1. Buscar usando chunks pequenos (maior precisão)
2. Recuperar chunk pai para contexto expandido
3. Enviar chunk pai ao LLM

---

### 7. Sentence Window Retrieval

**Problema:** A busca retorna chunks isolados que podem cortar contexto importante.

**Solução:** Ao recuperar um chunk, expandir com sentenças vizinhas.

```python
# Configuração sugerida:
- Indexar: sentenças individuais com embedding
- Recuperar: sentença + N sentenças antes/depois (janela)
- Enviar ao LLM: janela expandida
```

**Benefícios:**
- Menor índice vetorial (sentenças são menores)
- Contexto expandido para o LLM
- Maior precisão na busca

---

## 🟢 Otimizações Adicionais

### 9. Cache de Embeddings de Queries

**Problema:** Queries repetidas ou similares recalculam embeddings.

**Solução:** Implementar cache com hash da query normalizada.

```python
import hashlib
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_embedding(query_hash: str) -> list[float]:
    # Retorna embedding do cache se existir
    pass

def get_embedding_with_cache(query: str) -> list[float]:
    normalized = query.lower().strip()
    query_hash = hashlib.md5(normalized.encode()).hexdigest()
    return get_cached_embedding(query_hash)
```

---

### 10. Pré-processamento de Documentos Aprimorado

**Melhorias sugeridas para `ingestion.py`:**

| Área | Melhoria |
|------|----------|
| **OCR** | Adicionar suporte para PDFs escaneados usando `pytesseract` |
| **Tabelas** | Extração estruturada de tabelas com `tabula-py` ou `camelot` |
| **Imagens** | Extração de texto de imagens em documentos |
| **Estrutura** | Detectar headers/sections para enriquecer metadados |
| **Limpeza** | Remover cabeçalhos/rodapés repetidos de PDFs |

---

### 11. Detecção de Tipo de Pergunta

Classificar a pergunta para escolher estratégia de resposta:

```python
QUESTION_TYPES = {
    "definição": ["o que é", "defina", "explique"],
    "comparação": ["diferença entre", "compare", "versus"],
    "listagem": ["quais são", "liste", "enumere"],
    "procedimento": ["como fazer", "como funciona", "passos"],
    "factual": ["quando", "onde", "quem", "quanto"]
}

def detect_question_type(question: str) -> str:
    question_lower = question.lower()
    for q_type, keywords in QUESTION_TYPES.items():
        if any(kw in question_lower for kw in keywords):
            return q_type
    return "general"
```

**Uso:** Selecionar prompt template apropriado ou ajustar busca.

---

### 12. Self-RAG / Reflexão

**Conceito:** Após gerar resposta, verificar se ela está correta e completa.

```python
# Fluxo:
1. Gerar resposta inicial
2. LLM avalia: "A resposta está baseada no contexto? Há informações faltando?"
3. Se incompleta, buscar mais chunks e regenerar
```

---

### 13. Adaptive Retrieval

Ajustar `top_k` e `min_similarity` dinamicamente baseado na complexidade da query:

```python
def adaptive_retrieval_params(question: str) -> dict:
    word_count = len(question.split())
    
    if word_count < 5:  # Query curta
        return {"top_k": 10, "min_similarity": 0.6}
    elif word_count > 20:  # Query longa/detalhada
        return {"top_k": 3, "min_similarity": 0.4}
    else:
        return {"top_k": 5, "min_similarity": 0.5}
```

---

### 14. Avaliação de Qualidade (RAGAS)

**Problema:** Não há métricas objetivas para medir qualidade das respostas.

**Solução:** Implementar avaliação usando framework RAGAS:

| Métrica | Descrição |
|---------|-----------|
| **Faithfulness** | Resposta é fiel ao contexto? |
| **Answer Relevancy** | Resposta é relevante à pergunta? |
| **Context Precision** | Chunks recuperados são relevantes? |
| **Context Recall** | Todos chunks necessários foram recuperados? |

```bash
pip install ragas
```

---

### 15. Fallback Inteligente

Quando não encontrar resultados relevantes:

```python
def handle_no_results(question: str) -> str:
    # 1. Tentar busca mais ampla (min_similarity menor)
    results = search_with_lower_threshold(question)
    if results:
        return "Encontrei informações relacionadas, mas não específicas..."
    
    # 2. Sugerir perguntas alternativas
    suggestions = generate_related_questions(question)
    
    # 3. Indicar tópicos disponíveis
    available_topics = get_indexed_topics()
    
    return f"""Não encontrei informações sobre isso. 
    Você pode tentar perguntar sobre: {available_topics}
    Ou reformular a pergunta."""
```

---

## 📋 Priorização Sugerida

### Fase 1 - Quick Wins (1-2 semanas) (CONCLUÍDA)
1. ✅ Melhoria do Prompt Template
2. ✅ Cache de Embeddings
3. ✅ Detecção de Tipo de Pergunta
4. ✅ Fallback Inteligente

### Fase 2 - Melhorias Core (2-4 semanas)
5. ✅ Re-ranking com Cross-Encoder
6. ✅ Query Expansion
7. ✅ MMR para Diversidade
8. ✅ HyDE (Hypothetical Document Embeddings)

### Fase 3 - Avançado (1-2 meses)
9. ✅ Parent-Child Chunking
10. ✅ Contextual Chunking com Metadados
11. ✅ Avaliação RAGAS

---

## 📈 Impacto Esperado

| Melhoria | Impacto na Qualidade |
|----------|---------------------|
| Re-ranking | ⭐⭐⭐⭐⭐ |
| Prompt Melhorado | ⭐⭐⭐⭐ |
| Query Expansion | ⭐⭐⭐⭐ |
| Parent-Child Chunking | ⭐⭐⭐⭐ |
| HyDE | ⭐⭐⭐ |
| MMR | ⭐⭐⭐ |
| Contextual Metadata | ⭐⭐⭐ |
| Cache | ⭐⭐ (performance) |

---

## 🔧 Ajustes de Configuração Sugeridos

Considerar ajustar em `config.py`:

```python
# Aumentar chunks recuperados para ter margem para re-ranking
TOP_K_RESULTS = 10  # Recuperar mais, filtrar depois

# Ajustar threshold para ser menos restritivo
MIN_SIMILARITY_THRESHOLD = 0.4  # Deixar re-ranker filtrar

# Chunk size menor para maior precisão de busca
CHUNK_SIZE = 500
MIN_CHUNK_SIZE = 150

# Aumentar overlap para manter contexto
CHUNK_OVERLAP_SENTENCES = 2
```

---

*Documento gerado em: Dezembro 2025*
*Baseado na análise do projeto RAG*
