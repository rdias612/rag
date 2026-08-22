# Plano de Implementação & Roadmap de Tarefas

> **Projeto:** RAG System  
> **Documento de Referência:** [`01_analise_qualidade_e_oportunidades.md`](file:///c:/Users/PC/Documents/GitHub/rag/docs/analise_e_roadmap/01_analise_qualidade_e_oportunidades.md)  
> **Status:** Pronto para Execução

---

## 🗺️ Visão Geral das Fases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: Limpeza, Estabilidade e Eliminação de Débitos Técnicos              │
│ ├─ Sprint 1.1: Restauração do Logging e Correção dos `print("%s")`          │
│ ├─ Sprint 1.2: Purga de Código Morto em `src/data/database.py`             │
│ ├─ Sprint 1.3: Limpeza de `src/config.py` e Paths Relativos                │
│ ├─ Sprint 1.4: Unificação do Provider de NLP/spaCy                         │
│ └─ Sprint 1.5: Otimização de Latência e Pipeline Assíncrono                │
├─────────────────────────────────────────────────────────────────────────────┤
│ FASE 2: Evolução de Técnicas Avançadas de RAG                               │
│ ├─ Sprint 2.1: Contextual Retrieval (Anthropic Pattern)                     │
│ ├─ Sprint 2.2: Suíte de Benchmark e Avaliação Offline (RAG Triad)          │
│ ├─ Sprint 2.3: Corrective RAG (CRAG) & Roteador de Ferramentas             │
│ ├─ Sprint 2.4: Knowledge Graph RAG Híbrido (GraphRAG)                      │
│ ├─ Sprint 2.5: BGE-M3 Late Interaction (ColBERT MaxSim)                    │
│ ├─ Sprint 2.6: Multi-Modal RAG (Tabelas e Imagens com VLM)                 │
│ └─ Sprint 2.7: Frontend UX com Citações Clicáveis e Preview de PDF          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# SEÇÃO 1: Qualidade do Código e Refatoração

Esta seção foca em sanar os problemas estruturais, eliminar código morto e preparar a base para novas extensões sem fricção.

---

### 📋 Tarefa 1.1: Restauração do Módulo de Logging Estruturado
* **Prioridade:** 🔴 Alta (Crítico)
* **Status:** ✅ Concluído
* **Objetivo:** Substituir todas as chamadas `print("... %s", val)` quebradas por um sistema de logging profissional com suporte a logs estruturados e rastreamento de erros.
* **Arquivos Afetados:**
  - `src/core/logger.py` *(Criado)*
  - [`src/core/rag/pipeline.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/pipeline.py)
  - [`src/core/rag/services/search_service.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/services/search_service.py)
  - [`src/core/rag/services/context_service.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/services/context_service.py)
  - [`src/data/hybrid_search.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/hybrid_search.py)
  - [`src/data/ingestion.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/ingestion.py)
  - [`src/data/repositories/`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/repositories)
* **Tasks:**
  - [x] Criar logger unificado em `src/core/logger.py` com saída colorida e suporte a formatação padrão (`logger.info`, `logger.error(..., exc_info=True)`).
  - [x] Substituir ocorrências de `print(...)` com `%s` ou `%d` pelas chamadas apropriadas do `logger` em `src/core/` e `src/data/`.
  - [x] Garantir formatação correta de `request_id` nos logs de query.
* **Critério de Aceite:** Nenhuma linha do terminal imprime `%s` literal; stack traces aparecem formatados no console quando ocorrem exceções.

---

### 📋 Tarefa 1.2: Purga do Código Morto em `src/data/database.py`
* **Prioridade:** 🔴 Alta
* **Status:** ✅ Concluído
* **Objetivo:** Reduzir o arquivo `database.py` de 1.154 linhas para ~60 linhas, removendo todas as funções `@deprecated` já migradas para os Repositories.
* **Arquivos Afetados:**
  - [`src/data/database.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/database.py)
  - [`src/data/repositories/base.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/repositories/base.py)
* **Tasks:**
  - [x] Confirmar que nenhum arquivo de produção importa funções depreciadas de `database.py`.
  - [x] Remover decorators `@deprecated` e funções legadas (`insert_document`, `search_similar`, `get_prompts_by_category`, etc.).
  - [x] Manter apenas: `get_connection()`, `check_connection()`, `init_database()` e `run_migrations()`.
  - [x] Executar a suíte de testes / verificação de sintaxe para validar que nenhuma dependência foi quebrada.
* **Critério de Aceite:** `src/data/database.py` com menos de 100 linhas e 100% dos testes passando.

---

### 📋 Tarefa 1.3: Limpeza de `src/config.py` e Remoção de Paths Hardcoded
* **Prioridade:** 🟡 Média
* **Status:** ✅ Concluído
* **Objetivo:** Eliminar a duplicação manual de propriedades e tornar caminhos de diretórios relativos e portáveis.
* **Arquivos Afetados:**
  - [`src/config.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/config.py)
  - [`documents/README.md`](file:///c:/Users/PC/Documents/GitHub/rag/documents/README.md)
* **Tasks:**
  - [x] Alterar `DOCUMENTS_DIR` para `BASE_DIR / "documents"` por padrão, permitindo override via `.env`.
  - [x] Garantir que o diretório padrão `documents/` existe e é criado com documentação de boas-vindas.
  - [x] Limpar caminhos hardcoded de desenvolvedores específicos (`C:\Users\Rian\...`).
* **Critério de Aceite:** A aplicação inicia em qualquer sistema operacional sem apontar para `C:\Users\Rian\...`.

---

### 📋 Tarefa 1.4: Unificação do Provider NLP / spaCy
* **Prioridade:** 🟡 Média
* **Status:** ✅ Concluído
* **Objetivo:** Evitar carregamento redundante de múltiplos pipelines spaCy em memória.
* **Arquivos Afetados:**
  - `src/core/nlp.py` *(Criado)*
  - [`src/data/chunking.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/chunking.py)
  - [`src/data/sentence_window.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/sentence_window.py)
  - [`src/core/language_detector.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/language_detector.py)
* **Tasks:**
  - [x] Criar `NLPManager` singleton em `src/core/nlp.py` que carrega o modelo sob demanda com fallback seguro para modelos em branco e sentencizer.
  - [x] Refatorar `chunking.py`, `sentence_window.py` e `language_detector.py` para consumirem o mesmo `NLPManager`.
* **Critério de Aceite:** Apenas uma instância do spaCy é mantida em memória durante toda a execução.

---

### 📋 Tarefa 1.5: Otimização do Fluxo de Execução do Pipeline (Latência)
* **Prioridade:** 🟡 Média
* **Status:** ✅ Concluído
* **Objetivo:** Eliminar o travamento síncrono de 30-90 segundos causado por avaliações LLM encadeadas no request do usuário.
* **Arquivos Afetados:**
  - [`src/core/rag/pipeline.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/pipeline.py)
* **Tasks:**
  - [x] Mover a execução de `evaluate_rag_response` e persistência de métricas adaptativas para um `ThreadPoolExecutor` desacoplado que roda em background sem bloquear o retorno síncrono.
  - [x] Preservar a opção de avaliação síncrona sob demanda com logs estruturados.
* **Critério de Aceite:** Tempo de resposta da query com auto-avaliação habilitada reduzido para o tempo exclusivo da geração da resposta.

---

# SEÇÃO 2: Novos Requisitos & Funcionalidades Avançadas de RAG

Esta seção estabelece o plano de implementação de técnicas avançadas voltadas para o estudo aprofundado do ciclo de vida de sistemas RAG.

---

### 📋 Tarefa 2.1: Contextual Retrieval (Anthropic Pattern)
* **Objetivo:** Resolver a perda de contexto em chunks isolados gerando resumos contextuais na ingestão.
* **Arquivos Afetados:**
  - `src/data/contextual_retrieval.py` *(Novo)*
  - [`src/data/ingestion.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/ingestion.py)
  - [`src/data/repositories/document_repository.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/repositories/document_repository.py)
* **Tasks:**
  - [ ] Criar prompt para LLM: `Dado o documento inteiro e o chunk abaixo, forneça 1-2 frases situando o chunk no documento`.
  - [ ] Integrar no pipeline de ingestão: gerar o contexto contextual e prefixar no chunk antes de gerar o embedding.
  - [ ] Armazenar o campo `contextualized_content` no banco mantendo o texto original para exibição limpa ao usuário.
* **Critério de Aceite:** Chunks possuem contexto explícito do documento pai, aumentando a pontuação na busca vetorial.

---

### 📋 Tarefa 2.2: Suíte de Benchmark e Avaliação Empírica Offline (RAG Triad)
* **Objetivo:** Criar um ambiente de testes quantitativo para comparar estratégias de chunking e busca.
* **Arquivos Afetados:**
  - `scripts/benchmark_rag.py` *(Novo)*
  - `tests/data/golden_dataset.json` *(Novo)*
  - [`src/core/evaluation.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/evaluation.py)
* **Tasks:**
  - [ ] Criar dataset com 20 perguntas, respostas de referência e chunks esperados (Ground Truth).
  - [ ] Implementar cálculo de:
    - **Hit Rate @ K**
    - **Mean Reciprocal Rank (MRR)**
    - **Faithfulness Score**
    - **Context Precision**
  - [ ] Implementar runner CLI que roda o benchmark comparando: *Sentence Window vs Hierarchical vs Standard* e *Vector vs Hybrid Search*.
  - [ ] Gerar relatório consolidado em Markdown/Tabela com as métricas de cada estratégia.
* **Critério de Aceite:** Executar `python scripts/benchmark_rag.py` e obter comparativo tabular de performance de recuperação.

---

### 📋 Tarefa 2.3: Corrective RAG (CRAG) & Roteamento com Ferramentas
* **Objetivo:** Implementar auto-correção quando a recuperação de documentos não contiver informações suficientes.
* **Arquivos Afetados:**
  - `src/core/crag.py` *(Novo)*
  - [`src/core/rag/pipeline.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/pipeline.py)
* **Tasks:**
  - [ ] Implementar avaliador de relevância dos chunks recuperados (Confidence Evaluator).
  - [ ] Se a confiança for `ALTA` $\rightarrow$ Seguir para geração padrão.
  - [ ] Se a confiança for `BAIXA` $\rightarrow$ Acionar busca externa de fallback (ex: DuckDuckGo / Tavily API) ou acionar Query Reformulation.
  - [ ] Se a confiança for `AMBÍGUA` $\rightarrow$ Combinar busca interna com query expandida.
* **Critério de Aceite:** Perguntas sobre tópicos não indexados acionam o fallback sem alucinar.

---

### 📋 Tarefa 2.4: Knowledge Graph RAG Híbrido (GraphRAG)
* **Objetivo:** Possibilitar raciocínio multi-hop e perguntas globais cruzando entidades em múltiplos documentos.
* **Arquivos Afetados:**
  - `src/data/graph_rag.py` *(Novo)*
  - `alembic/versions/add_graph_tables.py` *(Novo)*
  - [`src/core/rag/services/search_service.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/rag/services/search_service.py)
* **Tasks:**
  - [ ] Criar tabelas PostgreSQL `knowledge_nodes` (id, entity_name, entity_type, chunk_id) e `knowledge_edges` (source_id, target_id, relation_type).
  - [ ] Durante a ingestão, usar LLM para extrair entidades e relações de cada chunk.
  - [ ] Na busca, identificar entidades na query e extrair vizinhos no grafo para compor o contexto junto com os vetores.
* **Critério de Aceite:** Queries do tipo *"Quais conexões existem entre o Conceito A e o Conceito B?"* retornam relações estruturadas no contexto.

---

### 📋 Tarefa 2.5: BGE-M3 Multi-Vector / Late Interaction (ColBERT MaxSim)
* **Objetivo:** Utilizar a capacidade multi-vetorial do BGE-M3 para reranking token a token ultra-rápido.
* **Arquivos Afetados:**
  - `src/core/late_interaction.py` *(Novo)*
  - [`src/core/reranker.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/core/reranker.py)
* **Tasks:**
  - [ ] Implementar função de cálculo de similaridade *MaxSim* entre matrizes de embeddings de tokens.
  - [ ] Integrar como opção de reranker leve que não depende de chamadas extras à LLM.
* **Critério de Aceite:** Reranking executado localmente via tensores sem sobrecarregar o LM Studio.

---

### 📋 Tarefa 2.6: Ingestão Multi-Modal para PDFs (Tabelas e Gráficos)
* **Objetivo:** Permitir que o sistema compreenda tabelas complexas e figuras em documentos PDF.
* **Arquivos Afetados:**
  - `src/data/multimodal_ingestion.py` *(Novo)*
  - [`src/data/ingestion.py`](file:///c:/Users/PC/Documents/GitHub/rag/src/data/ingestion.py)
* **Tasks:**
  - [ ] Integrar extrator de imagens e tabelas recortadas de PDFs (via `pypdf` / `pdfplumber`).
  - [ ] Enviar a imagem recortada para modelo VLM no LM Studio (ex: *Phi-3.5-Vision* ou *Qwen2-VL*) para gerar descrição em markdown.
  - [ ] Vetorizar a descrição mantendo o ponteiro da imagem para o frontend.
* **Critério de Aceite:** Chunks de tabelas contêm dados estruturados fiéis ao documento original.

---

### 📋 Tarefa 2.7: Citações Clicáveis e Visualização no Frontend
* **Objetivo:** Melhorar a auditabilidade das respostas permitindo visualizar a página exata da fonte.
* **Arquivos Afetados:**
  - [`frontend/src/components/MessageList.tsx`](file:///c:/Users/PC/Documents/GitHub/rag/frontend/src/components/MessageList.tsx)
  - `frontend/src/components/PDFViewerModal.tsx` *(Novo)*
  - [`frontend/src/components/SourceModal.tsx`](file:///c:/Users/PC/Documents/GitHub/rag/frontend/src/components/SourceModal.tsx)
* **Tasks:**
  - [ ] Transformar marcações de citação (ex: `[Fonte: doc.pdf, pág. 4]`) em links clicáveis na UI.
  - [ ] Criar modal de visualização de PDF (com `react-pdf` ou `pdfjs`) abrindo diretamente na página citada com o trecho destacado.
* **Critério de Aceite:** Clicar na citação abre a página correspondente do PDF com o contexto destacado.

---

# 📅 Ordem de Execução Recomendada

| Etapa | Foco | Tarefas | Benefício Imediato |
| :---: | :--- | :--- | :--- |
| **1** | Limpeza e Higiene de Código | Tasks 1.1, 1.2, 1.3 | Elimina ruídos nos logs, remove 1.000 linhas de código morto e torna o app portátil |
| **2** | Otimização Estrutural | Tasks 1.4, 1.5 | Reduz uso de memória do spaCy e corta a latência da query pela metade |
| **3** | RAG Avançado & Avaliação | Tasks 2.1, 2.2 | Ingestão com Contextual Retrieval e benchmark comparativo quantitativo |
| **4** | Autonomia & Expansão | Tasks 2.3, 2.4 | Corrective RAG (CRAG) e Knowledge Graph para perguntas complexas |
| **5** | Multi-Modalidade & UX | Tasks 2.5, 2.6, 2.7 | Suporte a tabelas/gráficos com VLM e citações interativas no frontend |
