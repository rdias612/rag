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
| **NLP** | spaCy + langdetect | Chunking semântico e detecção de idioma |
| **Monitoramento** | Prometheus | Coleta de métricas de performance e uso |
| **Ingestão** | pypdf, python-docx, bs4 | Extração de múltiplos formatos |

---

## ✨ Funcionalidades

- 📄 **Múltiplos formatos**: PDF, DOCX, TXT, Markdown, HTML
- 🔍 **Busca Híbrida**: Combina busca vetorial (semântica) + Full-Text Search (palavras-chave)
- 🗜️ **Compressão de Contexto**: Reduz contexto grande automaticamente antes de enviar ao LLM
- 🔎 **Filtro de similaridade**: Descarta resultados irrelevantes automaticamente
- 💬 **Histórico de conversas**: Perguntas de follow-up com contexto mantido
- 📤 **Upload via API**: Ingestão de documentos com processamento assíncrono
- ✂️ **Chunking semântico**: Divisão inteligente por sentenças (spaCy)
- 🌍 **Suporte Multi-idioma**: Detecção automática e processamento em PT, EN, ES, DE, FR, IT
- 📊 **Dashboard Admin**: Monitoramento completo do sistema, cache e sessões
- 🔬 **Modo Debug/Explain**: Transparência total no pipeline (timing, scores, HyDE)
- 🔄 **Streaming**: Respostas em tempo real
- ⚡ **Observabilidade**: Métricas Prometheus nativas em cada fase do RAG
- 🔧 **Configuração via Env**: Suporte a ambientes DEV, SIT e UAT via arquivos `.env`

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
├── src/
│   ├── api/                  # Endpoints Flask
│   ├── core/                 # Lógica RAG, LLM e NLP
│   ├── data/                 # Banco de dados e Ingestão
│   ├── app.py                # Aplicação principal
│   └── config.py             # Gestão de configurações (Pydantic)
├── .env.example              # Template de configurações
├── run_app.py                # Script de inicialização unificado
└── requirements.txt
```

---

## ⚙️ Configuração

### Pré-requisitos

1. **Python 3.11+** e **Node.js**
2. **Docker** (para PostgreSQL)
3. **LM Studio** com modelos `nomic-embed` e `phi-3.5-mini` carregados.

### 1. Preparar o Ambiente

```bash
# Backend
python -m venv .venv
.\.venv\Scripts\activate
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

### 3. Variáveis de Ambiente (Novo!)

O sistema utiliza `pydantic-settings`. Configure seu ambiente:

1. Copie o template: `cp .env.example .env`
2. Ajuste as variáveis no `.env` (os diretórios agora são relativos ou absolutos via env).

Ambientes suportados: `.env`, `.env.sit`, `.env.uat`.

---

## 🔧 Uso

### Iniciar Tudo (Recomendado)

O script unificado inicia o backend e o frontend simultaneamente:

```bash
python run_app.py
```

### Comandos de Ingestão (CLI)

```bash
# Ingerir pasta de documentos padrão
python -m scripts.ingest

# Verificar status e estatísticas
python -m scripts.ingest --stats
```

---

## 📡 API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/query` | POST | Query RAG principal |
| `/api/chat` | POST | Chat com histórico |
| `/api/ingest` | POST | Upload de arquivo |
| `/api/metrics` | GET | Métricas Prometheus |
| `/api/health` | GET | Status do sistema |

> [!TIP]
> Use o **Admin Dashboard** na interface web para monitorar o sistema visualmente.

---

## 📝 Melhorias Implementadas

- [x] ✅ **Busca Híbrida** (Vetorial + FTS)
- [x] ✅ **Compressão de Contexto**
- [x] ✅ **Re-ranking & Query Expansion**
- [x] ✅ **Observabilidade** (Prometheus)
- [x] ✅ **Admin Dashboard**
- [x] ✅ **Modo Debug/Explain**
- [x] ✅ **Suporte Multi-idioma**
- [x] ✅ **Configuração via Environment (#13)** - Pydantic Settings & `.env`
- [x] ✅ **Script Unificado de Execução** - `run_app.py`
- [x] ✅ **Validação de Schema (#12)** - Pydantic para todos os endpoints

---

## 📄 Licença
Projeto para estudo de técnicas avançadas de RAG.