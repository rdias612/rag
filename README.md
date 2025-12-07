# RAG System - Sistema de Recuperação e Geração Aumentada

Sistema RAG (Retrieval-Augmented Generation) local para consulta inteligente de documentos com suporte a múltiplos formatos, histórico de conversas e ingestão via API.

## 🚀 Tecnologias Utilizadas

| Componente | Tecnologia | Descrição |
|------------|------------|-----------|
| **Banco de Dados** | PostgreSQL + pgvector | Armazenamento e busca vetorial |
| **Embeddings** | Nomic Embed v1.5 | Modelo de embeddings via LM Studio |
| **LLM** | Phi-3.5 Mini | Geração de respostas via LM Studio |
| **API** | Flask | Backend REST API |
| **Frontend** | React + Vite | Interface moderna e responsiva |
| **Estilização** | Tailwind CSS | Design system e componentes |
| **NLP** | spaCy | Chunking semântico por sentenças |
| **Ingestão** | pypdf, python-docx, beautifulsoup4 | Extração de múltiplos formatos |

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

---

## 📁 Estrutura do Projeto

```
rag/
├── db/
│   ├── docker-compose.yml    # PostgreSQL + pgvector + Adminer
│   └── init.sql              # Script de inicialização do banco
├── scripts/
│   └── ingest.py             # CLI para ingestão de documentos
├── frontend/                 # Interface Web (React)
│   ├── src/
│   │   ├── components/       # Componentes UI (Chat, Upload, etc)
│   │   ├── hooks/            # Hooks customizados
│   │   └── api.ts            # Cliente da API
│   └── vite.config.ts        # Configuração do Vite
├── src/
│   ├── api/
│   │   └── routes.py         # Endpoints da API
│   ├── core/
│   │   ├── embeddings.py     # Geração de embeddings (Nomic)
│   │   ├── llm.py            # Integração com LLM (Phi-3.5)
│   │   ├── rag.py            # Pipeline RAG completo
│   │   ├── conversation.py   # Gerenciador de histórico de conversas
│   │   ├── context_compression.py  # Compressão inteligente de contexto
│   │   ├── logger.py         # Sistema de logging
│   │   ├── embedding_cache.py     # Cache LRU de embeddings (Phase 1)
│   │   ├── question_classifier.py # Classificador de perguntas (Phase 1)
│   │   ├── reranker.py       # Re-ranking com Cross-Encoder (Phase 2)
│   │   ├── query_expansion.py # Expansão de queries (Phase 2)
│   │   ├── mmr.py            # Diversificação MMR (Phase 2)
│   │   ├── hyde.py           # Hypothetical Document Embeddings (Phase 3)
│   │   ├── evaluation.py     # Métricas RAGAS (Phase 3)
│   │   ├── adaptive_retrieval.py  # Parâmetros adaptativos (Phase 4)
│   │   └── self_rag.py       # Auto-reflexão de respostas (Phase 4)
│   ├── data/
│   │   ├── database.py       # Conexão PostgreSQL + pgvector
│   │   ├── hybrid_search.py  # Busca híbrida (vetorial + FTS)
│   │   ├── ingestion.py      # Leitura de documentos + chunking
│   │   ├── chunking.py       # Chunking semântico com spaCy
│   │   ├── hierarchical_chunking.py  # Parent-Child chunks (Phase 3)
│   │   └── sentence_window.py # Busca por janela de sentenças (Phase 4)
│   ├── app.py                # Aplicação Flask principal
│   └── config.py             # Configurações centralizadas
├── docs/
│   ├── MELHORIAS.md          # Roadmap de melhorias
│   ├── SUGESTOES_MELHORIAS.md    # Sugestões detalhadas v1
│   └── SUGESTOES_MELHORIAS_V2.md # Sugestões detalhadas v2
├── requirements.txt
└── README.md
```

---

## ⚙️ Configuração

### Pré-requisitos

1. **Python 3.11+**
2. **Docker** (para PostgreSQL)
3. **LM Studio** rodando com:
   - Modelo de embeddings: `text-embedding-nomic-embed-text-v1.5`
   - Modelo LLM: `phi-3.5-mini-instruct`

### 1. Subir o Banco de Dados

```bash
cd db
docker-compose up -d
### 2. Instalar Dependências

#### Backend (Python)
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Baixar modelo spaCy para português
python -m spacy download pt_core_news_sm
### 3. Configurar LM Studio

3. Iniciar o servidor local (padrão: `http://127.0.0.1:1234`)

### 4. Aplicar Migrações do Banco (Alembic)

Em um terminal (na raiz do projeto):

```bash
alembic upgrade head
```

Isso cria a tabela `documentos`, índices vetoriais e a coluna `collection_id`.
```

#### Frontend (Node.js)
```bash
cd frontend
npm install
```

### 3. Configurar LM Studio.txt

# Baixar modelo spaCy para português
python -m spacy download pt_core_news_sm
```

### 3. Configurar LM Studio

1. Abrir o LM Studio
2. Carregar os modelos:
   - `text-embedding-nomic-embed-text-v1.5` (embeddings)
   - `phi-3.5-mini-instruct` (LLM)
3. Iniciar o servidor local (padrão: `http://127.0.0.1:1234`)

### 4. Configurar Diretório de Documentos

Edite `src/config.py` e ajuste o caminho dos documentos:

```python
DOCUMENTS_DIR = Path(r"C:\caminho\para\seus\documentos")
```

---

## 🔧 Uso

### Verificar Serviços

```bash
python -m scripts.ingest --check
```

### Ver Estatísticas

```bash
python -m scripts.ingest --stats
```

### Ingerir Documentos via CLI

```bash
python -m scripts.ingest
```
### Iniciar a API

```bash
python -m src.app
```

A API estará disponível em `http://localhost:5000`

### Iniciar o Frontend

Em outro terminal:

```bash
cd frontend
npm run dev
```

A interface estará disponível em `http://localhost:5173`

---

## 🔍 Busca Híbrida
```

A API estará disponível em `http://localhost:5000`

---

## 🔍 Busca Híbrida

O sistema combina dois tipos de busca para melhores resultados:

| Tipo | Tecnologia | Força |
|------|------------|-------|
| **Vetorial** | pgvector (cosine similarity) | Encontra conteúdo semanticamente similar |
| **Full-Text Search** | PostgreSQL tsvector + GIN | Encontra termos exatos, siglas, nomes |

### Reciprocal Rank Fusion (RRF)

Os resultados são combinados usando RRF:

```
Score_final = α × RRF_vetorial + (1-α) × RRF_FTS
```

Onde `α` (alpha) controla o peso de cada busca:
- `α = 1.0` → 100% vetorial (ignora FTS)
- `α = 0.7` → 70% vetorial, 30% FTS (padrão)
- `α = 0.5` → 50% cada
- `α = 0.0` → 100% FTS (ignora vetorial)

### Quando usar cada configuração

| Cenário | Alpha Recomendado |
|---------|-------------------|
| Perguntas conceituais | 0.8 - 1.0 |
| Busca por siglas/códigos | 0.3 - 0.5 |
| Uso geral | 0.7 (padrão) |

---

## 🗜️ Compressão de Contexto

Quando o contexto recuperado é muito grande (> 3000 chars por padrão), o sistema automaticamente o comprime antes de enviar ao LLM.

### Métodos de Compressão

| Método | Descrição | Quando usar |
|--------|-----------|-------------|
| `llm` | Usa o LLM para resumir mantendo informações relevantes | Mais preciso, recomendado |
| `heuristic` | Extrai sentenças mais relevantes usando sobreposição de palavras | Mais rápido, sem custo extra |

### Benefícios

- ⚡ Reduz tokens enviados ao LLM
- 💰 Menor custo de processamento
- 🎯 Foco nas informações relevantes para a pergunta

---

## 📡 API Endpoints

### Visão Geral

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Informações da API |
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Estatísticas do sistema |
| `/api/query` | POST | Query RAG principal |
| `/api/query/stream` | POST | Query com streaming |
| `/api/search` | POST | Busca semântica (sem LLM) |
| `/api/chat` | POST | Query com histórico de conversa |
| `/api/chat/sessions` | GET | Listar sessões ativas |
| `/api/chat/sessions/<id>` | GET | Obter histórico da sessão |
| `/api/chat/sessions/<id>` | DELETE | Remover sessão |
| `/api/chat/new` | POST | Criar nova sessão |
| `/api/ingest` | POST | Upload de documento |
| `/api/ingest/status/<job_id>` | GET | Status do processamento |
| `/api/ingest/jobs` | GET | Listar jobs de ingestão |
| `/api/ingest/formats` | GET | Formatos suportados |
| `/api/documents/stats` | GET | Estatísticas dos documentos |

---

## 🔎 Endpoints de Query

### `POST /api/query` - Query RAG Principal

Envia uma pergunta e recebe uma resposta baseada nos documentos indexados.

**Request:**
```json
{
  "question": "O que é GWPRP?",
  "top_k": 5,
  "temperature": 0.7,
  "include_sources": true,
  "use_hybrid_search": true,
  "hybrid_alpha": 0.7,
  "enable_compression": true
}
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `question` | string | ✅ | A pergunta a ser respondida |
| `top_k` | int | ❌ | Número de chunks a recuperar (padrão: 5) |
| `temperature` | float | ❌ | Criatividade do LLM, 0.0-1.0 (padrão: 0.7) |
| `include_sources` | bool | ❌ | Incluir fontes na resposta (padrão: true) |
| `use_hybrid_search` | bool | ❌ | Usar busca híbrida vetorial+FTS (padrão: config) |
| `hybrid_alpha` | float | ❌ | Peso da busca vetorial, 0.0-1.0 (padrão: 0.7) |
| `enable_compression` | bool | ❌ | Comprimir contexto grande (padrão: config) |

**Response:**
```json
{
  "answer": "GWPRP é um protocolo de roteamento...",
  "chunks_retrieved": 5,
  "context_used": "...",
  "sources": [
    {"source": "documento.pdf", "page": 1, "similarity": 0.85, "hybrid_score": 0.012}
  ],
  "search": {
    "search_type": "hybrid",
    "hybrid_alpha": 0.7,
    "vector_results": 4,
    "fts_results": 3
  },
  "compression": {
    "was_compressed": true,
    "original_size": 4500,
    "final_size": 2100,
    "compression_ratio": 53.3,
    "compression_time_ms": 1200
  }
}
```

### `POST /api/query/stream` - Query com Streaming

Mesmos parâmetros do `/api/query`, mas retorna a resposta em streaming (token por token).

```bash
curl -X POST http://localhost:5000/api/query/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "O que é GWPRP?"}'
```

### `POST /api/search` - Busca Semântica

Retorna apenas os chunks mais similares, sem gerar resposta do LLM. Útil para debug.

**Request:**
```json
{
  "question": "protocolo de roteamento",
  "top_k": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "content": "Texto do chunk...",
      "source": "documento.pdf",
      "page": 5,
      "similarity": 0.89
    }
  ],
  "count": 10
}
```

---

## 💬 Endpoints de Conversa (Histórico)

Permitem manter contexto entre perguntas de follow-up.

### `POST /api/chat` - Query com Histórico

Funciona como `/api/query`, mas mantém o histórico da conversa para entender referências como "ele", "isso", "o mesmo".

**Request (primeira pergunta):**
```json
{
  "question": "O que é GWPRP?"
}
```

**Response:**
```json
{
  "answer": "GWPRP é um protocolo de roteamento...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_count": 2,
  "sources": [...]
}
```

**Request (follow-up usando o session_id):**
```json
{
  "question": "Quem desenvolveu?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

O sistema entende que "Quem desenvolveu?" refere-se ao GWPRP mencionado anteriormente.

### `GET /api/chat/sessions` - Listar Sessões

Lista todas as sessões de conversa ativas.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-...",
      "message_count": 4,
      "created_at": "2025-11-30T10:00:00",
      "last_activity": "2025-11-30T10:05:00"
    }
  ],
  "count": 1
}
```

### `GET /api/chat/sessions/<session_id>` - Histórico da Sessão

Retorna o histórico completo de mensagens de uma sessão.

**Response:**
```json
{
  "session_id": "550e8400-...",
  "messages": [
    {"role": "user", "content": "O que é GWPRP?", "timestamp": 1732968000},
    {"role": "assistant", "content": "GWPRP é...", "timestamp": 1732968005}
  ],
  "message_count": 4
}
```

### `DELETE /api/chat/sessions/<session_id>` - Remover Sessão

Remove uma sessão de conversa.

### `POST /api/chat/new` - Criar Nova Sessão

Cria uma sessão vazia para uso posterior.

---

## 📤 Endpoints de Ingestão

Permitem upload de documentos via API com processamento em background.

### `POST /api/ingest` - Upload de Documento

Envia um documento para ser processado e indexado.

**Request:**
```bash
curl -X POST http://localhost:5000/api/ingest \
  -F "file=@documento.pdf"
```

**Response:**
```json
{
  "job_id": "abc123-...",
  "filename": "documento.pdf",
  "status": "queued",
  "message": "Documento recebido, processamento iniciado"
}
```

O processamento é feito em background. Use o `job_id` para acompanhar o status.

### `GET /api/ingest/status/<job_id>` - Status do Processamento

Verifica o status de um job de ingestão.

**Response:**
```json
{
  "job_id": "abc123-...",
  "filename": "documento.pdf",
  "status": "completed",
  "chunks_created": 15,
  "chunks_inserted": 15,
  "message": "Sucesso! 15 chunks indexados.",
  "created_at": "2025-11-30T10:00:00",
  "completed_at": "2025-11-30T10:00:05"
}
```

**Status possíveis:**
- `queued` - Aguardando processamento
- `processing` - Em processamento
- `completed` - Finalizado com sucesso
- `failed` - Falhou (ver campo `error`)

### `GET /api/ingest/jobs` - Listar Jobs

Lista todos os jobs de ingestão.

**Query params:**
- `status` - Filtrar por status (queued, processing, completed, failed)

```bash
curl "http://localhost:5000/api/ingest/jobs?status=completed"
```

### `GET /api/ingest/formats` - Formatos Suportados

Retorna os formatos de arquivo aceitos para upload.

**Response:**
```json
{
  "formats": [".docx", ".html", ".htm", ".md", ".pdf", ".txt"],
  "description": {
    ".pdf": "Documento PDF",
    ".docx": "Microsoft Word",
    ".txt": "Texto plano",
    ".md": "Markdown",
    ".html": "HTML"
  }
}
```

### `GET /api/documents/stats` - Estatísticas

Retorna estatísticas sobre os documentos.

**Response:**
```json
{
  "total_files": 10,
  "files_by_type": {".pdf": 5, ".docx": 3, ".txt": 2},
  "total_pdf_pages": 150,
  "total_size_mb": 25.5,
  "indexed_chunks": 500,
  "documents_dir": "C:\\..."
}
```

---

## 🔄 Pipeline RAG

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│   Pergunta  │────▶│  Embedding   │────▶│      Busca Híbrida          │
│             │     │ (Nomic v1.5) │     │  ┌─────────┐ ┌───────────┐  │
└─────────────┘     └──────────────┘     │  │pgvector │ │Full-Text  │  │
                                         │  │(vetorial)│ │Search(FTS)│  │
                                         │  └────┬────┘ └─────┬─────┘  │
                                         │       └─────┬──────┘        │
                                         │         RRF Fusion          │
                                         └──────────┬──────────────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │   Filtro Similaridade│
                                         │       (≥ 0.5)        │
                                         └──────────┬──────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │    Compressão de    │
                                         │      Contexto       │
                                         │  (se > 3000 chars)  │
                                         └──────────┬──────────┘
                                                    │
┌─────────────┐     ┌──────────────┐     ┌──────────▼──────────┐
│   Resposta  │◀────│   Phi-3.5    │◀────│      Contexto       │
│             │     │    Mini      │     │    + Histórico      │
└─────────────┘     └──────────────┘     └─────────────────────┘
```

---

## 🗄️ Banco de Dados

### Tabela `documentos`

```sql
CREATE TABLE documentos (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(768),
    search_vector TSVECTOR,  -- Para Full-Text Search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Índices

```sql
-- Índice vetorial (busca semântica)
CREATE INDEX idx_documentos_embedding 
ON documentos 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Índice GIN (Full-Text Search)
CREATE INDEX idx_documentos_fts 
ON documentos 
USING gin(search_vector);
```

### Trigger Automático (FTS)

O campo `search_vector` é atualizado automaticamente via trigger:

```sql
CREATE TRIGGER trg_update_search_vector
BEFORE INSERT OR UPDATE ON documentos
FOR EACH ROW
EXECUTE FUNCTION update_search_vector();
```

### Acessar via Adminer

- URL: http://localhost:8080
- Sistema: PostgreSQL
- Servidor: db
- Usuário: postgres
- Senha: changeme
- Base de dados: ragdb

---

## ⚡ Configurações

Todas as configurações estão em `src/config.py`:

### Geral

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DOCUMENTS_DIR` | `C:\Users\...\treinamento` | Diretório dos documentos |
| `DATABASE_PORT` | `5433` | Porta do PostgreSQL |
| `LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | URL do LM Studio |
| `EMBEDDING_DIMENSION` | `768` | Dimensão do Nomic Embed |

### Chunking

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `CHUNK_SIZE` | `800` | Tamanho máximo do chunk |
| `MIN_CHUNK_SIZE` | `200` | Tamanho mínimo do chunk |
| `USE_SEMANTIC_CHUNKING` | `True` | Usar chunking por sentenças |

### RAG

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `TOP_K_RESULTS` | `5` | Chunks retornados na busca |
| `MIN_SIMILARITY_THRESHOLD` | `0.5` | Similaridade mínima (0.0-1.0) |

### Busca Híbrida

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ENABLE_HYBRID_SEARCH` | `True` | Habilitar busca vetorial + FTS |
| `HYBRID_SEARCH_ALPHA` | `0.7` | Peso vetorial (0.7 = 70% vetorial, 30% FTS) |

### Compressão de Contexto

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ENABLE_CONTEXT_COMPRESSION` | `True` | Comprimir contexto grande |
| `CONTEXT_COMPRESSION_THRESHOLD` | `3000` | Limite de chars para comprimir |
| `CONTEXT_COMPRESSION_TARGET_RATIO` | `0.5` | Alvo de redução (50%) |
| `CONTEXT_COMPRESSION_METHOD` | `"llm"` | Método: "llm" ou "heuristic" |

### Conversação

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SESSION_TIMEOUT_MINUTES` | `30` | Timeout de sessões de conversa |
| `MAX_CONVERSATION_HISTORY` | `10` | Máx mensagens no histórico |

---

## 📦 Formatos de Documentos Suportados

| Formato | Extensão | Biblioteca | Descrição |
|---------|----------|------------|-----------|
| PDF | `.pdf` | pypdf | Extrai texto página por página |
| Word | `.docx` | python-docx | Extrai parágrafos e tabelas |
| Texto | `.txt` | nativo | Leitura direta (UTF-8, Latin-1) |
| Markdown | `.md` | markdown + bs4 | Converte para HTML e extrai texto |
| HTML | `.html`, `.htm` | beautifulsoup4 | Remove scripts/styles e extrai texto |

---

## 🛠️ Comandos Úteis

```bash
# Verificar serviços
python -m scripts.ingest --check

# Ver estatísticas
python -m scripts.ingest --stats

# Processar documentos
python -m scripts.ingest

# Limpar banco (cuidado!)
python -m scripts.ingest --clear

# Iniciar API
python -m src.app
```

---

## 📝 Melhorias Implementadas

### Base
- [x] ✅ Filtro de similaridade mínima
- [x] ✅ Chunking semântico com spaCy
- [x] ✅ Suporte a múltiplos formatos (PDF, DOCX, TXT, MD, HTML)
- [x] ✅ Histórico de conversas
- [x] ✅ Endpoint de ingestão via API
- [x] ✅ **Busca Híbrida** - Combina busca vetorial (pgvector) com Full-Text Search
- [x] ✅ **Compressão de Contexto** - Reduz contexto grande antes de enviar ao LLM

### Phase 1 - Quick Wins
- [x] ✅ **Cache de Embeddings** - Cache LRU para evitar recálculos
- [x] ✅ **Classificador de Perguntas** - Detecta tipo de pergunta (definição, comparação, etc.)
- [x] ✅ **Prompts Melhorados** - Chain-of-Thought com instruções por tipo
- [x] ✅ **Fallback Inteligente** - Sugestões quando não há resultados

### Phase 2 - Core Improvements
- [x] ✅ **Re-ranking com Cross-Encoder** - Reordena chunks por relevância real
- [x] ✅ **Query Expansion** - Gera variações da pergunta para melhor recall
- [x] ✅ **MMR (Diversidade)** - Evita chunks redundantes

### Phase 3 - Advanced
- [x] ✅ **HyDE** - Hypothetical Document Embeddings para busca melhorada
- [x] ✅ **RAGAS Evaluation** - Métricas de qualidade (faithfulness, relevancy)
- [x] ✅ **Hierarchical Chunking** - Chunks parent-child
- [x] ✅ **Contextual Metadata** - Metadados enriquecidos (seção, vizinhos)

### Phase 4 - Final
- [x] ✅ **Adaptive Retrieval** - Ajuste dinâmico de top_k e min_similarity
- [x] ✅ **Self-RAG** - Auto-avaliação e refinamento de respostas
- [x] ✅ **Sentence Window** - Busca por sentença com janela expandida

### Próximas Sugestões (v2)
- [ ] Multi-tenancy (coleções separadas)
- [ ] Suporte multi-modal (imagens)
- [ ] Re-ingestão incremental
- [ ] Cache Redis (persistente)
- [ ] Fine-tuning de embeddings

Veja detalhes em [docs/SUGESTOES_MELHORIAS_V2.md](docs/SUGESTOES_MELHORIAS_V2.md).


---

## 🔧 Configuração Inicial da Busca Híbrida

Se você já tem documentos indexados e quer ativar a busca híbrida:

```python
# Execute uma vez para criar as estruturas de FTS
from src.data.hybrid_search import init_fulltext_search
init_fulltext_search()
```

Isso irá:
1. Adicionar a coluna `search_vector` na tabela
2. Criar o índice GIN para Full-Text Search
3. Atualizar os documentos existentes
4. Criar trigger para atualização automática

---

## 📄 Licença

Projeto pessoal para estudo e uso local.