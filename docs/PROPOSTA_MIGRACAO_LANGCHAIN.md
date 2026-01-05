# Roadmap: Migração Estrutural para LangChain & LangGraph

Este documento detalha o plano de modernização do sistema RAG, substituindo implementações manuais por padrões de indústria que facilitam a escalabilidade, observabilidade e troca de modelos.

---

## 🎯 Objetivo
Transformar o sistema RAG atual de uma arquitetura "custom-manual" para uma arquitetura baseada em **Chains (LangChain)** e **Graphs (LangGraph)**, mantendo o uso de **LM Studio** e **pgvector**.

---

## 📅 Fase 1: Fundação e Abstração (LLM & Embeddings)
**Foco:** Eliminar o código boilerplate de chamadas HTTP e tratamento de JSON.

### Tasks:
1.  [ ] **Instalação de Dependências:** Adicionar `langchain`, `langchain-openai` e `langchain-community`.
2.  [ ] **Refatoração do LLM (`src/core/llm.py`):**
    *   Substituir `generate_response` por uma instância de `ChatOpenAI`.
    *   Configurar `base_url="http://localhost:1234/v1"` para o LM Studio.
3.  [ ] **Refatoração de Embeddings (`src/core/embeddings.py`):**
    *   Substituir `get_embedding` por `OpenAIEmbeddings`.
    *   Manter a compatibilidade com o cache atual ou migrar para o cache nativo do LangChain.

---

## 🚀 Fase 2: Pipeline Moderno com LCEL
**Foco:** Tornar o fluxo RAG declarativo e modular.

### Tasks:
1.  [ ] **Criação de Custom Retrievers:**
    *   Encapsular o `SearchService` em uma classe `BaseRetriever` do LangChain.
    *   Isso permite que a busca no `pgvector` seja usada em qualquer Chain.
2.  [ ] **Migração do Pipeline (`src/core/rag/pipeline.py`):**
    *   Reescrever o método `query` usando **LCEL** (LangChain Expression Language).
    *   Exemplo: `chain = setup_and_retrieval | prompt | llm | output_parser`.
3.  [ ] **Gerenciamento de Histórico:**
    *   Substituir `src/core/conversation.py` por `ChatMessageHistory`.
    *   Implementar `RunnableWithMessageHistory` para gerenciar o contexto automaticamente.

---

## 🧠 Fase 3: RAG Agêntico com LangGraph
**Foco:** Substituir o loop de reflexão manual (Self-RAG) por um grafo inteligente.

### Tasks:
1.  [ ] **Desenho do Grafo (`src/core/self_rag.py`):**
    *   Definir nós: `retrieve`, `generate`, `grade_documents`, `transform_query`.
    *   Definir bordas condicionais (ex: se o score do documento for baixo, refazer a busca).
2.  [ ] **Implementação do State:**
    *   Criar um `TypedDict` para gerenciar o estado da conversa (pergunta, documentos, resposta, tentativas).
3.  [ ] **Migração da Lógica de Avaliação:**
    *   Mover os prompts de `EVALUATION_PROMPT` para componentes de `OutputParser` que garantem o retorno em JSON.

---

## 📥 Fase 4: Ingestão e Ferramentas
**Foco:** Modernizar a entrada de dados e adicionar "superpoderes" ao sistema.

### Tasks:
1.  [ ] **Refatoração da Ingestão (`scripts/ingest.py`):**
    *   Usar `DirectoryLoader` e `UnstructuredFileLoader` (ou manter `MarkItDown` como loader customizado).
    *   Usar `RecursiveCharacterTextSplitter` para garantir que as quebras de texto respeitem a semântica.
2.  [ ] **Observabilidade com LangSmith:**
    *   Configurar variáveis de ambiente para rastrear cada passo da "corrente de pensamento" da IA sem precisar de logs manuais pesados.

---

## 📋 Resumo da Ordem de Implementação

1.  **Semana 1:** Setup e migração de `llm.py` e `embeddings.py` (Fase 1).
2.  **Semana 2:** Refatoração do Pipeline RAG para LCEL (Fase 2).
3.  **Semana 3:** Implementação do LangGraph para substituir o Self-RAG (Fase 3).
4.  **Semana 4:** Atualização do script de ingestão e testes finais (Fase 4).

---

> [!TIP]
> **Por onde começar?**
> A Fase 1 é a mais segura e com menor risco de quebra. Ela "limpa" o código sem mudar a lógica de negócio. Após ela, a Fase 3 (LangGraph) é a que trará o maior ganho de percepção de inteligência para o usuário final.
