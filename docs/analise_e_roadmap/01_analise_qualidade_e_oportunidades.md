# Relatório de Análise Técnica: Qualidade de Código & Oportunidades RAG

> **Projeto:** RAG System (Estudo e Experimentação Pessoal)  
> **Data da Análise:** Agosto de 2026  
> **Objetivo:** Avaliar a qualidade estrutural, identificar débitos técnicos/code slop e mapear novos requisitos de alto impacto para aprendizado aprofundado em RAG.

---

## 📌 Sumário Executivo

O projeto apresenta uma base sólida de funcionalidades avançadas de RAG (Busca Híbrida Vetorial + Full-Text Search, Hierarchical Chunking, Sentence Window Retrieval, HyDE, MMR, Compressão de Contexto, Adaptive Retrieval, Self-RAG e Reranking).

Entretanto, a evolução incremental gerou acúmulo de **code slop**, inconsistências e **sobre-engenharia corporativa** que aumentam a complexidade de manutenção sem agregar valor ao estudo central de IA.

Abaixo está o diagnóstico detalhado dividido em dois pilares:
1. **Qualidade do Código e Refatoração (Eliminação de Slop e Débito Técnico)**
2. **Novos Requisitos e Técnicas Avançadas de RAG para Estudo**

---

# 1. 🔍 Diagnóstico de Qualidade do Código

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        DIAGNÓSTICO DE CÓDIGO                               │
├───────────────────────────────┬────────────────────────────────────────────┤
│ 🚨 Bug Global de Logging      │ >400 ocorrências de print("%s", ...)       │
├───────────────────────────────┼────────────────────────────────────────────┤
│ 🗑️ Código Morto / Deprecated  │ ~1.000 linhas obsoletas em database.py     │
├───────────────────────────────┼────────────────────────────────────────────┤
│ 📦 Configuração e Hardcoding  │ 120 linhas duplicadas + Path fixo Windows  │
├───────────────────────────────┼────────────────────────────────────────────┤
│ 🧠 NLP / spaCy Fragmentado    │ 3 arquivos carregando spaCy diferentemente │
├───────────────────────────────┼────────────────────────────────────────────┤
│ ⚙️ Complexidade Corporativa   │ Pools customizados, AES-256, Limiter       │
├───────────────────────────────┼────────────────────────────────────────────┤
│ ⏱️ Gargalo Síncrono de LLM    │ 4 a 8 inferências sequenciais por request  │
└───────────────────────────────┴────────────────────────────────────────────┘
```

---

## 1.1. O Bug Global de Logging (`print("%s", val)`)

### 🔴 Problema
Em uma refatoração anterior, houve a substituição de chamadas de `logger` padrão por `print()`. Contudo, a assinatura de interpolação do `logging` foi mantida.

Em Python, a função `print(*args)` **não interpola especificadores de formato** (como `%s`, `%d`, `%.2f`) e não possui o parâmetro `exc_info=True`.

### 📌 Exemplos no Código
* [`search_service.py:52`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/services/search_service.py#L52-L55):
  ```python
  print("Search Started | request_id=%s | search_type=%s | top_k=%d | alpha=%s",
        request_id, "hybrid" if should_use_hybrid else "vector", top_k, alpha)
  ```
  *Saída no console:*
  ```text
  Search Started | request_id=%s | search_type=%s | top_k=%d | alpha=%s req-123 hybrid 10 0.7
  ```
* [`evaluation_repository.py:108`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/repositories/evaluation_repository.py#L108):
  ```python
  print("Failed to save evaluation: %s", e, exc_info=True)
  ```
  *Saída no console:*
  ```text
  Failed to save evaluation: %s ErroConexao exc_info=True
  ```

### 💡 Impacto
* Dificulta a leitura dos logs no terminal.
* Não exibe stack traces de exceções em tempo real.
* Polui a saída com especificadores não processados.

---

## 1.2. Código Morto em [`src/data/database.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/database.py)

### 🔴 Problema
O arquivo [`database.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/database.py) conta com **1.154 linhas**, das quais aproximadamente **1.000 linhas** são funções marcadas com `@deprecated("Repository.method")`:
- `insert_document`
- `insert_documents_batch`
- `search_similar`
- `search_similar_with_scores`
- `get_parent_content`
- `get_prompt`, `get_prompts_by_category`, etc.

Toda a camada de negócio e serviços já consome diretamente os módulos em [`src/data/repositories/`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/repositories).

### 💡 Impacto
* Gera confusão ao navegar pela camada de dados.
* Aumenta drasticamente o tamanho do arquivo com código não testado e obsoleto.
* Dificulta encontrar a lógica real de conexão com o PostgreSQL.

---

## 1.3. Configurações Redundantes e Hardcoded em [`src/config.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/config.py)

### 🔴 Problema
1. **Caminho absoluto de ambiente pessoal:**
   ```python
   # src/config.py:15
   DOCUMENTS_DIR: Path = Path(r"C:\Users\Rian\Documents\treinamento")
   ```
   Isso causa falhas imediatas se executado em outra máquina ou container Docker sem esse caminho exato.

2. **Duplicação de variáveis:**
   O `pydantic-settings` já carrega e valida o objeto `settings = Settings()`. No entanto, das linhas 210 a 325 há dezenas de linhas reatribuindo manualmente as propriedades:
   ```python
   BASE_DIR = settings.BASE_DIR
   DOCUMENTS_DIR = settings.DOCUMENTS_DIR
   DATABASE_CONFIG = settings.DATABASE_CONFIG
   DATABASE_URL = settings.DATABASE_URL
   EMBEDDING_MODEL = settings.EMBEDDING_MODEL
   # ... mais de 100 linhas idênticas
   ```

---

## 1.4. Inconsistência na Inicialização de NLP / spaCy

### 🔴 Problema
Existem 3 abordagens divergentes para carregar o spaCy:
1. [`chunking.py:36`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/chunking.py#L36): `spacy.blank("pt")` com pipeline leve `sentencizer`.
2. [`sentence_window.py:18`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/sentence_window.py#L18): `spacy.load("pt_core_news_md")` com fallback para `en_core_web_sm`.
3. [`language_detector.py:97`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/language_detector.py#L97): `spacy.blank(lang)` com cache LRU.

### 💡 Impacto
* Consumo desnecessário de memória carregando múltiplos pipelines.
* Comportamento assimétrico na divisão de sentenças dependendo do módulo acionado (Sentence Window vs Chunking padrão).

---

## 1.5. Sobre-Engenharia de Infraestrutura vs. Foco em IA

Para um ambiente de pesquisa e aprendizado, alguns componentes adicionam camadas de manutenção pesadas:
* **Custom Connection Pool ([`connection_pool.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/connection_pool.py) - 476 linhas):** Gerenciamento manual de threads, healthcheckers e failover que podem ser substituídos por pool padrão do `psycopg2` / `SQLAlchemy`.
* **Criptografia AES-256 no Postgres ([`encryption.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/encryption.py)):** Criptografa o campo de texto dos chunks, impossibilitando inspeção rápida via SQL no Adminer/DBeaver.
* **Rate Limiter em Memória / Redis:** Útil para SaaS multiusuário, mas introduz complexidade em desenvolvimento local.

---

## 1.6. Encadeamento Síncrono de LLM e Latência

### 🔴 Problema
No [`pipeline.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/pipeline.py), quando as flags de Self-RAG e Avaliação Automática estão ativas, uma única requisição executa até 8 chamadas síncronas ao LM Studio:
1. Classificação da Pergunta (LLM)
2. Geração de Documento Hipotético HyDE (LLM)
3. Reranking de N Chunks (LLM Reranker)
4. Resposta Final RAG (LLM)
5. Avaliação Faithfulness RAGAS (LLM)
6. Avaliação Relevancy RAGAS (LLM)
7. Self-RAG Evaluation (LLM)
8. Self-RAG Refinement (LLM)

Em hardware de desenvolvimento (GPU/CPU local), essa cadeia pode demorar **mais de 1 minuto** por mensagem no chat.

---

# 2. 🚀 Oportunidades & Novos Requisitos para Estudo Avançado de RAG

Para aprofundar o domínio de arquiteturas de RAG modernas, foram mapeadas as seguintes oportunidades de evolução:

---

## 2.1. Contextual Retrieval (Técnica Anthropic)

```
┌────────────────────────────────────────────────────────┐
│ Documento Original                                     │
│ "Relatório Anual 2024 - Empresa Alfa Tecnologia"       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ Ingestão com LLM
┌────────────────────────────────────────────────────────┐
│ Chunk Pré-pendurado com Contexto:                      │
│ "[Documento: Relatório Anual 2024 | Empresa Alfa]      │
│  A receita líquida operacional atingiu R$ 120M..."     │
└────────────────────────────────────────────────────────┘
```

* **Conceito:** Resolver a perda de contexto que ocorre quando um parágrafo é extraído isoladamente.
* **Mecanismo:** Na ingestão, gerar 1 ou 2 frases resumindo a que documento/seção aquele chunk pertence e concatenar no início do texto antes de gerar o embedding.

---

## 2.2. Graph RAG / Knowledge Graph Híbrido

* **Conceito:** Vetores encontram semelhança semântica local, mas falham em conexões relacionais e raciocínio multi-hop.
* **Mecanismo:** Extrair tripletas estruturadas `(Entidade A) -[RELAÇÃO]-> (Entidade B)` durante a ingestão e armazenar no PostgreSQL ou `networkx`.
* **Benefício:** Responder perguntas que exigem cruzar fatos espalhados por múltiplos arquivos.

---

## 2.3. Corrective RAG (CRAG) & Agentic Router

* **Conceito:** Substituir heurísticas rígidas (`if "como " in question: ...`) por um avaliador de confiança pós-recuperação.
* **Mecanismo:**
  - Se a similaridade dos chunks for alta $\rightarrow$ Responde diretamente.
  - Se a similaridade for baixa/ambígua $\rightarrow$ Aciona expansão de query ou fallback para busca web (DuckDuckGo/Tavily).
  - Se faltarem informações $\rightarrow$ Faz pergunta de esclarecimento ao usuário.

---

## 2.4. Suíte de Benchmark Offline (RAG Triad & Métricas de IR)

* **Conceito:** Avaliar cientificamente o impacto das alterações no pipeline.
* **Mecanismo:** Criar dataset padrão (Ground Truth) de 20 a 50 perguntas/respostas para calcular automaticamente:
  - **Hit Rate @ K** e **MRR (Mean Reciprocal Rank)**
  - **Faithfulness** (Fidelidade ao contexto / ausência de alucinações)
  - **Answer Relevance** (Relevância da resposta gerada)
  - Comparativos tabulares: *Sentence Window* vs *Hierarchical* vs *Busca Híbrida ($\alpha=0.3$ vs $\alpha=0.7$)*.

---

## 2.5. BGE-M3 Multi-Vector & Late Interaction (ColBERT / MaxSim)

* **Conceito:** O modelo de embedding já utilizado no projeto (`bge-m3`) possui suporte nativo a representações multi-vetoriais token a token.
* **Mecanismo:** Implementar o cálculo de similaridade *MaxSim*, que compara os vetores de cada token da query com os vetores dos tokens do documento, entregando precisão de Reranker com custo computacional reduzido.

---

## 2.6. Multi-Modal RAG (Extração e Compreensão de Tabelas/Gráficos)

* **Conceito:** Documentos técnicos possuem dados cruciais em tabelas e infográficos que perdem sentido em texto plano.
* **Mecanismo:**
  - Extrair imagens e tabelas recortadas de PDFs.
  - Utilizar VLM local via LM Studio (ex: *Qwen2-VL* ou *Phi-3.5-Vision*) para descrever os dados antes da vetorização.
  - Exibir a imagem original do gráfico no modal de fontes do frontend.

---

## 2.7. Experiência de Usuário & Citações Interativas no Frontend

* **Conceito:** Transparência total da informação recuperada.
* **Mecanismo:**
  - Tornar as citações `[Fonte: doc.pdf, pág. 5]` clicáveis no chat React.
  - Abrir visualizador de PDF destacando o trecho exato utilizado como contexto.
