# RAG System - Sistema de Recuperação e Geração Aumentada

Sistema RAG (Retrieval-Augmented Generation) local para consulta inteligente de documentos com suporte a múltiplos formatos, histórico de conversas, busca híbrida e ingestão via API.

## 🚀 Tecnologias Utilizadas

| Componente | Tecnologia | Descrição |
|------------|------------|-----------|
| **Banco de Dados** | PostgreSQL + pgvector | Armazenamento e busca vetorial |
| **Embeddings** | Nomic Embed v1.5 | Modelo de embeddings via LM Studio |
| **LLM** | Phi-3.5 Mini | Geração de respostas via LM Studio |
| **API** | Flask | Backend REST API |
| **NLP** | spaCy | Chunking semântico por sentenças |
| **Ingestão** | pypdf, python-docx, beautifulsoup4 | Extração de múltiplos formatos |
| **Testes** | pytest | Testes automatizados |

---

## ✨ Funcionalidades

- 📄 **Múltiplos formatos**: PDF, DOCX, TXT, Markdown, HTML
- 🔍 **Busca Híbrida**: Combina busca vetorial (semântica) + Full-Text Search (palavras-chave)
- 🗜️ **Compressão de Contexto**: Reduz contexto grande automaticamente antes de enviar ao LLM
- 🔎 **Filtro de similaridade**: Descarta resultados irrelevantes automaticamente
- 💬 **Histórico de conversas**: Perguntas de follow-up com contexto mantido
- 📤 **Upload via API**: Ingestão de documentos com processamento assíncrono
- ✂️ **Chunking semântico**: Divisão inteligente por sentenças (spaCy)
- 🔄 **Streaming**: Respostas em tempo real
- 📊 **Logging detalhado**: Sistema de logs para API, RAG e ingestão
- 🧪 **Testes automatizados**: Suíte de testes para validação de funcionalidades

---

## 📁 Estrutura do Projeto

```
rag/
├── db/
│   ├── docker-compose.yml    # PostgreSQL + pgvector + Adminer
│   ├── init.sql              # Script de inicialização do banco
│   └── connections.md        # Documentação de conexões
├── scripts/
│   └── ingest.py             # CLI para ingestão de documentos
├── src/
│   ├── api/
│   │   └── routes.py         # Endpoints da API
│   ├── core/
│   │   ├── embeddings.py     # Geração de embeddings (Nomic)
│   │   ├── llm.py            # Integração com LLM (Phi-3.5)
│   │   ├── rag.py            # Pipeline RAG completo
│   │   ├── conversation.py   # Gerenciador de histórico de conversas
│   │   ├── context_compression.py  # Compressão inteligente de contexto
│   │   └── logger.py         # Sistema de logging
│   ├── data/
│   │   ├── database.py       # Conexão PostgreSQL + pgvector
│   │   ├── hybrid_search.py  # Busca híbrida (vetorial + FTS)
│   │   ├── ingestion.py      # Leitura de documentos + chunking
│   │   └── chunking.py       # Chunking semântico com spaCy
│   ├── app.py                # Aplicação Flask principal
│   └── config.py             # Configurações centralizadas
├── tests/
│   └── test_chunking_comparison.py  # Testes de chunking
├── docs/
│   ├── MELHORIAS.md          # Roadmap de melhorias
│   ├── PLANO_CHUNKING_SEMANTICO.md  # Plano de implementação do chunking
│   └── EVOLUCAO_LANGCHAIN_SGLANG.md  # Evolução futura com LangChain
├── requirements.txt
└── README.md
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

# Instalar dependências pinadas (produção/estável)
pip install -r requirements.txt

# Para desenvolvimento (incluindo pip-tools e ferramentas de dev)
pip install -r requirements-dev.txt

python -m spacy download pt_core_news_sm

# Frontend
cd frontend
npm install
cd ..
```

> [!TIP]
> O projeto utiliza `pip-tools` para gerenciar dependências. Se desejar adicionar novos pacotes, edite os arquivos `.in` em `requirements/` e rode `pip-compile`.

#### Baixar modelos spaCy no host (para volume)

```bash
python -m venv .venv && . .venv/bin/activate
pip install spacy==3.8.11
python -m spacy download pt_core_news_sm --target ./models/spacy
python -m spacy download en_core_web_sm --target ./models/spacy
```

Monte `./models/spacy` no container (já configurado em docker-compose) para evitar downloads na imagem.

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
- `ENABLE_ADAPTIVE_RETRIEVAL`: Habilitar Adaptive Retrieval (default: true)
- `RATE_LIMIT_*`: Configurações de limite de requisições por endpoint

### Configuração de Segurança

O sistema oferece proteção de dados sensíveis em duas camadas:

#### 🔐 Criptografia em Repouso

Criptografia de dados sensíveis armazenados no banco de dados usando AES-128 + HMAC-SHA256.

**Campos Criptografados:**
- `content` (conteúdo de documentos)
- `metadata` (metadados de documentos e feedback)
- `comment` (comentários de feedback)

**Configuração:**
```bash
# Habilitar criptografia
ENABLE_ENCRYPTION=true
ENCRYPTION_KEY=your-generated-key-here
ENCRYPT_DOCUMENT_CONTENT=true
ENCRYPT_METADATA=true
ENCRYPT_FEEDBACK_COMMENTS=true
```

**Gerar chave de criptografia:**
```bash
python scripts/generate_encryption_key.py
```

⚠️ **Importante:**
- Faça backup da chave em local seguro
- Nunca commite a chave no Git
- Habilitar criptografia NÃO criptografa dados existentes automaticamente
- Para criptografar dados existentes: backup → limpar documentos → re-ingerir

#### 🔒 Criptografia em Trânsito (HTTPS)

Comunicação segura via TLS1.3 com headers de segurança (HSTS, CSP, etc.).

**Configuração:**
```bash
ENABLE_HTTPS=true
SSL_CERT_PATH=./certs/cert.pem
SSL_KEY_PATH=./certs/key.pem
SSL_PROTOCOL=TLSv1.3
SSL_CIPHERS=HIGH:!aNULL:!MD5
```

**Gerar certificado SSL (desenvolvimento):**
```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -days 365 \
  -nodes
```

**Produção (Let's Encrypt):**
```bash
sudo certbot certonly --standalone -d seu-dominio.com
# Certificados em: /etc/letsencrypt/live/seu-dominio.com/
```

#### 📊 Impacto de Performance

| Operação | Sem Criptografia | Com Criptografia |
|-----------|------------------|-------------------|
| Inserção de documento | 100ms | 110ms (+10%) |
| Busca similar | 50ms | 55ms (+10%) |
| Recuperação de documento | 10ms | 15ms (+50%) |

#### 🔧 Troubleshooting

**Erro: "Encryption key not provided"**
```bash
python scripts/generate_encryption_key.py
# Adicionar chave ao .env
```

**Erro: "SSL context creation failed"**
```bash
# Verificar arquivos
ls -la certs/

# Regenerar certificado
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes
```

#### ✅ Compliance

- **LGPD (Art. 46):** Criptografia de dados pessoais
- **ISO 27001 (A.10.1.1):** Controles de criptografia
- **SOC 2:** Proteção de informações em repouso e em trânsito

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

### Executar Testes

```bash
# Testar qualidade do chunking
python tests/test_chunking_comparison.py
```

---

# Verificar status
python -m scripts.ingest --stats
```

### Build de todas as imagens Docker

O repositório contém múltiplos `Dockerfile` (ex.: raiz/backend e `frontend/`). Para facilitar, há dois scripts que encontram todos os `Dockerfile` recursivamente e fazem o build automaticamente.

- PowerShell (Windows):

```powershell
.\scripts\build_all.ps1           # build com cache
.\scripts\build_all.ps1 -NoCache  # build sem cache

# Exemplos PowerShell com tag
```powershell
# build e usa tag 'v1.2.3'
.\scripts\build_all.ps1 -ImageTag v1.2.3
# sem cache e usa tag 'v1.2.3'
.\scripts\build_all.ps1 -ImageTag v1.2.3 -NoCache
```
```

- Bash (Linux / macOS / WSL / Git Bash):

```bash
chmod +x scripts/build_all.sh
./scripts/build_all.sh            # build com cache, tag default 'latest'
./scripts/build_all.sh --no-cache # build sem cache, tag default 'latest'
./scripts/build_all.sh mytag      # build com cache e usa tag 'mytag'
./scripts/build_all.sh --no-cache mytag # sem cache e usa tag 'mytag'
```

Comportamento:
- Cada `Dockerfile` será tagueado automaticamente com o caminho relativo (ex.: `frontend` vira `frontend:latest`).
- Os scripts rodam builds sequenciais; para builds paralelos podemos adaptar os scripts se desejar.

Argumento de tag
 - Ambos os scripts aceitam um argumento para definir a tag usada nas imagens. Se nenhum argumento for passado, a tag padrão é `latest`.
 - PowerShell: parâmetro `-ImageTag` (ex.: `.build_all.ps1 -ImageTag v1.2.3`).
 - Bash: passe a tag como primeiro argumento, ou use `--no-cache` seguido da tag (ex.: `./build_all.sh v1.2.3` ou `./build_all.sh --no-cache v1.2.3`).
 - A tag final aplicada às imagens terá o formato `<path-based-name>:<tag>` (ex.: `frontend:v1.2.3`).

Alternativa com `docker-compose`:

Se os serviços estiverem declarados em `docker-compose.yml` com `build:`, você pode usar:

```bash
docker-compose build --no-cache
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
  "enable_adaptive": true,
  "debug": false
}
```

**Nota**: O parâmetro `enable_adaptive` permite habilitar/desabilitar o Adaptive Retrieval por query. Quando habilitado, o sistema ajusta automaticamente `top_k` e `min_similarity` baseado na complexidade da pergunta.

**Exemplo /api/chat**:
```json
{
  "question": "Como funciona o GWPRP?",
  "session_id": "uuid-da-sessão",
  "top_k": 5,
  "temperature": 0.7,
  "include_explanation": true,
  "enable_adaptive": true
}
```

**Nota**: O parâmetro `include_explanation` (default: true) adiciona uma explicação detalhada do processo RAG na resposta, incluindo timeline de etapas, métricas de similaridade e detalhes técnicos.

**Nota**: O parâmetro `search_mode` (default: "automatic") define a estratégia de recuperação:
- `"automatic"`: Sistema decide automaticamente (hierárquico ou sentence window)
- `"hierarchical"`: Usa chunks grandes para contexto amplo (Explicação)
- `"sentence"`: Usa sentenças individuais expandidas para precisão (Precisão)

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

### Batch Processing Avançado

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/embeddings/advanced-stats` | GET | Estatísticas do processador avançado |
| `/api/embeddings/advanced-stats/reset` | POST | Resetar estatísticas |

### Métricas e Debug

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/metrics` | GET | Métricas Prometheus |
| `/api/metrics/status` | GET | Status do módulo |
| `/api/metrics/adaptive-retrieval/stats` | GET | Estatísticas agregadas do Adaptive Retrieval |
| `/api/metrics/adaptive-retrieval/recent` | GET | Queries recentes com ajustes aplicados |
| `/api/metrics/adaptive-retrieval/performance` | GET | Métricas de performance do Adaptive |
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
- **Adaptive Retrieval Toggle**: Botão no header para habilitar/desabilitar automaticamente
- **Admin Dashboard**:
  - **Documentos**: Upload, listagem, gerenciamento
  - **Prompts**: Criar, editar, deletar prompts
  - **Sessões**: Ver e gerenciar sessões ativas
  - **Overview**: Estatísticas do sistema
  - **Adaptive Retrieval Metrics**: Dashboard de métricas de adaptive retrieval
- **Debug Panel**: Visualização detalhada do pipeline RAG
- **Modo Dark/Light**: Alternância de temas
- **Responsivo**: Funciona em desktop e mobile

### Componentes Principais

- `ChatArea`: Área principal de conversação
- `MessageList`: Lista de mensagens com markdown e botão de explicação
- `MessageInput`: Input com suporte a multi-linha
- `UploadModal`: Modal de upload de documentos
- `ExplanationModal`: Modal de explicação detalhada do pipeline RAG
- `AdminDashboard`: Dashboard administrativo
- `PromptsManagement`: Gerenciador de prompts
- `DocumentsPanel`: Painel de documentos
- `SessionsPanel`: Painel de sessões
- `DebugPanel`: Painel de debug
- `TemperatureSelector`: Seletor de temperatura
- `ThemeContext`: Contexto de tema
- `AdaptiveRetrievalMetrics`: Dashboard de métricas de adaptive

---

## 🔬 Técnicas RAG Implementadas

### 1. Busca Híbrida
Combina similaridade semântica (embeddings) com busca textual (FTS):
- **Alpha**: 0.7 (70% vetorial, 30% FTS)
- Ajustável via `HYBRID_SEARCH_ALPHA`

### 2. Re-ranking
Refina resultados usando Cross-Encoder:
- Modelo: `text-embedding-bge-reranker-v2-m3`
- Top-K inicial: 15 → Top-K final: 5
- Melhora significativamente a precisão

### 3. HyDE (Hypothetical Document Embeddings)
Gera documento hipotético para busca:
- Usa LLM para criar resposta "ideal"
- Busca embeddings do documento hipotético
- Melhora buscas por conceito abstratos

### 4. Query Expansion
Gera variações da pergunta usando LLM para busca mais abrangente:
- **Número de variações**: 3 (configurável via `QUERY_EXPANSION_COUNT`)
- **Fusão com RRF**: Combina resultados de múltiplas buscas usando Reciprocal Rank Fusion
- **Melhoria de recall**: +20-40% na recuperação de documentos relevantes
- **Prompt customizável**: Gerenciado via banco de dados (tabela `prompts`)
- **Útil para**: Perguntas curtas, ambíguas, ou com terminologia técnica variada
- **Documentação detalhada**: `docs/melhorias_feitas/IMPLEMENTACAO_2_QUERY_EXPANSION.md`

### 5. MMR (Maximal Marginal Relevance)
Diversifica resultados:
- Lambda: 0.7 (equilíbrio relevância/diversidade)
- Evita chunks muito similares
- Melhor cobertura de tópicos

### 6. Adaptive Retrieval
Ajusta parâmetros dinamicamente baseado na complexidade da query:
- **Análise de Complexidade**: Detecta nível (0-10) considerando:
  - Número de palavras
  - Presença de palavras interrogativas (como, por que, etc.)
  - Múltiplas frases
  - Terminologia técnica
- **Ajuste Automático**:
  - **Queries Simples (0-3)**: Aumenta `top_k` e diminui `min_similarity` para buscar mais contexto
  - **Queries Médias (4-6)**: Usa valores padrão (equilíbrio)
  - **Queries Complexas (7-10)**: Diminui `top_k` e aumenta `min_similarity` para focar nos mais relevantes
- **Configurável**: Limites ajustáveis via `MAX_TOP_K_ADAPTIVE`, `MIN_TOP_K_ADAPTIVE`, etc.
- **Toggle de Usuário**: Botão no header para habilitar/desabilitar
- **Métricas Completas**:
  - Estatísticas agregadas (total, complexidade média, etc.)
  - Distribuição de complexidade (Simple/Medium/Complex)
  - Tabela de queries recentes com ajustes aplicados
  - Monitoramento via Admin Dashboard
- **Documentação Detalhada**: `docs/melhorias_feitas/IMPLEMENTACAO_ADAPTIVE_RETRIEVAL.md`

**Exemplo de Uso**:
```json
POST /api/query
{
  "question": "Como funciona o sistema?",
  "enable_adaptive": true
}
```

**Resposta com Análise**:
```json
{
  "adaptive_params_used": {
    "applied": true,
    "complexity_score": 3,
    "top_k": 12,
    "min_similarity": 0.55,
    "adjustment_reason": "Simple query - expanding search scope"
  }
}
```

### 7. Context Compression
Reduz tamanho do contexto:
- Threshold: 3000 tokens
- Método: LLM-based
- Preserva informações relevantes

### 8. Self-RAG (Reflexão)
Avalia e refina automaticamente respostas incompletas:
- Avaliação de qualidade (score 0-100)
- Refinamento automático com Query Expansion
- Métricas detalhadas (iterations, initial_score, final_score, was_refined)
- Configurável via `ENABLE_SELF_RAG`, `SELF_RAG_MIN_SCORE`, `SELF_RAG_MAX_ITERATIONS`
- Integração transparente em `/api/query` e `/api/chat`

### 9. Cache de Embeddings
Cache LRU para embeddings:
- Max size: 1000
- Hit rate esperado: 30-50%
- Reduz latência drasticamente

### 10. Classificador de Perguntas
Identifica tipo de pergunta:
- Types: definition, comparison, procedure, troubleshooting, etc.
- Permite prompts específicos por tipo
- Melhora precisão

### 11. Processamento Avançado de Batches
Processamento paralelo de múltiplos batches simultâneos:
- **Workers paralelos**: 4 workers por padrão (configurável)
- **Speedup**: 2.5x mais rápido que processamento sequencial
- **Throughput**: ~50 embeddings/segundo
- **Utilização de GPU**: Maximiza capacidade de processamento
- **Configurável**: Desativável via `ENABLE_ADVANCED_BATCH_PROCESSING`
- **Estatísticas**: API para monitorar throughput e error rate

### 12. Testes Automatizados
Suíte completa de testes para Adaptive Retrieval:
- **48 testes unitários**: Cobertura completa de funcionalidades
- **Categorias**: Cálculo de complexidade, ajuste de parâmetros, validação de limites, integração, casos de borda
- **Execução**: `pytest tests/test_adaptive_retrieval.py -v`
- **Documentação**: Testes com docstrings explicativas

### 13. Sentence Window Retrieval
Busca precisa usando sentenças individuais com expansão dinâmica:
- **3 Modos de Recuperação**:
  - **Automático**: Sistema analisa a pergunta e escolhe a melhor estratégia (hierárquico ou sentence window)
  - **Explicação (Hierarchical)**: Contexto amplo com chunks grandes, ideal para tutoriais e documentação
  - **Precisão (Sentence Window)**: Chunks pequenos (1 sentença) com janela expandida, ideal para perguntas específicas de fatos
- **Ingestão Seletiva**: Tipo de chunking selecionável por documento (Hierarchical vs Sentence Window)
- **Expansão Dinâmica**: 3 sentenças vizinhas (antes e depois) para contexto suficiente
- **Heurísticas de Decisão**: Sistema analisa pergunta para escolher estratégia automaticamente:
  - Perguntas curtas (≤5 palavras) → Precisão
  - Perguntas "qual é", "quanto custa", "onde fica" → Precisão
  - Perguntas "como funciona", "por que", "explique" → Explicação
- **Benefícios**:
  - Melhor recall para perguntas específicas
  - Respostas mais diretas e precisas
  - Menos ruído nos embeddings
  - Contexto mais adequado ao tipo de pergunta
- **Configurável**: `SENTENCE_WINDOW_SIZE` (default: 3)
- **Dependências**: spaCy + modelo `pt_core_news_sm`
- **Documentação Detalhada**: `docs/melhorias_feitas/IMPLEMENTACAO_SENTENCE_WINDOW.md`

**Exemplo de Uso**:
```json
POST /api/query
{
  "question": "Qual o preço do produto?",
  "search_mode": "automatic"  // "hierarchical", "sentence", ou "automatic"
}
```

**Resposta com Modo Usado**:
```json
{
  "answer": "...",
  "search_mode_used": "sentence",
  "retrieval_strategy": "Precisão (Sentence Window) - 7 chunks expandidos"
}
```

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

# Métricas de Adaptive Retrieval
curl http://localhost:5000/api/metrics/adaptive-retrieval/stats?days=7
curl http://localhost:5000/api/metrics/adaptive-retrieval/recent?limit=50
curl http://localhost:5000/api/metrics/adaptive-retrieval/performance?days=7
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

**adaptive_retrieval_metrics**:
- Métricas de adaptive retrieval
- Complexidade de queries
- Ajustes de parâmetros aplicados
- Performance e timing

**question_type_instructions**:
- Instruções especializadas para cada tipo de pergunta
- Exemplos few-shot para guiar o modelo
- 7 tipos suportados: definition, comparison, listing, procedure, factual, reason, general
- Cache em memória (TTL 5 minutos) para otimizar performance
- Fallback para instruções hardcoded se BD indisponível
- Gerenciamento via SQL (sem frontend por enquanto)

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
pytest tests/test_adaptive_retrieval.py -v
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

O sistema utiliza o módulo padrão de logging do Python configurado via `dictConfig`.

**Formato de Log:**
```
2026-01-03 12:30:45 INFO flask.app Iniciando processamento do pedido 9988
2026-01-03 12:30:45 ERROR rag.llm Erro fatal ao processar requisição LLM
Traceback (most recent call last):
  File "src/core/llm.py", line 80, in generate_response
    response.raise_for_status()
requests.exceptions.HTTPError: 502 Server Error
```

**Níveis de Log:**
- **DEBUG**: Detalhes de execução (queries SQL, embedding vectors)
- **INFO**: Eventos importantes (API requests, LLM calls, document ingestion)
- **WARNING**: Situações anormais não-críticas
- **ERROR**: Erros que requerem atenção

**Arquivos de Log:**
- `logs/flask_app.log`: Log principal com rotação automática (10MB, 3 backups)

**Configuração:**
```python
# src/config.py
LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE: str = "logs/flask_app.log"
LOG_MAX_BYTES: int = 10485760  # 10MB
LOG_BACKUP_COUNT: int = 3
```

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `CHUNK_SIZE` | `800` | Tamanho máximo do chunk |
| `MIN_CHUNK_SIZE` | `200` | Tamanho mínimo do chunk |
| `USE_SEMANTIC_CHUNKING` | `True` | Usar chunking por sentenças |
| `CHUNK_OVERLAP_SENTENCES` | `1` | Sentenças de overlap |

# Obter logger para o módulo
logger = logging.getLogger(__name__)

# Log de informação
logger.info("Mensagem informativa")

# Log com variáveis (lazy formatting)
order_id = 9988
logger.info("Iniciando processamento do pedido %s", order_id)

# Log de erro com stacktrace
try:
    resultado = 1 / 0
except Exception:
    logger.exception("Erro fatal ao processar pagamento do pedido %s", order_id)
```

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

---

## 📝 Melhorias Futuras

Ver documento completo em `docs/MELHORIAS_COMPLETAS.md`

### Próximas Prioridades

- [ ] **Sistema de autenticação**: API Key ou JWT
- [ ] **Distributed tracing**: OpenTelemetry/Jaeger
- [ ] **Sistema de filas**: Celery ou RQ
- [ ] **Exportação de conversas**: JSON, Markdown, TXT
- [ ] **Sugestões de perguntas**: Baseadas em documentos
- [ ] **Multi-query**: Busca com múltiplas variações
- [ ] **Temporal re-ranking**: Priorizar documentos recentes

---

## 🤝 Contribuindo

# Iniciar API
python -m src.app

# Testar qualidade do chunking
python tests/test_chunking_comparison.py
```

---

## 📄 Licença

- [x] ✅ Filtro de similaridade mínima
- [x] ✅ Chunking semântico com spaCy
- [x] ✅ Suporte a múltiplos formatos (PDF, DOCX, TXT, MD, HTML)
- [x] ✅ Histórico de conversas
- [x] ✅ Endpoint de ingestão via API
- [x] ✅ **Busca Híbrida** - Combina busca vetorial (pgvector) com Full-Text Search (BM25)
- [x] ✅ **Compressão de Contexto** - Reduz contexto grande antes de enviar ao LLM
- [x] ✅ **Sistema de Logging** - Logs detalhados para API, RAG e ingestão
- [x] ✅ **Testes Automatizados** - Validação de funcionalidades do chunking

---

- [ ] Re-ranking com cross-encoder
- [ ] Cache de embeddings
- [ ] Métricas e monitoramento
- [ ] Interface de chat (frontend)
- [ ] Autenticação na API
- [ ] Expansão da suíte de testes

- **Issues**: GitHub Issues
- **Documentação**: Ver pasta `docs/`
- **Exemplos**: `docs/MELHORIAS.md`
- **Sistema de Avaliação RAG**: Documentação completa em `docs/SISTEMA_AVALIACAO_QUALIDADE.md`
  - Métricas de qualidade (fidelidade, relevância, precisão do contexto)
  - Avaliação manual e automática
  - Dashboard administrativo
  - Exemplos de uso da API
  - **Implementação de Adaptive Retrieval**: `docs/melhorias_feitas/IMPLEMENTACAO_ADAPTIVE_RETRIEVAL.md`
- **Implementação de Sentence Window Retrieval**: `docs/melhorias_feitas/IMPLEMENTACAO_SENTENCE_WINDOW.md`

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

## 🚀 Evolução Futura: LangChain e sglang

O projeto possui documentação para evolução futura com tecnologias avançadas:

### LangChain
- Blocos prontos para loaders, splitters, embeddings e retrievers
- Observabilidade com callbacks/tracing
- Composição de chains/runnables para flexibilidade

### sglang
- Servidor de inferência otimizado com batching e speculative decoding
- Redução de latência e custo
- Cache KV para melhor performance

Para mais detalhes sobre o plano de migração, consulte [docs/EVOLUCAO_LANGCHAIN_SGLANG.md](docs/EVOLUCAO_LANGCHAIN_SGLANG.md).

---

## 📄 Licença

Projeto pessoal para estudo e uso local.
