# Projeto RAG -- Arquitetura Completa (Usando Phi-3.1 Mini)

## 1. Objetivo do Projeto

Construir um sistema RAG (Retrieval-Augmented Generation) local, rápido
e barato, utilizando: - **pgvector** como mecanismo de busca
semântica. - **BGE-Large v2** como modelo de embeddings. - **Phi-3.1
Mini** como LLM principal para geração de respostas. - Todos os
componentes rodando localmente.

Este documento foi estruturado para permitir que um agente de IA
implemente o projeto de forma clara, direta e reprodutível.

------------------------------------------------------------------------

## 2. Arquitetura Geral do Sistema

### **Fluxo Completo**

1.  **Ingestão de dados**
    -   Ler arquivos `.pdf`, `.docx`, `.md`, `.txt`.
    -   Extrair texto usando libraries como `pypdf`, `python-docx`, etc.
    -   Fazer chunking do texto.
2.  **Embedding**
    -   Gerar embeddings usando **BGE-Large v2** (open-source).
    -   Armazenar texto + embeddings + metadados no Postgres com
        pgvector.
3.  **Query RAG**
    -   Usuário envia pergunta.
    -   Pergunta → embedding com o mesmo modelo.
    -   Buscar `k` vizinhos mais próximos via pgvector.
    -   Concatenar contexto retornado.
    -   Enviar contexto para a LLM **Phi-3.1 Mini**.
    -   Gerar resposta final.

------------------------------------------------------------------------

## 3. Detalhes Técnicos do Projeto

### 3.1 Banco de Dados --- Postgres + pgvector

-   Criar tabela:

``` sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documentos (
    id SERIAL PRIMARY KEY,
    content TEXT,
    metadata JSONB,
    embedding VECTOR(1024)
);
```

### 3.2 Chunking

Regras recomendadas: - Tamanho: **500--1200 tokens**. - Overlap:
**100--200 tokens**. - Cada chunk recebe: - `content` - `source` -
`page` - `timestamp`

------------------------------------------------------------------------

## 4. Pipeline de Embeddings

### 4.1 Extração de texto

-   `.pdf`: `pypdf`\
-   `.docx`: `python-docx`\
-   `.md`: leitura normal\
-   `.txt`: leitura normal

### 4.2 Geração de Embeddings

Modelo: **BGE-Large v2**\
Dimensão: **1024**\
Formato salvo no banco: `vector(1024)`.

### 4.3 Inserção no Postgres

Exemplo:

``` python
cur.execute(
    "INSERT INTO documentos (content, metadata, embedding) VALUES (%s, %s, %s)",
    (text, metadata_json, embedding.tolist())
)
```

------------------------------------------------------------------------

## 5. Mecanismo de Busca Semântica

Query SQL típica:

``` sql
SELECT content, metadata
FROM documentos
ORDER BY embedding <-> query_embedding
LIMIT 5;
```

Operador `<->` representa **distância vetorial** (cosine ou L2).

------------------------------------------------------------------------

## 6. Modelo LLM --- Phi-3.1 Mini

### **Características**

-   Muito leve (ideal para 4060 Ti 16GB).
-   Excelente custo/desempenho.
-   Ótimo para:
    -   explicações
    -   resumos curtos
    -   perguntas diretas sobre contexto
    -   tarefas simples a médias

### **Limitações**

-   Raciocínio complexo.
-   Análise profunda de documentos muito longos.
-   Combinação de múltiplas fontes simultaneamente.

### **Configuração recomendada**

Rodar via: - **Ollama** - **LM Studio** - **Text Generation WebUI**

Formato sugerido: `phi3.1-mini-instruct-Q4_K_M`.

------------------------------------------------------------------------

## 7. Prompt RAG Padrão

``` text
Você é um assistente especializado e deve responder apenas com base no contexto fornecido.

[CONTEXTO]
{{contexto}}

[PERGUNTA]
{{pergunta}}

Se a resposta não estiver no contexto, diga: "Não há informações suficientes no contexto."
```

------------------------------------------------------------------------

## 8. Processo de Resposta (Pipeline RAG)

1.  Receber pergunta do usuário.
2.  Gerar embedding da pergunta com BGE-Large v2.
3.  Buscar os `k` chunks mais relevantes no pgvector.
4.  Concatenar chunks como contexto.
5.  Enviar contexto + pergunta para o Phi-3.1 Mini.
6.  Gerar resposta final.
7.  (Opcional) Guardar logs e métricas de precisão.

------------------------------------------------------------------------

## 9. Ferramentas Recomendadas

### Backend

-   Python 3.11+
-   FastAPI ou Flask
-   psycopg2 ou asyncpg
-   huggingface transformers
-   sentence-transformers

### Frontend (opcional)

-   React + Next.js
-   Vite
-   Simple chat UI

------------------------------------------------------------------------

## 10. Considerações de Performance

### Embeddings

-   BGE-Large v2 é pesado, mas roda bem na GPU.
-   Processamento dos 50MB deve durar poucos minutos.

### pgvector

-   Índices recomendados:

``` sql
CREATE INDEX idx_embed ON documentos USING ivfflat (embedding vector_cosine_ops);
```

### LLM

-   Phi-3.1 Mini roda tranquilo em GPU 4060 Ti com Chrome + VSCode
    abertos.
-   Q4_K\_M consome cerca de 3--3.5GB VRAM.

------------------------------------------------------------------------

## 11. Próximos Passos para Implementação

1.  Subir Postgres + pgvector.
2.  Criar tabela e índices.
3.  Criar script de ingestão + chunking + embeddings.
4.  Popular o banco com os embeddings.
5.  Criar API `/query` que implementa o RAG.
6.  Integrar com o Phi-3.1 Mini via Ollama/LM Studio.
7.  Criar interface simples de chat.

------------------------------------------------------------------------

## 12. Conclusão

Este documento fornece as instruções completas para um ambiente RAG
local usando: - **pgvector**\
- **BGE-Large v2**\
- **Phi-3.1 Mini**

Totalmente open-source, rápido, barato e eficiente para sua base de
conhecimento de \~50MB.