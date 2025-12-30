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
| **Ingestão** | Microsoft MarkItDown | 0.0.1+ | Conversão universal para Markdown |
| **Segurança** | cryptography | 41.0+ | Criptografia em repouso (AES-128) |
| **Segurança** | Restrictive CORS | - | Proteção contra origens não autorizadas |
| **Segurança** | Flask-Limiter | 3.5+ | Rate limiting e proteção contra abuso |
| **Dependências** | pip-tools | 7.4+ | Pinning e gestão de dependências |
| **Arquitetura** | Repository Pattern | - | Desacoplamento da camada de dados |
| **Arquitetura** | Modular RAG | - | Pipeline, Services e Retrieval Strategies |

---

## ✨ Funcionalidades Principais

### 📄 Ingestão de Documentos
- **Extração Unificada (MarkItDown)**: Todos os documentos são convertidos para Markdown estruturado antes do processamento, preservando tabelas e títulos.
- **Múltiplos formatos**: PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, CSV.
- **Processamento em background**: Upload assíncrono com status tracking.
- **Ingestão em massa**: Processamento de múltiplos documentos simultaneamente.
- **Processamento Paralelo de Embeddings**: Batches processados simultaneamente para máxima performance (2.5x mais rápido).
- **Detecção de alterações**: Re-ingestão automática de arquivos modificados via Hash SHA-256.
- **Estatísticas detalhadas**: Contagem de chunks, tamanho de arquivos e métricas de conversão.
- **Nota sobre Multimodalidade**: Atualmente, formatos de **imagem** e **áudio** estão desabilitados, pois requerem chaves de API externas para processamento via MarkItDown.

### 🔍 Busca e Recuperação Avançada
- **Busca Híbrida**: Combina busca vetorial (semântica) + Full-Text Search (palavras-chave)
- **Re-ranking com Cross-Encoder**: Refina resultados usando modelo especializado
- **Query Expansion**: Gera variações da pergunta para busca mais abrangente (3 variações por padrão, fundidas com RRF)
- **HyDE (Hypothetical Document Embeddings)**: Gera documento hipotético para melhorar busca
- **MMR (Maximal Marginal Relevance)**: Diversifica resultados para evitar redundância
- **Adaptive Retrieval**: Ajusta parâmetros dinamicamente baseado na complexidade da query
- **Filtro de similaridade**: Descarta resultados irrelevantes automaticamente
- **Arquitetura Modular**: Pipeline orquestrada com serviços especializados (Search, Context, Prompt, Response)

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

### 🔒 Segurança e Criptografia
- **Criptografia em Repouso**: Dados sensíveis criptografados no banco (AES-128 + HMAC-SHA256)
- **Criptografia em Trânsito**: HTTPS/TLS1.3 com headers de segurança
- **Headers de Segurança**: HSTS, CSP, X-Frame-Options, etc.
- **Campos Criptografados**: conteúdo de documentos, metadados, comentários de feedback
- **Criptografia Condicional**: Habilitável/desabilitável por campo
- **Geração de Chaves Seguras**: Script dedicado para gerenciar chaves
- **Restrictive CORS**: Configuração rigorosa de origens permitidas via `ALLOWED_ORIGINS` e `CORS_MAX_AGE`.
- **API Rate Limiting**: Proteção global e por endpoint contra abusos e DoS (Flask-Limiter).
- **Compliance**: Auxilia no cumprimento de LGPD (Art. 46) e ISO 27001

### 🔬 Observabilidade e Monitoramento
- **Métricas Prometheus**: Métricas nativas em cada fase do RAG
- **Modo Debug/Explain**: Transparência total no pipeline (timing, scores, HyDE)
- **Logging estruturado**: Logs detalhados para debugging
- **Estátisticas de cache**: Hit rate, tamanho, performance

### 🔍 Explicação Detalhada de Fontes
- **Timeline completa do processo RAG**: Visualização de todas as etapas do pipeline
- **Explicação de técnicas usadas**: HyDE, busca híbrida, re-ranking, MMR
- **Detalhes de seleção de chunks**: Como e por quais chunks foram selecionados
- **Métricas de similaridade**: Scores de similaridade para cada etapa
- **Interface visual interativa**: Modal com timeline, cards expansíveis e ícones
- **Ativação via toggle**: Botão (✨) no header para ativar/desativar funcionalidade
- **Transparência para usuários**: Entendam como o sistema chegou a determinada resposta
- **Baixo overhead**: ~50-100ms adicionais por query no backend

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
- **Adaptive Retrieval Metrics**: Dashboard de métricas de adaptive retrieval
  - Estatísticas agregadas (total queries, complexidade média, etc.)
  - Distribuição de complexidade (Simple/Medium/Complex)
  - Tabela de queries recentes com ajustes aplicados
  - Gráfico de barras de distribuição
  - Filtro por período (24h, 7 dias, 30 dias)

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
│   │   │   ├── ExplanationModal.tsx  # Modal de explicação RAG
│   │   │   └── ...                   # Outros componentes
│   │   └── types.ts              # TypeScript types
│   ├── package.json
│   └── vite.config.ts
├── src/                           # Backend Python
│   ├── api/                       # Camada API
│   │   ├── routes/                # Blueprints modulares (prompts, docs, chat, etc.)
│   │   └── schemas.py             # Schemas Pydantic
│   ├── core/                      # Lógica RAG e NLP
│   │   ├── rag/                   # Nova arquitetura RAG Modular
│   │   │   ├── services/          # Serviços (Search, Context, Prompt, Response)
│   │   │   ├── strategies/        # Estratégias (Retrieval, HyDE, etc.)
│   │   │   └── pipeline.py        # Orquestrador principal (RAGPipeline)
│   │   ├── rag.py                 # Wrapper de compatibilidade
│   │   └── ...                    # Módulos core (llm, embeddings, etc.)
│   ├── data/                      # Camada de dados
│   │   ├── repositories/          # Repository Pattern (Document, Prompt, etc.)
│   │   ├── database.py            # Conexão base
│   │   ├── ingestion.py           # Processamento de arquivos
│   │   └── ...                    # Módulos de busca e chunking
│   ├── app.py                     # Inicialização Flask (Limiter, Blueprints)
│   └── config.py                  # Configurações centralizadas
├── requirements/                  # Definições de dependências (pip-tools)
│   ├── base.in                    # Dependências base
│   └── dev.in                     # Dependências de desenvolvimento
├── requirements.txt               # Pinned dependencies (Base)
├── requirements-dev.txt           # Pinned dependencies (Dev)
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
- Modelo: `cross-encoder/ms-marco-MiniLM-L-6-v2`
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
- ✅ Adaptive Retrieval dinâmico

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
- **Implementação de Adaptive Retrieval**: `docs/melhorias_feitas/IMPLEMENTACAO_ADAPTIVE_RETRIEVAL.md`

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
**Versão**: 2.1
