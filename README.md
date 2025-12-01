# RAG System - Sistema de Recuperação e Geração Aumentada

Sistema RAG (Retrieval-Augmented Generation) local para consulta inteligente de documentos com suporte a múltiplos formatos, histórico de conversas e ingestão via API.

## 🚀 Tecnologias Utilizadas

| Componente | Tecnologia | Descrição |
|------------|------------|-----------|
| **Banco de Dados** | PostgreSQL + pgvector | Armazenamento e busca vetorial |
| **Embeddings** | Nomic Embed v1.5 | Modelo de embeddings via LM Studio |
| **LLM** | Phi-3.5 Mini | Geração de respostas via LM Studio |
| **API** | Flask | Backend REST API |
| **NLP** | spaCy | Chunking semântico por sentenças |
| **Ingestão** | pypdf, python-docx, beautifulsoup4 | Extração de múltiplos formatos |

---

## ✨ Funcionalidades

- 📄 **Múltiplos formatos**: PDF, DOCX, TXT, Markdown, HTML
- 🔍 **Filtro de similaridade**: Descarta resultados irrelevantes automaticamente
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
├── src/
│   ├── api/
│   │   └── routes.py         # Endpoints da API
│   ├── core/
│   │   ├── embeddings.py     # Geração de embeddings (Nomic)
│   │   ├── llm.py            # Integração com LLM (Phi-3.5)
│   │   ├── rag.py            # Pipeline RAG completo
│   │   ├── conversation.py   # Gerenciador de histórico de conversas
│   │   └── logger.py         # Sistema de logging
│   ├── data/
│   │   ├── database.py       # Conexão PostgreSQL + pgvector
│   │   ├── ingestion.py      # Leitura de documentos + chunking
│   │   └── chunking.py       # Chunking semântico com spaCy
│   ├── app.py                # Aplicação Flask principal
│   └── config.py             # Configurações centralizadas
├── docs/
│   └── MELHORIAS.md          # Roadmap de melhorias
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
```

Isso irá iniciar:
- **PostgreSQL + pgvector** na porta `5433`
- **Adminer** (interface web) na porta `8080`

### 2. Instalar Dependências

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt

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

Este comando irá:
1. Ler todos os documentos suportados (PDF, DOCX, TXT, MD, HTML)
2. Dividir em chunks usando chunking semântico
3. Gerar embeddings via LM Studio
4. Armazenar no PostgreSQL com pgvector

### Iniciar a API

```bash
python -m src.app
```

A API estará disponível em `http://localhost:5000`

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
  "include_sources": true
}
```

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `question` | string | ✅ | A pergunta a ser respondida |
| `top_k` | int | ❌ | Número de chunks a recuperar (padrão: 5) |
| `temperature` | float | ❌ | Criatividade do LLM, 0.0-1.0 (padrão: 0.7) |
| `include_sources` | bool | ❌ | Incluir fontes na resposta (padrão: true) |

**Response:**
```json
{
  "answer": "GWPRP é um protocolo de roteamento...",
  "chunks_retrieved": 5,
  "context_used": "...",
  "sources": [
    {"source": "documento.pdf", "page": 1, "similarity": 0.85}
  ]
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
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Pergunta  │────▶│  Embedding   │────▶│   pgvector  │
│             │     │ (Nomic v1.5) │     │   (busca)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                         ┌──────▼──────┐
                                         │   Filtro    │
                                         │ Similaridade│
                                         │   (≥ 0.5)   │
                                         └──────┬──────┘
                                                │
┌─────────────┐     ┌──────────────┐     ┌──────▼──────┐
│   Resposta  │◀────│   Phi-3.5    │◀────│  Contexto   │
│             │     │    Mini      │     │  + Histórico│
└─────────────┘     └──────────────┘     └─────────────┘
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Índice Vetorial

```sql
CREATE INDEX idx_documentos_embedding 
ON documentos 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
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

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DOCUMENTS_DIR` | `C:\Users\...\treinamento` | Diretório dos documentos |
| `DATABASE_PORT` | `5433` | Porta do PostgreSQL |
| `LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | URL do LM Studio |
| `EMBEDDING_DIMENSION` | `768` | Dimensão do Nomic Embed |
| `CHUNK_SIZE` | `800` | Tamanho máximo do chunk |
| `MIN_CHUNK_SIZE` | `200` | Tamanho mínimo do chunk |
| `TOP_K_RESULTS` | `5` | Chunks retornados na busca |
| `MIN_SIMILARITY_THRESHOLD` | `0.5` | Similaridade mínima (0.0-1.0) |
| `USE_SEMANTIC_CHUNKING` | `True` | Usar chunking por sentenças |
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

- [x] ✅ Filtro de similaridade mínima
- [x] ✅ Chunking semântico com spaCy
- [x] ✅ Suporte a múltiplos formatos (PDF, DOCX, TXT, MD, HTML)
- [x] ✅ Histórico de conversas
- [x] ✅ Endpoint de ingestão via API

### Próximos Passos

- [ ] Re-ranking com cross-encoder
- [ ] Cache de embeddings
- [ ] Métricas e monitoramento
- [ ] Interface de chat (frontend)
- [ ] Autenticação na API
- [ ] Testes automatizados

Veja o roadmap completo em [docs/MELHORIAS.md](docs/MELHORIAS.md).

---

## 📄 Licença

Projeto pessoal para estudo e uso local.