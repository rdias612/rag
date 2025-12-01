# RAG System - Sistema de Recuperação e Geração Aumentada

Sistema RAG (Retrieval-Augmented Generation) local para consulta inteligente de documentos PDF.

## 🚀 Tecnologias Utilizadas

| Componente | Tecnologia | Descrição |
|------------|------------|-----------|
| **Banco de Dados** | PostgreSQL + pgvector | Armazenamento e busca vetorial |
| **Embeddings** | Nomic Embed v1.5 | Modelo de embeddings via LM Studio |
| **LLM** | Phi-3.5 Mini | Geração de respostas via LM Studio |
| **API** | Flask | Backend REST API |
| **Ingestão** | pypdf | Extração de texto de PDFs |

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
│   │   └── rag.py            # Pipeline RAG completo
│   ├── data/
│   │   ├── database.py       # Conexão PostgreSQL + pgvector
│   │   └── ingestion.py      # Leitura de PDFs + chunking
│   ├── app.py                # Aplicação Flask principal
│   └── config.py             # Configurações centralizadas
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

### Ingerir Documentos

```bash
python -m scripts.ingest
```

Este comando irá:
1. Ler todos os PDFs do diretório configurado
2. Dividir em chunks (800 caracteres, 150 overlap)
3. Gerar embeddings via LM Studio
4. Armazenar no PostgreSQL com pgvector

### Iniciar a API

```bash
python -m src.app
```

A API estará disponível em `http://localhost:5000`

---

## 📡 API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Informações da API |
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Estatísticas (contagem de documentos) |
| `/api/query` | POST | **Query RAG principal** |
| `/api/query/stream` | POST | Query com streaming |
| `/api/search` | POST | Apenas busca semântica (sem LLM) |

### Exemplo de Query

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is GWPRP?"}'
```

**Resposta:**
```json
{
  "answer": "GWPRP é um protocolo de roteamento...",
  "chunks_retrieved": 5,
  "sources": [
    {"source": "documento.pdf", "page": 1, "similarity": 0.85}
  ]
}
```

### Parâmetros Opcionais

```json
{
  "question": "Sua pergunta",
  "top_k": 5,              // Número de chunks (padrão: 5)
  "temperature": 0.7,      // Criatividade (padrão: 0.7)
  "include_sources": true  // Incluir fontes (padrão: true)
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
                                                ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Resposta  │◀────│   Phi-3.5    │◀────│  Contexto   │
│             │     │    Mini      │     │  (top k)    │
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
| `DOCUMENTS_DIR` | `C:\Users\Rian\Documents\treinamento` | Diretório dos PDFs |
| `DATABASE_PORT` | `5433` | Porta do PostgreSQL |
| `LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | URL do LM Studio |
| `EMBEDDING_DIMENSION` | `768` | Dimensão do Nomic Embed |
| `CHUNK_SIZE` | `800` | Tamanho do chunk (caracteres) |
| `CHUNK_OVERLAP` | `150` | Sobreposição entre chunks |
| `TOP_K_RESULTS` | `5` | Chunks retornados na busca |

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

## 📝 TODO / Próximos Passos

- [ ] Interface de chat (frontend)
- [ ] Suporte a outros formatos (.docx, .md, .txt)
- [ ] Histórico de conversas
- [ ] Autenticação na API
- [ ] Cache de embeddings
- [ ] Métricas e logs
- [ ] Testes automatizados

---

## 📄 Licença

Projeto pessoal para estudo e uso local.