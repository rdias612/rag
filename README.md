# RAG System - Sistema de Recuperação e Geração Aumentada

Sistema RAG (Retrieval-Augmented Generation) local para consulta inteligente de documentos com técnicas avançadas de recuperação, interface web moderna e arquitetura escalável.

## 🚀 Tecnologias Utilizadas

| Componente | Tecnologia | Versão | Descrição |
|------------|------------|--------|-----------|
| **Banco de Dados** | PostgreSQL + pgvector | 16+ | Armazenamento e busca vetorial |
| **Embeddings** | BGE-M3 (bge-m3) | - | Modelo multilingue (1024 dimensões) via LM Studio |
| **LLM** | Phi-3.5 Mini | - | Geração de respostas via LM Studio |
| **API** | Flask + Flask-CORS | 3.0+ | Backend REST API |
| **Frontend** | React 19 + Vite | 7.2+ | Interface moderna e responsiva |
| **Estilização** | Tailwind CSS | 4.1+ | Design system e componentes |
| **NLP** | spaCy + langdetect | 3.7+ | Chunking semântico e detecção de idioma |
| **Monitoramento** | Prometheus | 0.19+ | Coleta de métricas de performance |
| **Re-ranking** | sentence-transformers | 2.2+ | Cross-encoder para melhoria de relevância |
| **Validação** | Pydantic | 2.0+ | Validação de dados e configurações |
| **Migrações** | Alembic | 1.13+ | Gerenciamento de schema do banco |
| **Agendamento** | APScheduler | 3.10+ | Tarefas em background |
| **Ingestão** | pypdf, python-docx, bs4 | - | Extração de múltiplos formatos |

---

## ✨ Funcionalidades Principais

### 📄 Ingestão de Documentos
- **Múltiplos formatos**: PDF, DOCX, TXT, Markdown, HTML
- **Processamento em background**: Upload assíncrono com status tracking
- **Ingestão em massa**: Processamento de múltiplos documentos simultaneamente
- **Detecção de alterações**: Re-ingestão automática de arquivos modificados
- **Gerenciamento de coleções**: Organização por projeto/categoria
- **Controle de versão**: Hash SHA-256 para detectar alterações
- **Estatísticas detalhadas**: Contagem de chunks, páginas, tamanho de arquivos

### 🔍 Busca e Recuperação Avançada
- **Busca Híbrida**: Combina busca vetorial (semântica) + Full-Text Search (palavras-chave)
- **Re-ranking com Cross-Encoder**: Refina resultados usando modelo especializado
- **Query Expansion**: Gera variações da pergunta para busca mais abrangente
- **HyDE (Hypothetical Document Embeddings)**: Gera documento hipotético para melhorar busca
- **MMR (Maximal Marginal Relevance)**: Diversifica resultados para evitar redundância
- **Adaptive Retrieval**: Ajusta parâmetros baseado na complexidade da pergunta
- **Filtro de similaridade**: Descarta resultados irrelevantes automaticamente

### 🗜️ Otimização de Contexto
- **Compressão de Contexto**: Reduz contexto grande automaticamente antes de enviar ao LLM
- **Hierarchical Chunking**: Divisão em chunks pais e filhos (opcional)
- **Sentence Window**: Inclui contexto de sentenças vizinhas (opcional)
- **Contextual Metadata**: Metadados contextuais para melhor recuperação

### 💬 Sistema de Conversação
- **Histórico de conversas**: Perguntas de follow-up com contexto mantido
- **Gerenciamento de sessões**: Sessões isoladas com expiração automática
- **Streaming**: Respostas em tempo real
- **Suporte multi-idioma**: Detecção automática (PT, EN, ES, DE, FR, IT)

### 🎯 Sistema de Prompts Dinâmico
- **13 prompts pré-configurados**: Para diferentes cenários de uso
- **Gerenciamento via API**: Criar, atualizar, deletar prompts
- **Categorias organizadas**: RAG principal, HyDE, Query Expansion, Instruções
- **Priorização**: Sistema de prioridade para seleção automática
- **Versionamento**: Controle de versões de prompts

### 🔬 Observabilidade e Monitoramento
- **Métricas Prometheus**: Métricas nativas em cada fase do RAG
- **Modo Debug/Explain**: Transparência total no pipeline (timing, scores, HyDE)
- **Logging estruturado**: Logs detalhados para debugging
- **Estátisticas de cache**: Hit rate, tamanho, performance

### 🛡️ Qualidade e Validação
- **Classificador de perguntas**: Identifica tipo de pergunta automaticamente
- **Auto-avaliação**: Avalia qualidade de respostas RAG (opcional)
- **Validação com Pydantic**: Validação rigorosa de inputs/outputs
- **Sanitização de inputs**: Prevenção de ataques e injeções

### 🔧 Administração
- **Admin Dashboard**: Interface web completa para gerenciamento
- **Upload via API**: Upload de documentos com tracking
- **Gerenciamento de documentos**: Listar, deletar documentos ingeridos
- **Sistema de feedback**: Coleta feedback do usuário sobre respostas
- **Configuração via Env**: Suporte a ambientes DEV, SIT e UAT via arquivos `.env`

---

## 📁 Estrutura do Projeto

```
rag/
├── db/                            # Banco de dados
│   ├── docker-compose.yml         # PostgreSQL + pgvector + Adminer
│   └── init.sql                   # Script de inicialização
├── scripts/                       # Scripts utilitários
│   └── ingest.py                  # CLI para ingestão de documentos
├── frontend/                      # Interface Web (React)
│   ├── src/
│   │   ├── api.ts                 # Cliente da API
│   │   ├── App.tsx               # Componente principal
│   │   ├── components/           # Componentes React
│   │   │   ├── AdminDashboard.tsx    # Dashboard admin
│   │   │   ├── ChatArea.tsx          # Área de chat
│   │   │   ├── DocumentsPanel.tsx    # Gerenciamento de docs
│   │   │   ├── PromptsManagement.tsx # Gestão de prompts
│   │   │   └── ...                   # Outros componentes
│   │   └── types.ts              # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── src/                           # Backend Python
│   ├── api/                       # Rotas Flask
│   │   ├── routes.py              # Endpoints da API
│   │   └── schemas.py             # Schemas Pydantic
│   ├── core/                      # Lógica RAG e NLP
│   │   ├── rag.py                 # Pipeline RAG principal
│   │   ├── embeddings.py          # Geração de embeddings
│   │   ├── llm.py                 # Interface com LLM
│   │   ├── prompt_manager.py      # Gerenciador de prompts
│   │   ├── reranker.py            # Re-ranking de resultados
│   │   ├── query_expansion.py     # Expansão de queries
│   │   ├── hyde.py                # Geração HyDE
│   │   ├── mmr.py                 # Algoritmo MMR
│   │   ├── adaptive_retrieval.py  # Recuperação adaptativa
│   │   ├── context_compression.py # Compressão de contexto
│   │   ├── embedding_cache.py     # Cache de embeddings
│   │   ├── question_classifier.py # Classificador de perguntas
│   │   ├── evaluation.py          # Avaliação de respostas
│   │   ├── metrics.py             # Métricas Prometheus
│   │   └── logger.py              # Logging estruturado
│   ├── data/                      # Camada de dados
│   │   ├── database.py            # Conexão PostgreSQL
│   │   ├── ingestion.py           # Ingestão de documentos
│   │   ├── chunking.py            # Chunking semântico
│   │   ├── hybrid_search.py       # Busca híbrida
│   │   ├── hierarchical_chunking.py # Chunking hierárquico
│   │   └── sentence_window.py     # Sentence window retrieval
│   ├── app.py                     # Aplicação Flask
│   └── config.py                  # Configurações (Pydantic Settings)
├── alembic/                       # Migrações do banco
│   └── versions/                  # Scripts de migração
├── docs/                          # Documentação adicional
│   ├── MELHORIAS.md               # Lista de melhorias
│   └── ...
├── .env.example                   # Template de configurações
├── .env.sit                       # Configurações SIT
├── .env.uat                       # Configurações UAT
├── run_app.py                     # Script de inicialização unificado
├── requirements.txt                # Dependências Python
└── alembic.ini                    # Configuração Alembic
```

---

## ⚙️ Configuração

### Pré-requisitos

1. **Python 3.11+** e **Node.js 18+**
2. **Docker** (para PostgreSQL)
3. **LM Studio** com modelos `bge-m3` e `phi-3.5-mini` carregados

### 1. Preparar o Ambiente

```bash
# Backend
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m spacy download pt_core_news_sm

# Frontend
cd frontend
npm install
cd ..
```

### 2. Banco de Dados

```bash
cd db
docker-compose up -d
cd ..
alembic upgrade head
```

### 3. Variáveis de Ambiente

O sistema utiliza `pydantic-settings` para configuração:

```bash
# Copiar template
cp .env.example .env

# Editar .env com suas configurações
# Ou usar ambientes específicos:
# export APP_ENV=sit  # Usa .env.sit
# export APP_ENV=uat  # Usa .env.uat
```

Variáveis principais:
- `LM_STUDIO_BASE_URL`: URL do LM Studio (default: `http://127.0.0.1:1234/v1`)
- `DOCUMENTS_DIR`: Diretório de documentos
- `DATABASE_*`: Configurações PostgreSQL
- `ENABLE_*`: Ativar/desativar funcionalidades (HyDE, MMR, etc.)

---

## 🔧 Uso

### Iniciar Tudo (Recomendado)

```bash
python run_app.py
```

Este script inicia:
- Backend Flask (porta 5000)
- Frontend Vite (porta 5173)
- Limpeza automática de sessões expiradas

### Acessar Interface Web

- **Frontend**: http://localhost:5173
- **Admin Dashboard**: Disponível na interface web
- **API Docs**: Ver seção de endpoints abaixo

### Ingestão de Documentos

**Via Interface Web**:
1. Acesse Admin Dashboard
2. Vá em "Documentos"
3. Use "Upload" ou "Ingerir Todos"

**Via CLI**:
```bash
# Ingerir pasta de documentos padrão
python -m scripts.ingest

# Verificar status
python -m scripts.ingest --stats
```

**Via API**:
```bash
# Upload de arquivo
curl -X POST http://localhost:5000/api/ingest \
  -F "file=@documento.pdf"

# Verificar status
curl http://localhost:5000/api/ingest/status/{job_id}

# Ingerir todos
curl -X POST http://localhost:5000/api/documents/ingest-all \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

---

## 📡 API Endpoints

### Query RAG

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/query` | POST | Query RAG principal |
| `/api/query/stream` | POST | Query com streaming |
| `/api/chat` | POST | Chat com histórico |
| `/api/search` | POST | Apenas busca (sem LLM) |

**Exemplo /api/query**:
```json
{
  "question": "O que é GWPRP?",
  "top_k": 5,
  "temperature": 0.7,
  "include_sources": true,
  "collection": "default",
  "debug": false
}
```

**Exemplo /api/chat**:
```json
{
  "question": "Como funciona o GWPRP?",
  "session_id": "uuid-da-sessão",
  "top_k": 5,
  "temperature": 0.7
}
```

### Sessões

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/chat/sessions` | GET | Listar sessões |
| `/api/chat/sessions/<id>` | GET | Histórico de sessão |
| `/api/chat/sessions/<id>` | DELETE | Deletar sessão |
| `/api/chat/new` | POST | Criar nova sessão |

### Documentos

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/ingest` | POST | Upload de documento |
| `/api/ingest/status/<job_id>` | GET | Status do job |
| `/api/ingest/jobs` | GET | Listar todos jobs |
| `/api/ingest/formats` | GET | Formatos suportados |
| `/api/documents/stats` | GET | Estatísticas do diretório |
| `/api/documents/scan` | GET | Documentos pendentes |
| `/api/documents/ingest-all` | POST | Ingerir todos |
| `/api/documents/ingest-status` | GET | Status da ingestão em massa |
| `/api/documents/reprocess` | POST | Re-processar tudo |
| `/api/documents/ingested` | GET | Lista documentos ingeridos |
| `/api/documents/delete` | POST | Deletar documento |

### Prompts

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/prompts` | GET | Listar todos prompts |
| `/api/prompts/<id>` | GET | Detalhes do prompt |
| `/api/prompts` | POST | Criar novo prompt |
| `/api/prompts/<id>` | PUT | Atualizar prompt |
| `/api/prompts/<id>` | DELETE | Deletar prompt |
| `/api/prompts/categories` | GET | Categorias disponíveis |

### Métricas e Debug

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/metrics` | GET | Métricas Prometheus |
| `/api/metrics/status` | GET | Status do módulo |
| `/api/cache/stats` | GET | Estatísticas do cache |
| `/api/cache/clear` | POST | Limpar cache |
| `/api/classify` | POST | Classificar pergunta |
| `/api/evaluate` | POST | Avaliar resposta RAG |
| `/api/hyde/test` | POST | Testar HyDE |

### Sistema

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Estatísticas gerais |
| `/api/collections` | GET | Listar coleções |

---

## 🎨 Interface Web (Frontend)

### Funcionalidades

- **Chat Interface**: Chat moderno com streaming de respostas
- **Admin Dashboard**:
  - **Documentos**: Upload, listagem, gerenciamento
  - **Prompts**: Criar, editar, deletar prompts
  - **Sessões**: Ver e gerenciar sessões ativas
  - **Overview**: Estatísticas do sistema
- **Debug Panel**: Visualização detalhada do pipeline RAG
- **Modo Dark/Light**: Alternância de temas
- **Responsivo**: Funciona em desktop e mobile

### Componentes Principais

- `ChatArea`: Área principal de conversação
- `MessageList`: Lista de mensagens com markdown
- `MessageInput`: Input com suporte a multi-linha
- `UploadModal`: Modal de upload de documentos
- `AdminDashboard`: Dashboard administrativo
- `PromptsManagement`: Gerenciador de prompts
- `DocumentsPanel`: Painel de documentos
- `SessionsPanel`: Painel de sessões
- `DebugPanel`: Painel de debug
- `TemperatureSelector`: Seletor de temperatura
- `ThemeContext`: Contexto de tema

---

## 🔬 Técnicas RAG Implementadas

### 1. Busca Híbrida
Combina similaridade semântica (embeddings) com busca textual (FTS):
- **Alpha**: 0.7 (70% vetorial, 30% FTS)
- Ajustável via `HYBRID_SEARCH_ALPHA`

### 2. Re-ranking
Refina resultados usando Cross-Encoder:
- Modelo: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Top-K inicial: 15 → Top-K final: 5
- Melhora significativamente a precisão

### 3. HyDE (Hypothetical Document Embeddings)
Gera documento hipotético para busca:
- Usa LLM para criar resposta "ideal"
- Busca embeddings do documento hipotético
- Melhora buscas por conceito abstratos

### 4. Query Expansion
Gera variações da pergunta:
- Número de variações: 3
- Aumenta cobertura de busca
- Útil para perguntas complexas

### 5. MMR (Maximal Marginal Relevance)
Diversifica resultados:
- Lambda: 0.7 (equilíbrio relevância/diversidade)
- Evita chunks muito similares
- Melhor cobertura de tópicos

### 6. Adaptive Retrieval
Ajusta parâmetros automaticamente:
- Baseia-se no classificador de perguntas
- Ajusta top_k, temperatura, etc.
- Melhora eficiência

### 7. Context Compression
Reduz tamanho do contexto:
- Threshold: 3000 tokens
- Método: LLM-based
- Preserva informações relevantes

### 8. Cache de Embeddings
Cache LRU para embeddings:
- Max size: 1000
- Hit rate esperado: 30-50%
- Reduz latência drasticamente

### 9. Classificador de Perguntas
Identifica tipo de pergunta:
- Types: definition, comparison, procedure, troubleshooting, etc.
- Permite prompts específicos por tipo
- Melhora precisão

---

## 📊 Métricas

### Métricas Disponíveis (Prometheus)

- `rag_query_duration_seconds`: Tempo total de query
- `rag_embedding_duration_seconds`: Tempo de embedding
- `rag_search_duration_seconds`: Tempo de busca
- `rag_llm_duration_seconds`: Tempo do LLM
- `rag_chunks_retrieved`: Número de chunks retornados
- `rag_similarity_score`: Similaridade média
- `rag_cache_hits_total`: Hits do cache
- `rag_cache_misses_total`: Misses do cache
- `rag_errors_total`: Erros totais

### Acesso às Métricas

```bash
# Scraping (formato Prometheus)
curl http://localhost:5000/api/metrics

# Verificar status
curl http://localhost:5000/api/metrics/status
```

### Dashboard Sugestão (Grafana)

- Query Latency: P95, P99, média
- Cache Hit Rate: Hits vs Misses
- Error Rate: Taxa de erros
- Chunks per Query: Distribuição
- Similarity Distribution: Histograma de similaridade

---

## 🗄️ Banco de Dados

### Tabelas Principais

**documentos**:
- Chunks indexados com embeddings
- Metadados (source, page, collection_id)
- Vetor pgvector (1024 dimensões)

**prompts**:
- Templates de prompts
- Categorias e prioridades
- Versionamento

**user_feedback**:
- Feedback do usuário
- Rating (1-5)
- Comentários

**ingestion_control**:
- Controle de ingestão
- Hash SHA-256
- Status e timestamps

**conversation_history**:
- Histórico de conversas
- Sessões com expiração

### Migrações

```bash
# Ver status
alembic current

# Criar nova migração
alembic revision --autogenerate -m "Descrição"

# Aplicar migrações
alembic upgrade head

# Reverter
alembic downgrade -1
```

---

## 🧪 Desenvolvimento

### Testes

```bash
# Executar todos os testes
pytest

# Com cobertura
pytest --cov=src --cov-report=html

# Testes específicos
pytest tests/test_embeddings.py
```

### Linting e Formatação

```bash
# Type checking
mypy src/

# Linting
flake8 src/

# Formatação (Black)
black src/

# Ordenação de imports
isort src/
```

### Logs

Logs estruturados em formato JSON:
- **DEBUG**: Detalhes de execução
- **INFO**: Eventos importantes
- **WARNING**: Situações anormais não-críticas
- **ERROR**: Erros que requerem atenção

---

## 🚀 Performance

### Benchmarks

| Operação | Tempo Alvo | Tempo Atual |
|----------|------------|-------------|
| Embedding (cache hit) | < 50ms | ~10ms |
| Embedding (cache miss) | < 500ms | ~200ms |
| Busca vetorial | < 100ms | ~50ms |
| Re-ranking | < 200ms | ~100ms |
| LLM generation | < 2s | ~1.5s |
| Query total | < 3s | ~1.8s |

### Otimizações Implementadas

- ✅ Cache de embeddings (LRU)
- ✅ Batch processing de embeddings
- ✅ Pool de conexões PostgreSQL
- ✅ Re-ranking eficiente
- ✅ Compressão de contexto
- ✅ Background processing
- ✅ Query expansion seletiva

---

## 📝 Melhorias Futuras

Ver documento completo em `docs/MELHORIAS_COMPLETAS.md`

### Próximas Prioridades

- [ ] **Sistema de autenticação**: API Key ou JWT
- [ ] **Rate limiting**: Prevenção de abuso
- [ ] **Testes automatizados**: Suíte completa
- [ ] **Distributed tracing**: OpenTelemetry/Jaeger
- [ ] **Sistema de filas**: Celery ou RQ
- [ ] **Exportação de conversas**: JSON, Markdown, TXT
- [ ] **Sugestões de perguntas**: Baseadas em documentos
- [ ] **Multi-query**: Busca com múltiplas variações
- [ ] **Temporal re-ranking**: Priorizar documentos recentes

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Projeto para estudo de técnicas avançadas de RAG.

---

## 📞 Suporte

- **Issues**: GitHub Issues
- **Documentação**: Ver pasta `docs/`
- **Exemplos**: `docs/MELHORIAS.md`

---

## 🙏 Agradecimentos

- **BAAI**: Modelo BGE-M3
- **Microsoft**: Modelo Phi-3.5 Mini
- **LangChain**: Inspiração e conceitos
- **Sentence Transformers**: Modelos de re-ranking
- **spaCy**: Processamento de NLP

---

## 📖 Recursos Adicionais

- [Documentação BGE-M3](https://github.com/FlagOpen/FlagEmbedding)
- [Documentação Phi-3](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct)
- [Prometheus](https://prometheus.io/)
- [pgvector](https://github.com/pgvector/pgvector)

---

**Última atualização**: Dezembro 2025
**Versão**: 2.0
