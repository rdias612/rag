# Implementação do Sistema de Chunking Type

## 📋 Resumo

Esta implementação adiciona suporte para registrar e filtrar documentos por tipo de chunking (hierarchical ou sentence), permitindo que o frontend controle qual estratégia usar nas buscas.

## 🎯 Problema Original

Antes desta implementação:
- A informação de tipo de chunking estava apenas no metadata de cada chunk
- Não era possível saber em nível de documento qual tipo foi usado
- Não existia filtragem eficiente por tipo de chunking nas buscas

## ✅ Solução Implementada

### 1. Banco de Dados

**Migration criada:** `20260102_01_add_chunking_type_to_ingestion.py`

- Campo `chunking_type` adicionado à tabela `documentos_ingeridos`
- Valores: `hierarchical`, `sentence`, ou `NULL` (legado)
- Índices otimizados para consultas por tipo
- Migração automática de dados existentes (inferidos do metadata)

### 2. Novo Repositório

**Arquivo:** `src/data/repositories/ingestion_repository.py`

Métodos principais:
- `find_by_path()` - Verifica se documento foi ingerido
- `create()` - Registra novo documento com tipo de chunking
- `update()` - Atualiza documento existente
- `create_or_update()` - Registra ou atualiza (upsert)
- `find_by_chunking_type()` - Lista documentos por tipo
- `count_by_chunking_type()` - Conta documentos por tipo
- `get_stats()` - Estatísticas por coleção

### 3. Repositório Atualizado

**Arquivo:** `src/data/repositories/document_repository.py`

Novo método:
- `find_similar_by_chunking_type()` - Busca filtrando por tipo de chunking
  - Usa `IngestionRepository` para identificar documentos com o tipo
  - Busca apenas nesses documentos (otimização)
  - Filtra por tipo no metadata ('child' para hierarchical, 'sentence' para sentence)

### 4. Script de Ingestão Atualizado

**Arquivo:** `scripts/ingest.py`

Novos recursos:
- Parâmetro `--chunking-type`: Escolhe tipo de chunking
  - `--chunking-type hierarchical` (padrão)
  - `--chunking-type sentence`
- Usa `IngestionRepository` para registrar tipo
- Usa `DocumentRepository` para inserir chunks
- Mostra tipo na listagem de documentos ingeridos

**Uso:**
```bash
# Ingestão com hierarchical (padrão)
python -m scripts.ingest

# Ingestão com sentence window
python -m scripts.ingest --chunking-type sentence

# Forçar re-ingestão com sentence
python -m scripts.ingest --force --chunking-type sentence

# Listar documentos (mostra tipo)
python -m scripts.ingest --list-ingested
```

### 5. Busca e RAG Atualizados

**Arquivo:** `src/core/rag/services/search_service.py`

Atualizações:
- Método `search()` agora aceita parâmetro `chunking_type`
  - Se `chunking_type` fornecido: busca otimizada usando tabela documentos_ingeridos
  - Se `None`: busca normal em todos os documentos
- Método `search_with_sentence_window()` atualizado para usar `DocumentRepository`
- Usa filtro de chunking_type no metadata

**Arquivo:** `src/core/rag/pipeline.py`

Já tinha suporte a `search_mode`:
- `search_mode="auto"`: Sistema decide baseado na pergunta
- `search_mode="hierarchical"`: Busca apenas em documentos hierarchical
- `search_mode="sentence"`: Busca apenas em documentos sentence

### 6. API Frontend

**Schema já atualizado em:** `src/api/schemas.py`

Parâmetro disponível em todos os endpoints:
- `QueryRequest.search_mode`
- `ChatRequest.search_mode`
- `StreamQueryRequest.search_mode`

**Exemplo de requisição:**
```json
{
  "question": "Qual é o valor do projeto?",
  "top_k": 5,
  "search_mode": "sentence",
  "collection": "projeto_A"
}
```

## 🔄 Como Funciona

### Ingestão

1. Usuário executa: `python -m scripts.ingest --chunking-type sentence`
2. Script processa documentos usando `process_document_with_chunking_type(doc_path, "sentence")`
3. Chunks são gerados com `metadata["chunk_type"] = "sentence"`
4. Chunks são inseridos na tabela `documentos`
5. Documento é registrado em `documentos_ingeridos` com `chunking_type = "sentence"`

### Busca

1. Frontend envia requisição com `search_mode="sentence"`
2. Pipeline RAG determina estratégia baseada no search_mode
3. SearchService busca documentos:
   - Se `search_mode="sentence"`: Usa `find_similar_by_chunking_type("sentence")`
   - Se `search_mode="hierarchical"`: Usa `find_similar_by_chunking_type("hierarchical")`
   - Se `search_mode="auto"`: Sistema decide (heurística da pergunta)
4. IngestionRepository retorna lista de `source_paths` com esse tipo
5. DocumentRepository busca apenas nesses documentos
6. Resultados são retornados ao usuário

## 📊 Modo Auto (Heurística)

Quando `search_mode="auto"`, o sistema decide automaticamente:

**Indicadores de Sentence Window (respostas diretas):**
- Perguntas com ≤ 5 palavras
- Perguntas com: "qual é", "o que é", "quanto custa", "onde fica", "quem é"
- Perguntas com: "qual", "quanto", "onde", "quem"

**Indicadores de Hierarchical (explicações detalhadas):**
- Perguntas com: "como funciona", "por que", "porque", "como fazer"
- Perguntas com: "explique", "detalhe", "descreva", "o processo de"
- Perguntas começando com "como"

**Padrão:** Hierarchical (mais seguro)

## 🧪 Testes Recomendados

### Teste 1: Ingestão Hierarchical
```bash
# Limpar banco (opcional)
python -m scripts.ingest --clear

# Ingerir com hierarchical
python -m scripts.ingest --chunking-type hierarchical

# Verificar documentos
python -m scripts.ingest --list-ingested
```

### Teste 2: Ingestão Sentence
```bash
# Limpar banco (opcional)
python -m scripts.ingest --clear

# Ingerir com sentence
python -m scripts.ingest --chunking-type sentence

# Verificar documentos
python -m scripts.ingest --list-ingested
```

### Teste 3: Busca Hierarchical
```bash
# Usando curl
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Como funciona o processo de aprovação?",
    "search_mode": "hierarchical",
    "top_k": 5
  }'
```

### Teste 4: Busca Sentence
```bash
# Usando curl
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o valor do projeto?",
    "search_mode": "sentence",
    "top_k": 5
  }'
```

### Teste 5: Busca Auto
```bash
# Usando curl
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é o processo?",
    "search_mode": "auto",
    "top_k": 5
  }'
```

## 🔍 Verificação no Banco de Dados

```sql
-- Verificar chunking_type dos documentos
SELECT 
    chunking_type,
    COUNT(*) as count
FROM documentos_ingeridos
GROUP BY chunking_type;

-- Verificar documentos de cada tipo
SELECT 
    di.chunking_type,
    d.metadata->>'chunk_type' as metadata_chunk_type,
    COUNT(*) as count
FROM documentos_ingeridos di
JOIN documentos d ON d.metadata->>'source_path' = di.file_path
GROUP BY di.chunking_type, d.metadata->>'chunk_type';

-- Buscar documentos sentence
SELECT d.metadata->>'chunk_type', COUNT(*)
FROM documentos d
WHERE d.metadata->>'source_path' IN (
    SELECT file_path FROM documentos_ingeridos WHERE chunking_type = 'sentence'
)
GROUP BY d.metadata->>'chunk_type';
```

## 🎓 Boas Práticas

### Para Ingestão
- **Consistência:** Use o mesmo chunking_type para todos os documentos de uma coleção
- **Documentação:** Documente quais coleções usam cada tipo
- **Teste:** Teste ambos os tipos antes de escolher um definitivo

### Para Busca
- **Frontend:** Deixe usuário escolher o modo quando apropriado
- **Auto vs Específico:** Use `auto` para usuário final, específico para casos de uso
- **Feedback:** Colete feedback sobre qualidade de respostas em cada modo

## 📝 Considerações Futuras

### Possíveis Melhorias
1. **Migração de dados existentes:** Script para migrar documentos ingeridos sem tipo
2. **Análise de uso:** Logs de qual modo é mais usado
3. **Recomendação automática:** Sistema sugerir melhor tipo baseado em uso
4. **Misto:** Permitir coleção ter documentos de ambos os tipos

### Performance
- Índices criados para consultas rápidas
- Busca otimizada usando IN clause para source_paths
- Considerar materialized view para estatísticas

## 🐛 Troubleshooting

### Erro: "Nenhum documento encontrado"
- **Causa:** Nenhum documento com o chunking_type solicitado
- **Solução:** Verifique com `--list-ingested` quais tipos existem
- **Solução:** Re-ingerir documentos com o tipo correto

### Erro: "Busca retorna resultados vazios"
- **Causa:** Filtro muito restritivo ou min_similarity alto
- **Solução:** Ajuste `top_k` ou `min_similarity`
- **Solução:** Use `search_mode="auto"` para buscar em todos

### Erro: "Embedding inválido"
- **Causa:** Problema com LM Studio ou modelo de embedding
- **Solução:** Verifique se LM Studio está rodando
- **Solução:** Verifique modelo correto (Nomic Embed)

## 📚 Referências

- **Ingestion:** `src/data/ingestion.py`
- **IngestionRepository:** `src/data/repositories/ingestion_repository.py`
- **DocumentRepository:** `src/data/repositories/document_repository.py`
- **SearchService:** `src/core/rag/services/search_service.py`
- **RAG Pipeline:** `src/core/rag/pipeline.py`
- **API Schemas:** `src/api/schemas.py`
- **Ingest Script:** `scripts/ingest.py`

---

**Implementado em:** 2026-01-02
**Status:** ✅ Completo e pronto para uso
