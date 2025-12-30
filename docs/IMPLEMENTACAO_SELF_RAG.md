# 🔄 Implementação do Self-RAG / Reflexão

**Autor:** Cline  
**Data:** 30/12/2025  
**Prioridade:** Alta  
**Status:** 📝 Planejado

---

## 📋 Visão Geral

Este documento descreve o plano completo para implementar o sistema **Self-RAG** (Retrieval-Augmented Generation com Reflexão) no projeto RAG existente.

**Objetivo:** Melhorar a qualidade das respostas do LLM através de um loop de reflexão que avalia e refina respostas incompletas.

**Arquitetura Decidida:**
- ✅ Usar Query Expansion para buscar contexto adicional
- ✅ Configurar número de iterações via `.env`
- ✅ Aplicar Self-RAG em `/api/query` e `/api/chat`
- ✅ Não implementar em `/api/query/stream` (conflito de conceitos)

---

## 🎯 Decisões Arquiteturais

### 1. Busca de Contexto Adicional
**Escolha:** Usar Query Expansion automaticamente

**Motivo:**
- Reutiliza código existente e configurado
- Consistente com o resto do sistema
- Evita duplicação de lógica

### 2. Número de Iterações
**Escolha:** Configuração global no `.env`

**Motivo:**
- Simples de usar e configurar
- Performance previsível
- Facilita A/B Testing

### 3. Endpoints
**Escolha:** Aplicar em `/api/query` e `/api/chat`

**Motivo:**
- Consistência de qualidade
- UX completa
- Latência justificável pelo ganho de qualidade

### 4. Streaming
**Escolha:** Não implementar em `/api/query/stream`

**Motivo:**
- Conflito fundamental: Self-RAG precisa avaliar resposta completa antes de streaming
- Endpoint não está sendo usado pelo frontend
- Complexidade alta sem benefício claro

---

## 📁 Arquivos a Modificar

### 1. **`src/config.py`**
- Adicionar configuração `SELF_RAG_MAX_ITERATIONS`
- Adicionar configuração `SELF_RAG_ENABLED` (opcional, já existe `ENABLE_SELF_RAG`)

### 2. **`.env.example`**
- Adicionar parâmetros de Self-RAG ao arquivo de exemplo

### 3. **`src/core/rag/pipeline.py`**
- Integrar `self_rag_pipeline()` no método `RAGPipeline.query()`
- Integrar em `RAGPipeline.query_with_history()`
- Retornar métricas de Self-RAG na resposta

### 4. **`src/api/schemas.py`**
- Adicionar campos opcionais para Self-RAG (se necessário)

### 5. **`src/core/self_rag.py`**
- Revisar e aprimorar prompts se necessário
- Garantir integração correta com `query_expansion.py`

---

## 🔧 Plano de Implementação

### Passo 1: Atualizar Configurações

#### 1.1 Adicionar parâmetros em `src/config.py`

```python
# Self-RAG Configuration
SELF_RAG_MAX_ITERATIONS: int = Field(default=1, validation_alias="SELF_RAG_MAX_ITERATIONS")
```

#### 1.2 Adicionar ao `.env.example`

```bash
# Self-RAG Configuration
ENABLE_SELF_RAG=False
SELF_RAG_MIN_SCORE=60
SELF_RAG_MAX_ITERATIONS=1
```

---

### Passo 2: Integrar Self-RAG no Pipeline RAG

#### 2.1 Modificar `src/core/rag/pipeline.py`

Importar Self-RAG:
```python
from src.core.self_rag import self_rag_pipeline, check_self_rag_available
from src.config import ENABLE_SELF_RAG, SELF_RAG_MIN_SCORE, SELF_RAG_MAX_ITERATIONS
```

No método `RAGPipeline.query()`, após gerar a resposta:

```python
# 7. Gerar resposta
with LatencyTracker("llm"):
    answer = generate_response(prompt, temperature=temperature)

# 7.5. Self-RAG - Avaliar e refinar se habilitado
self_rag_metrics = {}
if ENABLE_SELF_RAG:
    with LatencyTracker("self_rag"):
        # Função de busca adicional usando Query Expansion
        def additional_search(query: str, top_k: int):
            from src.core.query_expansion import expand_query
            expanded_queries = expand_query(query)
            results = []
            for eq in expanded_queries[:2]:  # Limitar para não demorar muito
                eq_embedding = get_embedding(eq)
                results.extend(
                    self.search.search(
                        question=eq,
                        query_embedding=eq_embedding,
                        top_k=top_k,
                        use_hybrid=use_hybrid_search,
                        hybrid_alpha=hybrid_alpha,
                        collection_id=collection_id
                    )
                )
            return results[:top_k]
        
        # Aplicar Self-RAG
        answer, self_rag_metrics = self_rag_pipeline(
            question=question,
            answer=answer,
            context=raw_context,
            search_function=additional_search,
            min_score=SELF_RAG_MIN_SCORE,
            max_iterations=SELF_RAG_MAX_ITERATIONS
        )

# 8. Formatar resposta
return self.responses.format_response(
    answer=answer,
    documents=documents if include_sources else [],
    question_type=question_type,
    was_compressed=context_result["was_compressed"],
    search_metrics=search_metrics,
    self_rag_metrics=self_rag_metrics,  # Adicionar métricas
    duration=time.time() - start_time
)
```

#### 2.2 Modificar método `format_response()` em `src/core/rag/services/response_service.py`

Adicionar parâmetro `self_rag_metrics` e incluir na resposta:

```python
def format_response(
    self,
    answer: str,
    documents: list,
    question_type: str,
    was_compressed: bool,
    search_metrics: dict,
    self_rag_metrics: dict = None,
    duration: float = 0.0
) -> dict:
    
    # ... código existente ...
    
    result = {
        "answer": answer,
        "question_type": question_type,
        "sources": sources,
        "search": search_metrics,
        "duration": duration,
        "was_compressed": was_compressed
    }
    
    # Adicionar métricas de Self-RAG se disponíveis
    if self_rag_metrics:
        result["self_rag"] = self_rag_metrics
    
    return result
```

#### 2.3 Aplicar mesmo padrão em `query_with_history()`

O método `query_with_history()` já chama `query()` internamente, então receberá automaticamente as métricas de Self-RAG.

---

### Passo 3: Atualizar Schemas (Opcional)

#### 3.1 Revisar `src/api/schemas.py`

Os schemas atuais são suficientes, mas podemos adicionar campo opcional para permitir override:

```python
class QueryRequest(BaseModel):
    # ... campos existentes ...
    
    # Self-RAG options (opcional, usa config padrão se não fornecido)
    enable_self_rag: Optional[bool] = Field(default=None, description="Override Self-RAG setting")
    self_rag_min_score: Optional[int] = Field(default=None, ge=0, le=100, description="Override min score")
```

**Nota:** Isso é opcional. Se preferir simplificar, podemos manter apenas as configurações globais.

---

### Passo 4: Testes e Validação

#### 4.1 Testes Unitários

Criar `tests/test_self_rag.py`:

```python
import pytest
from src.core.self_rag import evaluate_response, refine_response

def test_evaluate_response():
    """Testa avaliação de resposta."""
    question = "Qual é a capital do Brasil?"
    answer = "A capital do Brasil é Brasília."
    context = "Brasília é a capital federal do Brasil, fundada em 1960."
    
    result = evaluate_response(question, answer, context)
    
    assert "score" in result
    assert "is_complete" in result
    assert 0 <= result["score"] <= 100
    assert isinstance(result["is_complete"], bool)

def test_refine_response():
    """Testa refinamento de resposta."""
    question = "Quem foi o primeiro presidente dos EUA?"
    previous_answer = "George Washington"
    reason = "Falta informação sobre o período"
    additional_context = "George Washington foi presidente de 1789 a 1797."
    
    refined = refine_response(question, previous_answer, reason, additional_context)
    
    assert len(refined) > len(previous_answer)
    assert "1789" in refined or "1797" in refined
```

#### 4.2 Testes de Integração

Criar script de teste manual:

```python
# tests/manual_test_self_rag.py
from src.core.rag import query_rag
from src.config import ENABLE_SELF_RAG, SELF_RAG_MAX_ITERATIONS

# Testar com Self-RAG habilitado
print(f"Self-RAG enabled: {ENABLE_SELF_RAG}")
print(f"Max iterations: {SELF_RAG_MAX_ITERATIONS}")

question = "Quais são os benefícios do uso de RAG?"
result = query_rag(question)

print("\n=== RESPOSTA ===")
print(result["answer"])

if "self_rag" in result:
    print("\n=== MÉTRICAS SELF-RAG ===")
    print(f"Iterações: {result['self_rag']['iterations']}")
    print(f"Score inicial: {result['self_rag']['initial_score']}")
    print(f"Score final: {result['self_rag']['final_score']}")
    print(f"Refinado: {result['self_rag']['was_refined']}")
```

---

### Passo 5: Atualizar Documentação

#### 5.1 Atualizar `docs/SUGESTOES_MELHORIAS.md`

Marcar Self-RAG como implementado:

```markdown
## ✅ Implementado (Dezembro 2025)

### 1. Self-RAG / Reflexão ✅
- Implementado loop de reflexão com avaliação e refinamento
- Configurações: `ENABLE_SELF_RAG`, `SELF_RAG_MIN_SCORE`, `SELF_RAG_MAX_ITERATIONS`
- Integração com Query Expansion para contexto adicional
- Métricas retornadas na resposta da API
```

#### 5.2 Criar `docs/SELF_RAG_GUIDE.md`

Documento explicando como usar Self-RAG:

```markdown
# Guia de Uso - Self-RAG

## O que é Self-RAG?
Sistema de reflexão que avalia respostas e refina automaticamente quando necessário.

## Como Habilitar
1. No arquivo `.env`:
```bash
ENABLE_SELF_RAG=True
SELF_RAG_MIN_SCORE=60
SELF_RAG_MAX_ITERATIONS=1
```

## Configurações
- `ENABLE_SELF_RAG`: Habilita/desabilita o sistema (default: False)
- `SELF_RAG_MIN_SCORE`: Score mínimo para considerar resposta completa (0-100)
- `SELF_RAG_MAX_ITERATIONS`: Máximo de refinamentos por query (default: 1)

## Como Funciona
1. Gera resposta inicial
2. Avalia qualidade (0-100)
3. Se score < min_score OU incompleta:
   - Busca contexto adicional (Query Expansion)
   - Refina resposta com novo contexto
4. Retorna resposta final com métricas

## Métricas Retornadas
```json
{
  "self_rag": {
    "iterations": 2,
    "initial_score": 45,
    "final_score": 85,
    "was_refined": true,
    "total_time_ms": 1234
  }
}
```
```

---

## 📊 Checklist de Implementação

### Configurações
- [ ] Adicionar `SELF_RAG_MAX_ITERATIONS` em `src/config.py`
- [ ] Adicionar parâmetros Self-RAG em `.env.example`

### Código Core
- [ ] Importar Self-RAG em `src/core/rag/pipeline.py`
- [ ] Implementar função de busca adicional com Query Expansion
- [ ] Integrar `self_rag_pipeline()` em `RAGPipeline.query()`
- [ ] Adicionar métricas de Self-RAG na resposta
- [ ] Atualizar `format_response()` para incluir `self_rag_metrics`
- [ ] Validar funcionamento em `query_with_history()`

### Testes
- [ ] Criar testes unitários em `tests/test_self_rag.py`
- [ ] Criar script de teste manual
- [ ] Testar com `ENABLE_SELF_RAG=True`
- [ ] Testar com diferentes valores de `SELF_RAG_MIN_SCORE`
- [ ] Testar com diferentes valores de `SELF_RAG_MAX_ITERATIONS`

### Documentação
- [ ] Atualizar `docs/SUGESTOES_MELHORIAS.md`
- [ ] Criar `docs/SELF_RAG_GUIDE.md`
- [ ] Documentar novo endpoint behavior
- [ ] Adicionar exemplos de uso

---

## 🚀 Roteiro de Execução

### Fase 1: Preparação (15 min)
1. Atualizar `src/config.py`
2. Atualizar `.env.example`
3. Commit: "feat: add Self-RAG configuration"

### Fase 2: Integração (45 min)
4. Modificar `src/core/rag/pipeline.py`
5. Atualizar `src/core/rag/services/response_service.py`
6. Testes locais básicos
7. Commit: "feat: integrate Self-RAG into RAG pipeline"

### Fase 3: Testes (30 min)
8. Criar testes unitários
9. Criar script de teste manual
10. Validar cenários
11. Commit: "test: add Self-RAG tests"

### Fase 4: Documentação (20 min)
12. Atualizar documentação existente
13. Criar guia de uso
14. Commit: "docs: add Self-RAG documentation"

**Tempo total estimado:** ~2 horas

---

## ⚠️ Considerações Importantes

### Performance
- Self-RAG adiciona latência (~1-3 segundos por iteração)
- Query Expansion adicional também adiciona custo
- Monitorar métricas de latência após implementação

### Comportamento Esperado
- Respostas de baixa qualidade serão refinadas automaticamente
- Respostas completas não sofrem impacto (avaliação rápida)
- Métricas permitem monitorar eficácia do sistema

### Troubleshooting
- Se muitas respostas estão sendo refinadas, aumentar `SELF_RAG_MIN_SCORE`
- Se latência está muito alta, reduzir `SELF_RAG_MAX_ITERATIONS`
- Se refinamento não melhora qualidade, revisar prompts em `self_rag.py`

---

## 📈 Métricas de Sucesso

### Qualitativas
- [ ] Respostas mais completas e informativas
- [ ] Menos respostas vagas ou incompletas
- [ ] Feedback positivo dos usuários

### Quantitativas
- [ ] Taxa de refinamento: 20-40% das queries (não 100%)
- [ ] Score médio final > Score médio inicial
- [ ] Latência adicional aceitável (<3 segundos)

---

## 🎓 Referências

- Self-RAG Paper: [https://arxiv.org/abs/2310.11511](https://arxiv.org/abs/2310.11511)
- Código Self-RAG atual: `src/core/self_rag.py`
- Pipeline RAG: `src/core/rag/pipeline.py`
