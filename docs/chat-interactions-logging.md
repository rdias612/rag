# Chat Interactions Logging - Plano de Implementação

## Visão Geral

Adicionar persistência de todas as interações de chat no banco de dados para análise aprofundada, identificação de cenários problemáticos e suporte ao aprendizado contínuo do sistema RAG.

## Objetivos

1. **Persistência**: Armazenar permanentemente todas as interações usuário-LLM
2. **Rastreabilidade**: Manter histórico completo do processo RAG (retrieval + generation)
3. **Análise**: Permitir identificação de padrões, problemas e oportunidades de melhoria
4. **Auditoria**: Rastreabilidade completa para compliance e debugging
5. **Aprendizado Contínuo**: Base de dados para avaliação e feedback

## Arquitetura Proposta

### Nova Tabela: `chat_interactions`

```sql
CREATE TABLE chat_interactions (
    -- Identificação
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_index INT NOT NULL,
    interaction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Input do Usuário
    user_question TEXT NOT NULL,
    user_metadata JSONB,  -- Ex: IP, user agent, etc.
    
    -- Fase de Retrieval
    retrieval_method VARCHAR(50),  -- 'hybrid', 'semantic', 'bm25'
    collection_id VARCHAR(255),
    top_k INT,
    retrieved_chunks JSONB,  -- Array com IDs, scores, e conteúdo dos chunks
    retrieval_score_avg FLOAT,
    retrieval_time_ms INT,
    
    -- Contexto Construído
    context_used TEXT,  -- Contexto final que foi enviado para a LLM
    context_length INT,  -- Tamanho em caracteres
    
    -- Interação com LLM
    llm_model VARCHAR(100),  -- Nome do modelo usado
    llm_prompt TEXT,  -- Prompt completo enviado
    llm_prompt_tokens INT,
    llm_response TEXT,  -- Resposta completa da LLM
    llm_response_tokens INT,
    temperature FLOAT,
    llm_time_ms INT,
    
    -- Prompt Engineering
    prompt_template_id INT,  -- Referência ao prompt usado
    prompt_category VARCHAR(100),  -- Categoria do prompt selecionado
    
    -- Performance Total
    total_time_ms INT,
    
    -- Metadados Adicionais
    metadata JSONB,  -- Campo flexível para dados extras
    
    -- Quality Tracking (para futura implementação de feedback)
    user_feedback_rating INT,  -- 1-5 estrelas
    admin_feedback_rating INT,  -- Avaliação do admin
    feedback_comment TEXT,
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    
    -- Flags de Status
    has_error BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    error_type VARCHAR(100),
    
    -- Indexes
    CONSTRAINT unique_session_message UNIQUE (session_id, message_index),
    INDEX idx_session_id (session_id),
    INDEX idx_timestamp (interaction_timestamp),
    INDEX idx_collection (collection_id),
    INDEX idx_needs_review (needs_review),
    INDEX idx_feedback (user_feedback_rating, admin_feedback_rating)
);
```

### Tabela Auxiliar: `retrieval_chunks_log`

Para evitar duplicação de dados grandes no JSONB:

```sql
CREATE TABLE retrieval_chunks_log (
    id SERIAL PRIMARY KEY,
    interaction_id INT REFERENCES chat_interactions(id) ON DELETE CASCADE,
    chunk_rank INT,  -- Posição no ranking
    document_id INT,  -- Referência ao chunk original
    chunk_content TEXT,
    similarity_score FLOAT,
    metadata JSONB,
    
    INDEX idx_interaction_id (interaction_id)
);
```

---

## Implementação Backend

### 1. Criar Funções de Database (`src/data/database.py`)

```python
def insert_chat_interaction(
    session_id: str,
    message_index: int,
    user_question: str,
    retrieval_data: dict,
    llm_data: dict,
    performance_data: dict,
    metadata: Optional[dict] = None
) -> int:
    """
    Insere uma nova interação de chat no banco de dados.
    
    Returns:
        ID da interação inserida
    """
    pass

def get_session_interactions(session_id: str) -> list[dict]:
    """
    Retorna todas as interações de uma sessão.
    """
    pass

def get_interaction_detail(interaction_id: int) -> dict:
    """
    Retorna detalhes completos de uma interação específica.
    """
    pass

def update_interaction_feedback(
    interaction_id: int,
    rating: int,
    comment: Optional[str] = None,
    is_admin: bool = False
) -> bool:
    """
    Adiciona feedback a uma interação.
    """
    pass

def mark_interaction_for_review(interaction_id: int, reason: str) -> bool:
    """
    Marca uma interação para revisão pelo admin.
    """
    pass

def get_interactions_needing_review(limit: int = 50) -> list[dict]:
    """
    Retorna interações que precisam de revisão.
    """
    pass
```

### 2. Modificar `src/core/rag.py`

Adicionar logging em `query_rag_with_history()`:

```python
def query_rag_with_history(...):
    # ... código existente ...
    
    # Timestamps para tracking
    start_time = time.time()
    retrieval_start = time.time()
    
    # Buscar documentos
    results = search_similar(...)
    retrieval_time = (time.time() - retrieval_start) * 1000
    
    # Construir contexto
    context = build_context(results)
    
    # Gerar resposta
    llm_start = time.time()
    answer = generate_answer(...)
    llm_time = (time.time() - llm_start) * 1000
    
    total_time = (time.time() - start_time) * 1000
    
    # Logar interação
    interaction_data = {
        'session_id': session_id,
        'message_index': len(conversation.messages) // 2,
        'user_question': question,
        'retrieval_data': {
            'method': 'hybrid',  # ou outro método usado
            'collection_id': collection_id,
            'top_k': top_k,
            'chunks': [
                {
                    'id': r['id'],
                    'score': r['score'],
                    'content': r['content'][:500],  # Preview
                    'metadata': r['metadata']
                }
                for r in results
            ],
            'avg_score': sum(r['score'] for r in results) / len(results) if results else 0,
            'time_ms': retrieval_time
        },
        'llm_data': {
            'model': 'gemini-1.5-flash',  # ou config.MODEL_NAME
            'prompt': final_prompt,
            'response': answer,
            'temperature': temperature,
            'time_ms': llm_time,
            'prompt_tokens': estimate_tokens(final_prompt),
            'response_tokens': estimate_tokens(answer)
        },
        'performance_data': {
            'retrieval_ms': retrieval_time,
            'llm_ms': llm_time,
            'total_ms': total_time
        },
        'metadata': {
            'prompt_category': selected_prompt_category,
            'has_sources': include_sources,
            'sources_count': len(results)
        }
    }
    
    try:
        insert_chat_interaction(**interaction_data)
    except Exception as e:
        # Não falhar a request se logging falhar
        api_logger.error(f"Failed to log interaction: {e}")
    
    # ... resto do código ...
```

### 3. Criar Script de Migration

`db/migrations/add_chat_interactions_table.sql`:

```sql
-- Migration: Add chat interactions logging
-- Created: 2025-12-27

BEGIN;

-- Criar tabela principal
CREATE TABLE IF NOT EXISTS chat_interactions (
    -- [Schema completo aqui]
);

-- Criar tabela auxiliar
CREATE TABLE IF NOT EXISTS retrieval_chunks_log (
    -- [Schema completo aqui]
);

-- Adicionar comentários
COMMENT ON TABLE chat_interactions IS 'Logs de todas as interações de chat para análise e aprendizado contínuo';
COMMENT ON TABLE retrieval_chunks_log IS 'Detalhes dos chunks recuperados em cada interação';

COMMIT;
```

---

## Implementação Frontend

### 1. Novos Endpoints API (`src/api/routes.py`)

```python
@api.route("/admin/interactions", methods=["GET"])
def get_interactions():
    """
    Lista interações com filtros.
    
    Query params:
        - session_id: filtrar por sessão
        - needs_review: apenas interações marcadas
        - from_date: data inicial
        - to_date: data final
        - limit: limite de resultados
    """
    pass

@api.route("/admin/interactions/<int:interaction_id>", methods=["GET"])
def get_interaction_detail(interaction_id: int):
    """
    Retorna detalhes completos de uma interação.
    """
    pass

@api.route("/admin/interactions/<int:interaction_id>/feedback", methods=["POST"])
def add_interaction_feedback(interaction_id: int):
    """
    Adiciona feedback do admin a uma interação.
    
    Body:
        {
            "rating": 1-5,
            "comment": "...",
            "needs_review": false
        }
    """
    pass

@api.route("/admin/analytics/interactions", methods=["GET"])
def get_interaction_analytics():
    """
    Retorna métricas agregadas das interações.
    """
    pass
```

### 2. Nova UI: Interaction Detail View

Criar `frontend/src/components/admin/InteractionDetail.tsx`:

- Mostrar pergunta do usuário
- Documentos recuperados com scores
- Contexto usado
- Prompt completo enviado à LLM
- Resposta da LLM
- Métricas de performance (tempo de retrieval, LLM, total)
- Tokens usados
- Botões de feedback (⭐ rating + comentário)
- Marcar para revisão

### 3. Expandir SessionsPanel

Adicionar na visualização de histórico de cada mensagem:
- Botão "Ver Detalhes" que abre `InteractionDetail`
- Indicador visual de qualidade (se tiver feedback)
- Badge "Precisa Revisão" se marcado

### 4. Nova Tab: "Análise de Qualidade"

Criar `frontend/src/components/admin/QualityAnalysis.tsx`:

- Lista de interações que precisam revisão
- Filtros por data, sessão, rating
- Métricas agregadas:
  - Tempo médio de resposta
  - Distribuição de ratings
  - Queries mais comuns
  - Documentos mais utilizados
  - Taxa de erro

---

## Roadmap de Implementação

### Fase 1: Database Setup (1-2 dias)
- [ ] Criar script de migration
- [ ] Executar migration no ambiente de dev
- [ ] Criar funções básicas de insert/select
- [ ] Testes unitários das funções de DB

### Fase 2: Backend Integration (2-3 dias)
- [ ] Modificar `query_rag_with_history` para logar
- [ ] Adicionar logging em outras funções (query_rag, etc.)
- [ ] Criar endpoints da API
- [ ] Tratamento de erros e fallbacks
- [ ] Testes de integração

### Fase 3: Frontend - Visualização Básica (2-3 dias)
- [ ] Criar `InteractionDetail` component
- [ ] Integrar com `SessionsPanel`
- [ ] Criar UI para ver detalhes de cada mensagem
- [ ] Testes manuais

### Fase 4: Frontend - Features Avançadas (3-4 dias)
- [ ] Sistema de feedback (ratings + comentários)
- [ ] Tab de "Análise de Qualidade"
- [ ] Filtros e busca
- [ ] Métricas e gráficos
- [ ] Export de dados (CSV/JSON)

### Fase 5: Testing & Refinement (1-2 dias)
- [ ] Testes end-to-end
- [ ] Performance testing (verificar impacto do logging)
- [ ] Ajustes de UX
- [ ] Documentação

**Tempo Total Estimado**: 9-14 dias de desenvolvimento

---

## Considerações Técnicas

### Performance

1. **Logging Assíncrono**: Não bloquear a resposta ao usuário
   - Usar thread separada ou queue para inserções
   - Cache de escritas se necessário

2. **Índices do Banco**: Garantir queries rápidas
   - Índices em session_id, timestamp, collection_id
   - Considerar particionamento por data se volume for muito alto

3. **Retenção de Dados**: Política de limpeza
   - Manter últimos 90 dias em tabela principal
   - Arquivar dados antigos em tabela separada
   - Agregações para dados históricos

### Segurança

1. **Dados Sensíveis**: 
   - Não logar informações pessoais nas queries
   - Sanitizar antes de inserir
   - GDPR compliance: direito de remoção

2. **Controle de Acesso**:
   - Apenas admins podem ver detalhes
   - Logs de quem acessou quais interações

### Escalabilidade

1. **Volume de Dados**:
   - ~100 interações/dia = ~36k/ano
   - ~1MB/interação (estimativa) = ~36GB/ano
   - Planejar para crescimento

2. **Otimizações**:
   - Comprimir campos TEXT grandes
   - Limitar tamanho de prompts/respostas logadas
   - Usar JSONB indexes para metadata

---

## Métricas de Sucesso

Após implementação, devemos ser capazes de responder:

1. **Qualidade**:
   - Qual % de respostas tem rating positivo?
   - Quais tipos de perguntas geram respostas ruins?
   - Quais prompts performam melhor?

2. **Performance**:
   - Tempo médio de retrieval?
   - Tempo médio de LLM?
   - Gargalos no pipeline?

3. **Uso**:
   - Quais coleções são mais usadas?
   - Quais documentos aparecem mais frequentemente?
   - Padrões de uso por horário/dia?

4. **Problemas**:
   - Taxa de erro?
   - Queries que falham consistentemente?
   - Cenários que precisam melhorar?

---

## Próximos Passos

1. **Revisar este plano** e ajustar conforme necessário
2. **Priorizar features** (pode implementar por fases)
3. **Setup de ambiente** para desenvolvimento
4. **Começar pela Fase 1** quando estiver pronto

---

## Referências

- [PostgreSQL JSONB Best Practices](https://www.postgresql.org/docs/current/datatype-json.html)
- [Logging Best Practices for ML Systems](https://cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning)
- [Database Indexing Strategies](https://use-the-index-luke.com/)

---

**Documento criado em**: 2025-12-27  
**Versão**: 1.0  
**Status**: Planejamento
