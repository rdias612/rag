# Sistema de Avaliação de Qualidade RAG

## 📋 Visão Geral

O Sistema de Avaliação de Qualidade RAG permite medir e monitorar a qualidade das respostas geradas pelo sistema, fornecendo insights valiosos para melhorias contínuas.

### 🎯 Objetivos

- **Avaliação Automática**: Medir qualidade de cada resposta automaticamente
- **Avaliação Manual**: Permitir que usuários avaliem respostas sob demanda
- **Dashboard Administrativo**: Visualizar métricas agregadas e tendências
- **Múltiplas Métricas**: Avaliar diferentes aspectos da qualidade (fidelidade, relevância, precisão)

---

## 🏗️ Arquitetura da Implementação

### Backend

#### 1. Infraestrutura de Dados

**Migration**: `alembic/versions/20251231_02_add_rag_evaluations_table.py`

Nova tabela `rag_evaluations` com os campos:
- `id`: Identificador único
- `question`: Pergunta original do usuário
- `answer`: Resposta gerada pelo LLM
- `context`: Contexto usado para gerar a resposta
- `faithfulness` (FLOAT): Fidelidade da resposta ao contexto (0-1)
- `answer_relevancy` (FLOAT): Relevância da resposta para a pergunta (0-1)
- `context_precision` (FLOAT): Precisão do contexto recuperado (0-1)
- `overall_score` (FLOAT): Score geral agregado (0-1)
- `evaluation_summary` (TEXT): Resumo textual da avaliação
- `session_id` (UUID): Sessão associada (opcional)
- `user_id` (UUID): Usuário associado (opcional)
- `chunks_retrieved` (INT): Número de chunks recuperados
- `search_mode` (VARCHAR): Modo de busca usado
- `adaptive_used` (BOOLEAN): Se adaptive retrieval foi usado
- `created_at` (TIMESTAMP): Data da avaliação

**Repository**: `src/data/repositories/evaluation_repository.py`

Implementa o padrão Repository Pattern com os métodos:
- `save_evaluation()`: Salva uma avaliação no banco
- `get_stats()`: Retorna estatísticas agregadas (médias, min, max, mediana)
- `get_trends()`: Retorna tendência temporal (diária ou semanal)
- `get_recent_evaluations()`: Lista avaliações recentes com filtros
- `get_top_worst_queries() Retorna as melhores e piores queries
- `delete_old_evaluations()`: Remove avaliações antigas
- `count()`: Conta total de avaliações

#### 2. Módulo de Avaliação

**Arquivo**: `src/core/evaluation.py` (Já existente)

Funções principais de avaliação:
- `evaluate_rag_response()`: Avalia resposta completa com múltiplas métricas
  - `Faithfulness`: Verifica se a resposta é fiel ao contexto
  - `Answer Relevancy`: Avalia se a resposta é relevante para a pergunta
  - `Context Precision`: Analisa a precisão do contexto recuperado
  - `Overall Score`: Métrica agregada (média das anteriores)
  - `Evaluation Summary`: Descrição textual da qualidade

#### 3. Integração com Pipeline RAG

**Modificado**: `src/core/rag/pipeline.py`

Integração da avaliação automática:
```python
# 7.5. Auto-avaliação (opcional)
if ENABLE_AUTO_EVALUATION:
    evaluation_result = evaluate_rag_response(
        question=question,
        answer=answer,
        context=raw_context,
        chunks=documents
    )
    
    # Filtra avaliações muito baixas
    if evaluation_result["overall_score"] >= EVALUATION_MIN_SCORE_THRESHOLD:
        # Salva no banco (assíncrono para não impactar performance)
        evaluation_repo.save_evaluation(
            question=question,
            answer=answer,
            context=raw_context,
            scores=evaluation_result,
            session_id=collection_id,
            chunks_retrieved=len(documents),
            search_mode=search_mode,
            adaptive_used=adaptive_metrics.get("applied", False)
        )
```

**Modificado**: `src/core/rag/services/response_service.py`

Adição de parâmetros na resposta:
```python
def format_response(
    self,
    answer: str,
    documents: list,
    question_type: str,
    was_compressed: bool = False,
    search_metrics: dict = None,
    self_rag_metrics: dict = None,
    adaptive_params_used: dict = None,
    evaluation_metrics: dict = None,  # NOVO
    duration: float = 0.0,
    **kwargs
) -> Dict[str, Any]:
```

As métricas de avaliação agora são retornadas na resposta da API quando `ENABLE_AUTO_EVALUATION=true`.

#### 4. API Endpoints

**Arquivo**: `src/api/routes/quality_metrics.py`

Endpoints implementados:

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/metrics/quality/stats` | GET | Estatísticas agregadas (médias, min, max, mediana) |
| `/api/metrics/quality/recent` | GET | Avaliações recentes com filtros |
| `/api/metrics/quality/trends` | GET | Tendência temporal de qualidade |
| `/api/metrics/quality/top-worst` | GET | Melhores e piores queries |
| `/api/metrics/quality/evaluate` | POST | Avaliar resposta sob demanda |

**Registro**: `src/api/routes/__init__.py`

```python
from src.api.routes.quality_metrics import quality_bp

api.register_blueprint(quality_bp, url_prefix="/metrics/quality")
```

### Frontend

#### 1. Dashboard Administrativo

**Arquivo**: `frontend/src/components/admin/QualityMetricsPanel.tsx`

Componente com visualização completa de métricas:
- **Cards de Estatísticas Gerais**:
  - Total de Avaliações
  - Score Médio
  - Fidelidade Média
  - Relevância Média

- **Métricas Detalhadas**:
  - Score Mínimo e Máximo
  - Mediana
  - Precisão do Contexto

- **Tendência Temporal**:
  - Tabela com evolução das métricas
  - Filtros: 7/30/90 dias
  - Agrupamento: Diário ou Semanal

- **Avaliações Recentes**:
  - Lista de avaliações com detalhes expansíveis
  - Clique para ver todas as métricas individuais
  - Resumo textual da avaliação

**Integração**: `frontend/src/components/AdminDashboard.tsx`

Nova aba "Qualidade RAG" adicionada ao dashboard:
- Ícone de prêmio (Award)
- Acessível via desktop e mobile
- Reutiliza estilos do AdaptiveRetrievalMetrics

#### 2. Modal de Avaliação no Chat

**Arquivo**: `frontend/src/components/EvaluationModal.tsx`

Modal visual para avaliação manual:
- **Display de Pergunta e Resposta**
- **Score Geral** com barra de progresso
- **3 Métricas Individuais**:
  - Fidelidade (Faithfulness)
  - Relevância (Answer Relevancy)
  - Precisão do Contexto (Context Precision)
- **Cores Dinâmicas**:
  - Verde (≥80%): Excelente
  - Amarelo (60-80%): Bom
  - Vermelho (<60%): Precisa melhorar
- **Resumo da Avaliação**: Descrição textual
- **Sugestões de Melhoria**: Quando score for baixo
- **Botão de Reavaliação**: Para testar novamente

**Modificado**: `frontend/src/components/MessageList.tsx`

Adição do botão de avaliação:
- Novo botão 🏆 junto com buttons de feedback
- Visível ao passar o mouse sobre mensagem do assistant
- Encontra automaticamente a pergunta do usuário correspondente
- Integração com EvaluationModal

**Modificado**: `frontend/src/types.ts`

Adição do campo `context` ao tipo `DebugInfo`:
```typescript
export interface DebugInfo {
    // ... campos existentes
    context?: string;  // NOVO
    // ... campos existentes
}
```

---

## ⚙️ Configurações

### Variáveis de Ambiente

```bash
# Habilita avaliação automática de respostas
ENABLE_AUTO_EVALUATION=false

# Habilita botão de avaliação manual no chat
ENABLE_EVALUATION_UI=true

# Threshold mínimo para salvar avaliações (0.0-1.0)
# Avaliações abaixo deste valor não são salvas
EVALUATION_MIN_SCORE_THRESHOLD=0.4
```

### Quando Usar Cada Modo

#### Auto-avaliação (ENABLE_AUTO_EVALUATION=true)
- **Vantagens**:
  - Métricas coletadas automaticamente
  - Cobertura total das respostas
  - Identificação de problemas em tempo real
- **Desvantagens**:
  - Custo adicional (uma chamada extra ao LLM)
  - Aumento de latência (~200-500ms)
- **Recomendado para**: Produção com baixo volume de queries

#### Avaliação Manual (ENABLE_EVALUATION_UI=true)
- **Vantagens**:
  - Custo zero por padrão (avaliação apenas sob demanda)
  - Usuário decide quando avaliar
  - Sem impacto na latência das queries
- **Desvantagens**:
  - Dependência da interação do usuário
  - Métricas parciais (apenas respostas avaliadas)
- **Recomendado para**: Desenvolvimento, testes, volume alto

#### Ambos Habilitados
- Combinação ideal para testes e feedback contínuo
- Avaliação automática coleta dados em background
- Botão manual permite que usuários revisem e avaliem

---

## 📊 Métricas Explicadas

### 1. Fidelidade (Faithfulness)

**Definição**: Mede o quanto a resposta é fiel ao contexto fornecido.

**Como é calculada**:
- Analisa se a resposta contradiz o contexto
- Verifica se afirmações não são suportadas pelo contexto
- Detecta alucinações (informações não presentes no contexto)

**Interpretação**:
- **≥80%**: Resposta é fiel ao contexto, sem contradições
- **60-80%**: Resposta é majoritariamente fiel, com pequenas imprecisões
- **<60%**: Resposta contém contradições ou informações não suportadas

### 2. Relevância (Answer Relevancy)

**Definição**: Mede o quanto a resposta é relevante para a pergunta feita.

**Como é calculada**:
- Analisa se a resposta aborda a pergunta
- Verifica se é uma resposta direta ou tangencial
- Avalia a completude da resposta

**Interpretação**:
- **≥80%**: Resposta diretamente relevante, aborda a pergunta completamente
- **60-80%**: Resposta relevante, mas pode melhorar em especificidade
- **<60%**: Resposta tangencial ou parcialmente irrelevante

### 3. Precisão do Contexto (Context Precision)

**Definição**: Mede a precisão do contexto recuperado para responder a pergunta.

**Como é calculada**:
- Analisa se os chunks recuperados são relevantes
- Verifica se há ruído ou informações desnecessárias
- Avalia a cobertura dos tópicos

**Interpretação**:
- **≥80%**: Contexto é preciso, com baixo ruído
- **60-80%**: Contexto é razoavelmente preciso
- **<60%**: Contexto contém muito ruído ou informações irrelevantes

### 4. Score Geral (Overall Score)

**Definição**: Métrica agregada de todas as anteriores.

**Como é calculada**:
```python
overall_score = (
    faithfulness * 0.4 +
    answer_relevancy * 0.3 +
    context_precision * 0.3
)
```

Pesos:
- Fidelidade: 40% (mais importante)
- Relevância: 30%
- Precisão: 30%

**Interpretação**:
- **≥80%**: Qualidade Excelente
- **60-80%**: Qualidade Boa
- **<60%**: Precisa melhorar

---

## 🚀 Como Usar

### Setup Inicial

1. **Aplicar Migration**:
   ```bash
   alembic upgrade head
   ```

2. **Configurar Variáveis de Ambiente**:
   ```bash
   # No arquivo .env
   ENABLE_AUTO_EVALUATION=false  # ou true
   ENABLE_EVALUATION_UI=true
   EVALUATION_MIN_SCORE_THRESHOLD=0.4
   ```

3. **Reiniciar Backend**:
   ```bash
   python run_app.py
   ```

### Dashboard Administrativo

1. Acesse o Admin Dashboard
2. Clique na aba "Qualidade RAG"
3. Visualize as métricas:
   - Cards de estatísticas gerais
   - Métricas detalhadas
   - Tendência temporal
   - Avaliações recentes

### Avaliação Manual no Chat

1. Faça uma pergunta no chat
2. Quando o assistente responder, passe o mouse sobre a resposta
3. Clique no botão 🏆 (Avaliar qualidade)
4. O modal abrirá com:
   - Pergunta e resposta exibidas
   - Botão "Avaliar Resposta"
5. Clique no botão para executar a avaliação
6. Visualize o resultado com todas as métricas

---

## 🔍 API Examples

### Obter Estatísticas

```bash
curl http://localhost:5000/api/metrics/quality/stats?days=7
```

Resposta:
```json
{
  "total_evaluations": 150,
  "avg_score": 0.72,
  "avg_faithfulness": 0.75,
  "avg_relevancy": 0.70,
  "avg_precision": 0.68,
  "min_score": 0.35,
  "max_score": 0.95,
  "median_score": 0.71
}
```

### Obter Avaliações Recentes

```bash
curl http://localhost:5000/api/metrics/quality/recent?limit=20&min_score=0.5
```

Resposta:
```json
{
  "evaluations": [
    {
      "id": 1,
      "question": "Como funciona o sistema?",
      "overall_score": 0.85,
      "faithfulness": 0.90,
      "answer_relevancy": 0.80,
      "context_precision": 0.85,
      "evaluation_summary": "Resposta fiel e relevante para a pergunta.",
      "created_at": "2025-12-31T14:30:00"
    }
  ]
}
```

### Obter Tendência

```bash
curl http://localhost:5000/api/metrics/quality/trends?days=30&group_by=day
```

Resposta:
```json
{
  "trends": [
    {
      "period": "2025-12-01",
      "evaluations_count": 50,
      "avg_score": 0.71,
      "avg_faithfulness": 0.74,
      "avg_relevancy": 0.69
    }
  ]
}
```

### Avaliar Resposta Sob Demanda

```bash
curl -X POST http://localhost:5000/api/metrics/quality/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Como funciona o sistema?",
    "answer": "O sistema RAG permite consulta...",
    "context": "O sistema é composto por...",
    "chunks": [...]
  }'
```

Resposta:
```json
{
  "faithfulness": 0.85,
  "answer_relevancy": 0.90,
  "context_precision": 0.75,
  "overall_score": 0.83,
  "evaluation_summary": "Resposta fiel ao contexto e relevante para a pergunta. O contexto recuperado é razoavelmente preciso."
}
```

---

## 📈 Melhorias Futuras

### Curto Prazo
- [ ] Adicionar gráficos visuais (linhas, barras) ao dashboard
- [ ] Implementar exportação de métricas (CSV, JSON)
- [ ] Adicionar alertas automáticos quando score cair abaixo de threshold
- [ ] Implementar testes unitários para evaluation.py

### Médio Prazo
- [ ] A/B testing de prompts baseado em métricas de qualidade
- [ ] Integração com Prometheus para métricas de qualidade
- [ ] Comparação de qualidade entre diferentes modos de busca
- [ ] Análise de causas de baixa qualidade (drill-down)

### Longo Prazo
- [ ] Sistema de recomendações automáticas para melhorar qualidade
- [ ] Machine learning para prever qualidade antes de gerar resposta
- [ ] Integração com feedback do usuário para calibrar métricas
- [ ] Dashboard avançado com correlações entre métricas

---

## 🐛 Troubleshooting

### Problema: Avaliação não está sendo salva

**Causa**: `ENABLE_AUTO_EVALUATION=false` ou score abaixo de threshold

**Solução**:
```bash
# Habilitar no .env
ENABLE_AUTO_EVALUATION=true

# Ajustar threshold se necessário
EVALUATION_MIN_SCORE_THRESHOLD=0.3  # mais permissivo
```

### Problema: Botão de avaliação não aparece no chat

**Causa**: `ENABLE_EVALUATION_UI=false`

**Solução**:
```bash
# Habilitar no .env
ENABLE_EVALUATION_UI=true
```

### Problema: Erro ao acessar endpoint de qualidade

**Causa**: Migration não aplicada

**Solução**:
```bash
alembic upgrade head
```

### Problema: Performance afetada

**Causa**: `ENABLE_AUTO_EVALUATION=true` aumenta latência

**Solução**:
```bash
# Desabilitar auto-avaliação em produção de alto volume
ENABLE_AUTO_EVALUATION=false
ENABLE_EVALUATION_UI=true  # Usar apenas avaliação manual
```

---

## 📚 Referências

- **RAGAS**: Framework de avaliação para sistemas RAG
- **TruLens**: Ferramenta de avaliação para aplicações LLM
- **DeepEval**: Biblioteca para avaliação de qualidade de respostas
- **LangSmith**: Plataforma de observabilidade para LLMs

---

## ✅ Checklist de Implementação

- [x] Migration criada
- [x] Repository implementado
- [x] Integração com pipeline RAG
- [x] API endpoints implementados
- [x] Dashboard administrativo criado
- [x] Modal de avaliação no chat criado
- [x] Configurações documentadas
- [ ] Testes unitários criados
- [ ] Documentação no README atualizada
- [ ] Performance testado

---

**Versão**: 1.0
**Data**: 31/12/2025
