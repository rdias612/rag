# Implementação: Item 2 - Query Expansion / Reformulação

**Status:** ✅ IMPLEMENTADO  
**Data:** 29/12/2025  
**Prioridade:** 🔴 Alta (Maior Impacto na Qualidade)

---

## 📋 Descrição da Implementação

O **Query Expansion** (Expansão de Consulta) foi implementado para melhorar o recall da busca vetorial. O sistema agora gera automaticamente variações da pergunta do usuário usando o LLM antes de realizar a busca, o que ajuda a encontrar documentos relevantes que poderiam ser perdidos com uma única query.

---

## 🎯 Problema Solucionado

Perguntas curtas ou ambíguas podem não recuperar todos os chunks relevantes porque:
- O usuário usa termos diferentes dos presentes nos documentos
- A query não captura todas as formas que o conceito pode estar descrito
- Documentos técnicos usam terminologia específica que o usuário desconhece

**Exemplo:**
- Query do usuário: "O que é GWPRP?"
- Documentos podem conter: "Geographic Weighted Position Routing Protocol", "GWPRP protocol", "roteamento geográfico ponderado", etc.

---

## 🔧 Funcionalidades Implementadas

### 1. Geração de Variações de Query

**Arquivo:** `src/core/query_expansion.py`

**Função principal:** `expand_query(query, num_variations, temperature)`

```python
from src.core.query_expansion import expand_query

# Gerar 3 variações da query
variations = expand_query("O que é GWPRP?", num_variations=3)
# Retorna: ["O que é GWPRP?", "Explique o protocolo GWPRP", 
#           "Características do Geographic Weighted Position Routing Protocol"]
```

**Características:**
- Usa o LLM para gerar variações semanticamente relevantes
- Configuração de temperatura controla a diversidade das variações
- Parse inteligente remove numeração e marcadores
- Fallback seguro: retorna apenas query original em caso de erro

### 2. Fusão de Resultados com RRF

**Função:** `merge_search_results(results_list, top_k, k_constant)`

Implementa **Reciprocal Rank Fusion (RRF)** para combinar resultados de múltiplas buscas:

```python
from src.core.query_expansion import merge_search_results

# Fundir resultados de múltiplas buscas
merged = merge_search_results(
    results_list=[results_original, results_var1, results_var2],
    top_k=10,
    k_constant=60
)
```

**Como funciona o RRF:**
1. Para cada documento, calcula score: `1 / (k_constant + rank + 1)`
2. Soma os scores de cada variação
3. Ordena por score combinado
4. Documentos que aparecem em múltiplas buscas ganham boost

**Benefícios:**
- Documentos consistentemente relevantes são priorizados
- Reduz impacto de rankings ruins em buscas individuais
- Combina pontos fortes de diferentes variações

### 3. Integração com Pipeline RAG

**Arquivo:** `src/core/rag.py` - Função `_apply_phase2_pipeline()`

O Query Expansion está integrado ao pipeline principal:

```
Query Original
    ↓
[Query Expansion] → Gera N variações
    ↓
Busca com Variação 1 → Resultados A
Busca com Variação 2 → Resultados B
Busca com Variação N → Resultados N
    ↓
[RRF Merge] → Combina e ordena
    ↓
Resultados Finais
```

### 4. Configuração Centralizada

**Arquivo:** `src/config.py`

```python
# Habilitar Query Expansion
ENABLE_QUERY_EXPANSION: bool = True

# Número de variações a gerar
QUERY_EXPANSION_COUNT: int = 3
```

### 5. Prompt Customizável

**Database:** Tabela `prompts`

O prompt usado para gerar variações está no banco de dados, permitindo ajustes sem modificar código:

```sql
SELECT template FROM prompts WHERE name = 'query_expansion_prompt';
```

**Prompt atual:**
```
Você é um especialista em recuperação de informação e semântica técnica.
Dada a pergunta original do usuário, gere {num_variations} variações de busca que ajudem a encontrar documentos relevantes.

Regras:
1. Use sinônimos técnicos e termos relacionados para expandir o recall.
2. Reformule de forma a cobrir diferentes maneiras que um humano escreveria isso em um documento.
3. Mantenha a intenção original da busca.
4. Gere apenas uma variação por linha, sem numeração ou marcadores.

Pergunta original: "{query}"

Variações:
```

---

## 🚀 Como Usar

### Habilitar/Desabilitar

**Via arquivo de configuração:**
```python
# src/config.py
ENABLE_QUERY_EXPANSION = True  # Habilita
QUERY_EXPANSION_COUNT = 3     # Número de variações
```

**Via variável de ambiente (.env):**
```bash
ENABLE_QUERY_EXPANSION=True
QUERY_EXPANSION_COUNT=3
```

### Uso no Pipeline RAG

O Query Expansion é automático quando habilitado:

```python
from src.core.rag import query_rag

result = query_rag(
    question="O que é GWPRP?",
    top_k=10
)

# O sistema automaticamente:
# 1. Gera variações da query
# 2. Busca com cada variação
# 3. Funde resultados com RRF
# 4. Retorna os top_k melhores
```

### Uso Isolado

Para testar ou usar apenas a expansão:

```python
from src.core.query_expansion import expand_query

# Expandir query
variations = expand_query("Como funciona o GWPRP?", num_variations=5)

for i, var in enumerate(variations, 1):
    print(f"{i}. {var}")
```

---

## 📊 Métricas e Debug

### Informações de Debug

Quando `debug_mode=True` no `query_rag()`, informações detalhadas são incluídas:

```python
result = query_rag(
    question="O que é GWPRP?",
    debug_mode=True
)

debug_info = result.get("_debug", {})
print(debug_info)
```

**Contém:**
- `phase2.query_expanded`: Boolean indicando se expansion foi aplicado
- `phase2.query_variations`: Número de variações geradas
- `chunks_after_rerank`: Número de chunks após fusão

### Logs do Sistema

O sistema registra operações:

```python
from src.core.logger import rag_logger

# Logs são automaticamente gerados:
# - "Expanding query: '...' with N variations"
# - "Query expanded to N variations"
# - "RRF merged X results into Y"
```

---

## 🧪 Testes

**Arquivo:** `tests/test_query_expansion.py`

Testes automatizados para verificar funcionamento:

```bash
cd c:\GIT\rag
python tests/test_query_expansion.py
```

**Testes incluídos:**
1. ✅ Teste de expansão de query
   - Gera variações
   - Verifica qualidade das variações
   - Valida parsing da resposta LLM

2. ✅ Teste de fusão RRF
   - Mescla múltiplos conjuntos de resultados
   - Verifica ordenação por score
   - Confirma consolidação de duplicatas

---

## 📈 Benefícios Esperados

### Qualidade das Respostas

| Métrica | Impacto Esperado |
|---------|-----------------|
| Recall de busca | ⭐⭐⭐⭐⭐ (+20-40%) |
| Precisão das respostas | ⭐⭐⭐⭐ (+10-20%) |
| Cobertura de tópicos | ⭐⭐⭐⭐⭐ |
| Satisfação do usuário | ⭐⭐⭐⭐ |

### Cenários de Melhoria

1. **Perguntas curtas:** "O que é X?" → Encontra definições com termos variados
2. **Terminologia técnica:** Encontra sinônimos e termos relacionados
3. **Perguntas ambíguas:** Cobra múltiplas interpretações possíveis
4. **Documentos heterogêneos:** Adapta a diferentes estilos de escrita

---

## ⚙️ Configurações Recomendadas

### Produção (Padrão)
```python
ENABLE_QUERY_EXPANSION = True
QUERY_EXPANSION_COUNT = 3
```

### Alta Precisão
```python
ENABLE_QUERY_EXPANSION = True
QUERY_EXPANSION_COUNT = 5  # Mais variações, mais recall
```

### Baixa Latência
```python
ENABLE_QUERY_EXPANSION = False  # Desabilita
# ou
ENABLE_QUERY_EXPANSION = True
QUERY_EXPANSION_COUNT = 2  # Menos variações
```

---

## 🔍 Exemplo Prático

### Sem Query Expansion
```
Query: "O que é GWPRP?"

Resultados:
1. Documento A - "GWPRP é um protocolo..." (score: 0.85)
2. Documento B - "roteamento em redes..." (score: 0.72)
```

### Com Query Expansion
```
Query Original: "O que é GWPRP?"
Variação 1: "Explique o protocolo GWPRP"
Variação 2: "Características do Geographic Weighted Position Routing Protocol"
Variação 3: "Como funciona o roteamento geográfico ponderado"

Resultados (após RRF):
1. Documento A - "GWPRP é um protocolo..." (RRF: 0.033)
2. Documento C - "Geographic Weighted Position Routing Protocol..." (RRF: 0.028)
3. Documento D - "roteamento geográfico ponderado..." (RRF: 0.025)
4. Documento B - "roteamento em redes..." (RRF: 0.016)
```

**Observação:** Documentos C e D aparecem apenas com Query Expansion!

---

## 🔗 Integração com Outras Funcionalidades

O Query Expansion trabalha em conjunto com:

1. **Hybrid Search:** Usa variações em busca vetorial + FTS
2. **Re-ranking:** Aplica cross-encoder nos resultados expandidos
3. **MMR:** Remove redundância entre variações
4. **HyDE:** Pode ser combinado (primeiro expande, depois gera documento hipotético)

---

## 📝 Notas Importantes

### Trade-offs

**Prós:**
- ✅ Melhor recall de documentos
- ✅ Adaptação a diferentes terminologias
- ✅ Cobertura mais abrangente
- ✅ Implementação robusta com fallbacks

**Contras:**
- ⚠️ Aumenta latência (cada variação = uma busca extra)
- ⚠️ Maior uso de LLM (geração de variações)
- ⚠️ Pode introduzir ruído se variações forem muito diferentes

### Recomendações

1. **Monitorar latência:** Se >3s, reduzir `QUERY_EXPANSION_COUNT`
2. **Ajustar temperatura:** 0.7-0.9 para diversidade equilibrada
3. **Revisar prompt periodicamente:** Melhorar instruções de geração
4. **Usar com cache:** Ativar `EMBEDDING_CACHE_ENABLED` para reduzir custo

---

## 🎓 Referências Técnicas

- **Reciprocal Rank Fusion (RRF):** Cormack et al., 2009
- **Query Expansion:** Rocchio, 1971 (clássico) + adaptações modernas com LLM
- **Hybrid RAG:** Combinações de múltiplas estratégias de busca

---

## ✅ Checklist de Implementação

- [x] Implementar função `expand_query()`
- [x] Implementar função `merge_search_results()` com RRF
- [x] Integrar ao pipeline RAG em `_apply_phase2_pipeline()`
- [x] Configurar via `config.py`
- [x] Criar prompt no banco de dados
- [x] Adicionar métricas e logging
- [x] Criar testes automatizados
- [x] Documentação completa
- [x] Verificar fallbacks e tratamento de erros
- [x] Testar integração com outros módulos

---

## 🚀 Próximos Passos (Opcionais)

1. **A/B Testing:** Comparar qualidade com/sem expansion
2. **Adaptive Expansion:** Ajustar `QUERY_EXPANSION_COUNT` baseado na complexidade da query
3. **Caching de Variações:** Cache de variações para queries similares
4. **Feedback Loop:** Usar feedback do usuário para melhorar geração de variações

---

**Implementado por:** Cline  
**Revisado por:** [Aguardando revisão]  
**Status:** ✅ PRODUÇÃO READY
