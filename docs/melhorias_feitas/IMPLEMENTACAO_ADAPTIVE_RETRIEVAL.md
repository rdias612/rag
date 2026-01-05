# Implementação: Adaptive Retrieval

## Status
✅ **Implementado em 30/12/2025**

## Contexto
O Adaptive Retrieval foi implementado conforme item 2 da lista de melhorias (`docs/SUGESTOES_MELHORIAS.md`). Esta funcionalidade permite ajustar dinamicamente os parâmetros de busca (`top_k` e `min_similarity`) com base na complexidade da query do usuário.

## Visão Geral

**Problema Resolvido:** Busca fixa é ineficiente para queries simples (perde contexto) ou complexas (retorna ruído).

**Solução:** Análise dinâmica da query que:
- Detecta nível de complexidade (0-10)
- Ajusta `top_k` e `min_similarity` automaticamente
- Registra métricas para análise posterior

## Arquitetura

### 1. Componentes Backend

#### `src/core/adaptive_retrieval.py`
Função principal `get_adaptive_params()` que:
- Analisa a query (palavras, estrutura, terminologia técnica)
- Calcula score de complexidade (0-10)
- Ajusta parâmetros de busca

**Critérios de Complexidade:**
- **Simple (0-3)**: Queries curtas, diretas
  - Ação: Aumentar `top_k`, diminuir `min_similarity`
  - Razão: Buscar mais contexto para respostas simples
  
- **Medium (4-6)**: Queries moderadas
  - Ação: Usar valores padrão
  - Razão: Equilíbrio entre precisão e contexto
  
- **Complex (7-10)**: Queries longas, técnicas
  - Ação: Diminuir `top_k`, aumentar `min_similarity`
  - Razão: Focar nos documentos mais relevantes

### 2. Integração no Pipeline

#### `src/core/rag/pipeline.py`
- Fase 1.5: Aplica Adaptive Retrieval antes da busca
- Persiste métricas automaticamente após a query
- Retorna detalhes do ajuste na resposta API

### 3. Configuração

#### `src/config.py`
Novos parâmetros:

```python
# Limites de ajuste
MAX_TOP_K_ADAPTIVE = 20
MIN_TOP_K_ADAPTIVE = 3
MAX_MIN_SIMILARITY_ADAPTIVE = 0.9
MIN_MIN_SIMILARITY_ADAPTIVE = 0.3

# Logging
ADAPTIVE_RETRIEVAL_LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### 4. API Endpoints

#### Query com Adaptive
```
POST /api/query
{
  "question": "Como funciona o sistema?",
  "enable_adaptive": true  // Novo parâmetro
}
```

#### Métricas de Adaptive Retrieval
```
GET /api/metrics/adaptive-retrieval/stats?days=7
GET /api/metrics/adaptive-retrieval/recent?limit=50
GET /api/metrics/adaptive-retrieval/performance?days=7
```

### 5. Frontend

#### Toggle no Header
- Botão para habilitar/desabilitar Adaptive Retrieval
- Persistência em `localStorage`
- Estado compartilhado entre sessões

#### Admin Dashboard
Nova aba **"Adaptive Retrieval"** com:
- 4 cards de estatísticas
- Gráfico de distribuição de complexidade
- Tabela de queries recentes (últimas 50)
- Filtro por período (24h, 7 dias, 30 dias)

### 6. Métricas

#### Tabela `adaptive_retrieval_metrics`
```sql
- id
- session_id
- question
- complexity_score (0-10)
- word_count
- top_k_original
- top_k_adjusted
- min_similarity_original
- min_similarity_adjusted
- adjustment_reason
- characteristics (JSON)
- duration_ms
- created_at
```

## Casos de Uso

### Query Simples
```
Usuário: "O que é RAG?"

Adaptive Analysis:
- Palavras: 3
- Complexidade: 1/10
- Ajuste: top_k 5 → 15, min_similarity 0.7 → 0.4
- Razão: Buscar mais contexto para pergunta simples
```

### Query Média
```
Usuário: "Como funciona o sistema de busca vetorial?"

Adaptive Analysis:
- Palavras: 7
- Complexidade: 4/10
- Ajuste: top_k 5, min_similarity 0.7
- Razão: Usar valores padrão
```

### Query Complexa
```
Usuário: "Quero entender como configurar o sistema completo incluindo Query Expansion, HyDE, Re-ranking com Cross-Encoder, e como otimizar cada componente para performance em produção."

Adaptive Analysis:
- Palavras: 32
- Complexidade: 9/10
- Ajuste: top_k 10 → 5, min_similarity 0.5 → 0.75
- Razão: Focar nos documentos mais relevantes
```

## Benefícios

### 1. Melhoria de Qualidade
- Queries simples recebem mais contexto
- Queries complexas recebem respostas mais focadas
- Redução de "Eu não tenho informações"

### 2. Análise de Dados
- Entendimento do comportamento dos usuários
- Identificação de padrões de queries
- Ajuste fino dos parâmetros baseado em dados reais

### 3. Flexibilidade
- Usuário pode desabilitar se preferir
- Configuração via environment variables
- Logging configurável para diferentes ambientes

## Limites e Considerações

### Limites Configuráveis
Todos os limites são configuráveis em `src/config.py`:
- `MAX_TOP_K_ADAPTIVE`: Máximo de documentos retornados
- `MIN_TOP_K_ADAPTIVE`: Mínimo de documentos retornados
- `MAX_MIN_SIMILARITY_ADAPTIVE`: Similaridade máxima permitida
- `MIN_MIN_SIMILARITY_ADAPTIVE`: Similaridade mínima permitida

### Logging
Nível de log configurável via `ADAPTIVE_RETRIEVAL_LOG_LEVEL`:
- `DEBUG`: Detalhes completos da análise
- `INFO`: Resumo dos ajustes (padrão)
- `WARNING`: Apenas avisos
- `ERROR`: Apenas erros

## Testing

### Testes Unitários
Arquivo: `tests/test_adaptive_retrieval.py`

Cobertura:
- ✅ Cálculo de complexidade (25+ casos)
- ✅ Ajuste de parâmetros (10+ casos)
- ✅ Validação de limites (4 casos)
- ✅ Integração completa (5 casos)
- ✅ Casos de borda (4 casos)

Total: 48 testes automatizados

### Testes Manuais
1. ✅ Toggle UI funciona
2. ✅ Persistência em localStorage
3. ✅ Admin Dashboard exibe métricas
4. ✅ Filtro por período funciona
5. ⏳ Teste de regressão (ENABLE_ADAPTIVE_RETRIEVAL = False)

## Próximos Passos Opcionais

### Curto Prazo
- [ ] Executar teste de regressão completo
- [ ] Adicionar testes E2E com Cypress/Playwright
- [ ] Configurar CI/CD para rodar testes

### Médio Prazo
- [ ] A/B testing com/sem adaptive
- [ ] Machine Learning para ajustar limites automaticamente
- [ ] Integração com sistema de feedback do usuário

### Longo Prazo
- [ ] Personalização por usuário
- [ ] Adaptar parâmetros com base em histórico da sessão
- [ ] Multi-language support para análise de complexidade

## Troubleshooting

### Adaptive não está funcionando
1. Verificar `ENABLE_ADAPTIVE_RETRIEVAL=true` no `.env`
2. Verificar logs em nível `DEBUG`
3. Confirmar que `enable_adaptive=true` está sendo enviado na API

### Métricas não aparecem no Dashboard
1. Verificar se migration foi executada: `alembic upgrade head`
2. Confirmar que queries foram feitas com `enable_adaptive=true`
3. Verificar conexão com banco de dados

### Valores ajustados não respeitam limites
1. Verificar configuração em `src/config.py`
2. Confirmar que não há overrides em `.env`
3. Verificar logs para validação

## Referências

- Issue: Item 2 em `docs/SUGESTOES_MELHORIAS.md`
- Feature Branch: `rev2`
- Commits:
  - `feat: Implement Adaptive Retrieval com Toggle UI`
  - `feat: Add Adaptive Retrieval Metrics (Fase 3)`
  - `feat: Add Adaptive Retrieval Metrics to Admin Dashboard (Fase 4)`
  - `feat: Add tests for Adaptive Retrieval (Fase 5)`
  - `feat: Add documentation for Adaptive Retrieval (Fase 6)`

## Conclusão

O Adaptive Retrieval foi implementado com sucesso em 6 fases:
1. ✅ Backend Integration
2. ✅ Frontend Toggle
3. ✅ Métricas e Logging
4. ✅ Admin Dashboard
5. ✅ Testes
6. ✅ Documentação

A funcionalidade está pronta para uso em produção, com monitoramento e métricas para análise contínua.
