# Plano de Implementação: Adoção Seletiva de LangChain

## 📋 Resumo Executivo

Este documento detalha o plano de implementação de **LangChain** e **LangGraph** para componentes específicos do sistema RAG, mantendo a arquitetura customizada existente. A abordagem é **seletiva**: apenas componentes onde LangChain e LangGraph agregam valor real serão migrados, preservando Adaptive Retrieval, Sentence Window e outras otimizações avançadas.

---

## 🎯 Objetivos

1. **Adotar LangChain para LLM** ([`src/core/llm.py`](src/core/llm.py:12)): Wrapper simples para observabilidade
2. **Adotar LangChain para Embeddings** ([`src/core/embeddings.py`](src/core/embeddings.py:14)): Wrapper simples para cache e batch processing
3. **Implementar LangGraph para Self-RAG** ([`src/core/self_rag_graph.py`](src/core/self_rag_graph.py)): Migrar Self-RAG customizado para LangGraph com visualização de fluxos e state management
4. **Manter arquitetura core customizada**: Preservar Adaptive Retrieval, Sentence Window, etc.
5. **Integrar com OpenTelemetry**: Observabilidade completa via [`plans/IMPLEMENTACAO_OPENTELEMETRY.md`](plans/IMPLEMENTACAO_OPENTELEMETRY.md)

---

## 📊 Arquitetura Híbrida Proposta

```
┌─────────────────────────────────────────────────────────┐
│              Sistema RAG Atual/Futuro               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Pipeline    │  │   LLM/Embed  │  │   Services   │  │
│  │   RAG         │  │   (LangChain)│  │   Custom     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │            │
│         │         ┌────────▼────────┐       │            │
│         │         │  Self-RAG      │       │            │
│         │         │  (LangGraph)   │       │            │
│         │         └────────┬────────┘       │            │
│         └──────────────────┼──────────────────┘            │
│                            │                               │
│                    ┌───────▼────────┐                    │
│                    │ OpenTelemetry  │                    │
│                    │   SDK (Python) │                    │
│                    └───────┬────────┘                    │
└────────────────────────────┼────────────────────────────────┘
                              │
                      ┌────────▼────────┐
                      │   Collector     │
                      │ (OTLP Protocol) │
                      └────────┬────────┘
                              │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
      ┌────▼────┐      ┌─────▼─────┐     ┌────▼────┐
      │  Jaeger  │      │  Grafana   │     │Prometheus│
      │ (Traces)│      │ (Dashboards)│    │ (Metrics)│
      └──────────┘      └───────────┘     └─────────┘
```

---

## 🛠️ Componentes LangChain e LangGraph a Implementar

### 1. **LLM Client** ([`src/core/llm.py`](src/core/llm.py:12))

#### ✅ **Benefícios**
- Observabilidade nativa (tracing automático)
- Fallback automático em caso de erro
- Streaming simplificado
- Integração com LangChain chains futuras

#### ⚠️ **Limitações**
- Apenas wrapper simples, mantém interface existente
- Sem mudanças na lógica de negócio

#### 📋 **Implementação**

**Arquivo**: [`src/core/llm.py`](src/core/llm.py:12)

```python
"""
Módulo de integração com o LLM (Phi-3.5 Mini) via LM Studio API.
Wrapper LangChain para observabilidade.
"""
import time
from typing import Optional, Generator

import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from src.config import LM_STUDIO_BASE_URL, LLM_MODEL

# ============================================================================
# LangChain Wrapper
# ============================================================================

# Instância LangChain (inicializada lazy)
_langchain_llm = None

def get_langchain_llm():
    """
    Obtém instância singleton do LLM LangChain.
    
    Returns:
        Instância de ChatOpenAI
    """
    global _langchain_llm
    if _langchain_llm is None:
        _langchain_llm = ChatOpenAI(
            base_url=LM_STUDIO_BASE_URL,
            model=LLM_MODEL,
            temperature=0.7,
            timeout=120
        )
    return _langchain_llm

# ============================================================================
# Funções Compatíveis (Interface Existente)
# ============================================================================

def generate_response(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False,
    request_id: str = None
) -> str:
    """
    Gera uma resposta usando o modelo Phi-3.5 Mini.
    
    Wrapper para LangChain que mantém compatibilidade com código existente.
    
    Args:
        prompt: Prompt completo (com contexto e pergunta)
        max_tokens: Número máximo de tokens na resposta
        temperature: Temperatura para geração (0.0 = determinístico, 1.0 = criativo)
        stream: Se True, retorna um generator para streaming
        request_id: ID da requisição para correlação de logs
        
    Returns:
        Resposta gerada pelo modelo
    """
    request_id = request_id or "unknown"
    
    # Usar LangChain para observabilidade
    llm = get_langchain_llm()
    
    # Converter prompt para formato LangChain
    messages = [HumanMessage(content=prompt)]
    
    # Log início da requisição
    print("LLM Request Started (LangChain) | request_id=%s | model=%s | prompt_len=%d | max_tokens=%d | temperature=%s | stream=%s",
                   request_id, LLM_MODEL, len(prompt), max_tokens, temperature, stream)
    
    try:
        if stream:
            # Streaming com LangChain
            return _generate_stream_langchain(llm, messages, request_id)
        
        # Geração síncrona com LangChain
        response = llm.invoke(messages)
        
        # Extrair resposta
        result = response.content
        
        duration = time.time() - start_time if 'start_time' in locals() else 0
        
        print("LLM Response Received (LangChain) | request_id=%s | response_len=%d | duration=%s",
                       request_id, len(result), f"{duration:.3f}s")
        
        return result
        
    except Exception as e:
        print("LLM Error (LangChain) | request_id=%s | error_type=%s | error_message=%s",
                       request_id, type(e).__name__, str(e))
        raise


def _generate_stream_langchain(llm, messages: list, request_id: str) -> Generator[str, None, None]:
    """
    Gera resposta em streaming usando LangChain.
    
    Args:
        llm: Instância ChatOpenAI
        messages: Lista de mensagens
        request_id: ID da requisição
        
    Yields:
        Tokens da resposta conforme são gerados
    """
    print("LLM Stream Started (LangChain) | request_id=%s | model=%s",
                   request_id, LLM_MODEL)
    
    try:
        for chunk in llm.stream(messages):
            if hasattr(chunk, 'content'):
                content = chunk.content
            else:
                content = str(chunk)
            
            if content:
                yield content
                
    except Exception as e:
        print("LLM Stream Error (LangChain) | request_id=%s | error_type=%s | error_message=%s",
                       request_id, type(e).__name__, str(e))
        raise


def generate_with_system_prompt(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7
) -> str:
    """
    Gera uma resposta com system prompt separado.
    
    Wrapper para LangChain que mantém compatibilidade.
    
    Args:
        system_prompt: Instruções do sistema
        user_prompt: Prompt do usuário
        max_tokens: Número máximo de tokens na resposta
        temperature: Temperatura para geração
        
    Returns:
        Resposta gerada pelo modelo
    """
    llm = get_langchain_llm()
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    print("LLM Request with System Prompt (LangChain) | model=%s | system_len=%d | user_len=%d",
                   LLM_MODEL, len(system_prompt), len(user_prompt))
    
    response = llm.invoke(messages)
    return response.content


def check_llm_service() -> bool:
    """Verifica se o serviço LLM está disponível."""
    try:
        llm = get_langchain_llm()
        response = llm.invoke([HumanMessage(content="test")])
        return True
    except Exception as e:
        print("LLM service error (LangChain): %s", str(e))
        return False


# ============================================================================
# Funções Legacy (Mantidas para compatibilidade)
# ============================================================================

# Nota: Estas funções agora usam LangChain internamente,
# mas mantêm a mesma interface para não quebrar código existente

def _generate_stream(payload: dict) -> Generator[str, None, None]:
    """
    Gera resposta em streaming (legacy - usa LangChain agora).
    
    Mantido apenas para compatibilidade durante transição.
    """
    llm = get_langchain_llm()
    messages = [HumanMessage(content=payload["messages"][0]["content"])]
    
    for chunk in llm.stream(messages):
        if hasattr(chunk, 'content'):
            yield chunk.content
        elif hasattr(chunk, 'delta'):
            yield chunk.delta.get("content", "")
```

---

### 2. **Embeddings** ([`src/core/embeddings.py`](src/core/embeddings.py:14))

#### ✅ **Benefícios**
- Cache nativo do LangChain (mantém cache customizado)
- Batch processing otimizado
- Observabilidade integrada
- Suporte a múltiplos modelos

#### ⚠️ **Limitações**
- Apenas wrapper simples, mantém interface existente
- Cache customizado preservado

#### 📋 **Implementação**

**Arquivo**: [`src/core/embeddings.py`](src/core/embeddings.py:14)

```python
"""
Módulo de geração de embeddings via LM Studio API (Nomic Embed v1.5).
Wrapper LangChain para observabilidade e batch processing.
"""
import time
import re

import requests
from langchain_openai import OpenAIEmbeddings
from typing import Union

from src.config import LM_STUDIO_BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIMENSION
from src.config import EMBEDDING_CACHE_ENABLED
from src.core.embedding_cache import embedding_cache

# ============================================================================
# LangChain Wrapper
# ============================================================================

# Instância LangChain (inicializada lazy)
_langchain_embeddings = None

def get_langchain_embeddings():
    """
    Obtém instância singleton dos embeddings LangChain.
    
    Returns:
        Instância de OpenAIEmbeddings
    """
    global _langchain_embeddings
    if _langchain_embeddings is None:
        _langchain_embeddings = OpenAIEmbeddings(
            base_url=LM_STUDIO_BASE_URL,
            model=EMBEDDING_MODEL,
            embedding_ctx_length=EMBEDDING_DIMENSION,
            # Desabilitar cache nativo do LangChain para usar nosso cache customizado
            disable_cache=not EMBEDDING_CACHE_ENABLED
        )
    return _langchain_embeddings


def get_embedding(text: str, use_cache: bool = True, request_id: str = None) -> list[float]:
    """
    Gera o embedding de um texto usando o modelo Nomic Embed v1.5.
    
    Wrapper para LangChain que mantém compatibilidade com código existente.
    
    Args:
        text: Texto para gerar embedding
        use_cache: Se True, usa cache para evitar recálculo (default: True)
        
    Returns:
        Lista de floats representando o embedding
    """
    request_id = request_id or "unknown"
    
    # Verificar cache primeiro (se habilitado)
    if use_cache and EMBEDDING_CACHE_ENABLED:
        cached = embedding_cache.get(text)
        if cached is not None:
            print("Embedding from Cache (LangChain wrapper) | request_id=%s | text_len=%d",
                                 request_id, len(text))
            return cached
    
    start_time = time.time()
    
    print("Embedding Generation Started (LangChain wrapper) | request_id=%s | text_len=%d",
                         request_id, len(text))
    
    # Limpeza robusta do texto para evitar erros no modelo/LM Studio
    text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.strip()
    
    # 3. Validar tamanho mínimo do texto (chunks muito pequenos causam problemas)
    if len(text) < 10:
        print("Texto muito pequeno (%d chars) após limpeza. Retornando None.", len(text))
        return None
    
    # 4. Validar conteúdo do texto (evitar chunks só com caracteres especiais)
    if len(text.strip(' \n\r\t.,!?;:()[]{}<>"/\'-=+*&^%$#@|~`_')) < 5:
        print("Texto composto principalmente de caracteres especiais. Retornando None.")
        return None
    
    try:
        # Usar LangChain para geração (com cache customizado)
        embeddings = get_langchain_embeddings().embed_query([text])
        embedding = embeddings[0]
        
        duration = time.time() - start_time
        
        # Validar embedding
        null_count = sum(1 for v in embedding if v is None)
        nan_count = sum(1 for v in embedding if isinstance(v, float) and (v != v))  # NaN check
        inf_count = sum(1 for v in embedding if isinstance(v, float) and (v == float('inf') or v == float('-inf')))
        
        is_valid = (
            embedding is not None and 
            isinstance(embedding, list) and 
            len(embedding) > 0 and 
            null_count == 0 and
            nan_count == 0 and
            inf_count == 0
        )
        
        if not is_valid:
            error_details = []
            if embedding is None:
                error_details.append("embedding is None")
            if not isinstance(embedding, list):
                error_details.append("not a list")
            if len(embedding) > 0:
                error_details.append(f"not a list")
            if null_count > 0:
                error_details.append(f"{null_count} NULLs")
            if nan_count > 0:
                error_details.append(f"{nan_count} NaNs")
            if inf_count > 0:
                error_details.append(f"{inf_count} Infs")
            
            error_reason = ", ".join(error_details)
            
            text_sample = text[:150] + "..." if len(text) > 150 else text
            print(
                "Embedding inválido retornado para '%s'. Texto: %d chars, Embedding: %d dims. Erro: %s. Tentando retry único...",
                text_sample, len(text), len(embedding) if embedding else 0, error_reason
            )
            
            # Um pequeno sleep antes de tentar de novo
            time.sleep(1.0)
            
            # Retry
            embeddings = get_langchain_embeddings().embed_query([text])
            embedding = embeddings[0]
            
            # Validar novamente após retry
            null_count = sum(1 for v in embedding if v is None)
            nan_count = sum(1 for v in embedding if isinstance(v, float) and (v != v))
            inf_count = sum(1 for v in embedding if isinstance(v, float) and (v == float('inf') or v == float('-inf')))
            
            is_valid = (
                embedding is not None and 
                isinstance(embedding, list) and 
                len(embedding) > 0 and 
                null_count == 0 and
                nan_count == 0 and
                inf_count == 0
            )
            
            if not is_valid:
                error_details = []
                if embedding is None:
                    error_details.append("embedding is None")
                if not isinstance(embedding, list):
                    error_details.append("not a list")
                if len(embedding) > 0:
                    error_details.append(f"not a list")
                if null_count > 0:
                    error_details.append(f"{null_count} NULLs")
                if nan_count > 0:
                    error_details.append(f"{nan_count} NaNs")
                if inf_count > 0:
                    error_details.append(f"{inf_count} Infs")
                
                error_reason = ", ".join(error_details)
                
                text_sample = text[:150] + "..." if len(text) > 150 else text
                print(
                    "ERRO: Embedding inválido após retry. Texto: '%s' (%d chars). Erro: %s",
                    text_sample, len(text), error_reason
                )
                raise ValueError(f"O modelo de embeddings retornou um valor inválido ({error_reason}) após retry para o texto: '{text[:50]}...'")
        
        # Log do embedding gerado
        print("Embedding Response (LangChain wrapper) | dim=%d | duration=%.3fs",
                      len(embedding), duration)
        
        print("Embedding Generated (LangChain wrapper) | request_id=%s | dimension=%d | duration=%s | was_cached=%s",
                     request_id, len(embedding), f"{duration:.3f}s", False)
        
        # Armazenar no cache (se habilitado)
        if use_cache and EMBEDDING_CACHE_ENABLED:
            embedding_cache.set(text, embedding)
            print("Embedding Cached (LangChain wrapper) | request_id=%s", request_id)
        
        return embedding
        
    except Exception as e:
        print("Embedding Error (LangChain wrapper) | request_id=%s | error_type=%s | error_message=%s",
                       request_id, type(e).__name__, str(e))
        raise


def get_embeddings_batch(texts: list[str], batch_size: int = 32, document_name: str = None, request_id: str = None) -> list[list[float]]:
    """
    Gera embeddings para múltiplos textos em batch.
    
    Usa LangChain para batch processing otimizado.
    
    Args:
        texts: Lista de textos para gerar embeddings
        batch_size: Tamanho do batch para cada requisição
        document_name: Nome do documento sendo processado (para log)
        
    Returns:
        Lista de embeddings (cada um é uma lista de floats)
    """
    all_embeddings = []
    total_start = time.time()
    request_id = request_id or "unknown"
    
    doc_info = f" [{document_name}]" if document_name else ""
    print("Batch Embedding Started (LangChain wrapper) | request_id=%s | document_name=%s | texts_count=%d | batch_size=%d",
                         request_id, document_name or "unknown", len(texts), batch_size)
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Limpar textos do batch para evitar que um caracter estranho derrube o batch todo
        batch = ["".join(char for char in t if char.isprintable() or char in "\n\r\t").strip() for t in batch]
        
        batch_start = time.time()
        
        print(f"Embedding Batch Request (LangChain wrapper) | batch={i//batch_size + 1}/{(len(texts)-1)//batch_size + 1} | texts_count={len(batch)}")
        
        # Usar LangChain para batch processing
        embeddings = get_langchain_embeddings().embed_documents(batch)
        
        batch_duration = time.time() - batch_start
        print(f"Embedding Batch Response (LangChain wrapper) | count={len(embeddings)} | duration=%.3fs",
                      len(embeddings), batch_duration)
        
        all_embeddings.extend(embeddings)
    
    total_duration = time.time() - total_start
    print(f"Batch Embedding Complete (LangChain wrapper) | request_id=%s | document_name=%s | total_embeddings=%d | total_duration=%s",
                  request_id, document_name or "unknown", len(all_embeddings), f"{total_duration:.2f}s")
    
    return all_embeddings


def check_embedding_service() -> bool:
    """Verifica se o serviço de embeddings está disponível."""
    try:
        embedding = get_embedding("teste")
        print("Embedding service available. Dimension: %d", len(embedding))
        return len(embedding) > 0
    except Exception as e:
        print("Embedding service error (LangChain wrapper): %s", str(e))
        return False
```

---

### 3. **LangGraph para Self-RAG** ([`src/core/self_rag_graph.py`](src/core/self_rag_graph.py))

#### ✅ **Benefícios**
- **Visualização de fluxos**: Interface gráfica para ver o grafo de execução
- **State management integrado**: Gerenciamento automático do estado da conversa
- **Observabilidade melhorada**: Tracing automático de cada nó e borda
- **Flexibilidade**: Fácil adição/remoção de nós no grafo
- **Debugging simplificado**: Ver cada passo do processo de reflexão

#### ⚠️ **Limitações**
- Curva de aprendizado inicial para entender o modelo de grafo
- Requer instalação de dependências adicionais (langgraph)

#### 📋 **Implementação**

Ver seção **Fase 4: LangGraph para Self-RAG** abaixo para detalhes completos da implementação.

---

## 📅 Fase de Implementação

### **Fase 1: Setup e Dependências (2-3 dias)**

#### 1.1. Adicionar Dependências LangChain

**Arquivo**: [`requirements/base.in`](requirements/base.in)

```ini
# LangChain Core
langchain==0.2.11
langchain-core==0.2.11
langchain-openai==0.1.1

# LangGraph para Self-RAG
langgraph==0.0.26
```

#### 1.2. Instalar Dependências

```bash
# Atualizar requirements
pip-compile requirements/base.in

# Instalar novas dependências
pip install -r requirements/base.txt
```

---

### **Fase 2: Implementar LLM Wrapper (2-3 dias)**

#### 2.1. Atualizar [`src/core/llm.py`](src/core/llm.py:12)

- [ ] Adicionar importações LangChain
- [ ] Implementar wrapper simples
- [ ] Manter interface existente
- [ ] Testar chamadas síncronas
- [ ] Testar streaming
- [ ] Validar observabilidade

#### 2.2. Testes

```python
# tests/test_llm_langchain.py

def test_llm_sync():
    """Testa chamada síncrona com LangChain."""
    from src.core.llm import generate_response
    
    result = generate_response("Olá, mundo!")
    assert isinstance(result, str)
    assert len(result) > 0
    print("✅ LLM síncrono funcionando")

def test_llm_stream():
    """Testa streaming com LangChain."""
    from src.core.llm import generate_response
    
    chunks = list(generate_response("Conte sobre Python", stream=True))
    result = "".join(chunks)
    assert len(result) > 0
    print("✅ LLM streaming funcionando")
```

---

### **Fase 3: Implementar Embeddings Wrapper (2-3 dias)**

#### 3.1. Atualizar [`src/core/embeddings.py`](src/core/embeddings.py:14)

- [ ] Adicionar importações LangChain
- [ ] Implementar wrapper simples
- [ ] Manter cache customizado
- [ ] Testar geração individual
- [ ] Testar batch processing
- [ ] Validar observabilidade

#### 3.2. Testes

```python
# tests/test_embeddings_langchain.py

def test_embedding_single():
    """Testa geração de embedding individual."""
    from src.core.embeddings import get_embedding
    
    embedding = get_embedding("Teste de embedding")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    print("✅ Embedding individual funcionando")

def test_embedding_batch():
    """Testa batch processing."""
    from src.core.embeddings import get_embeddings_batch
    
    texts = ["Texto 1", "Texto 2", "Texto 3"]
    embeddings = get_embeddings_batch(texts, batch_size=2)
    
    assert len(embeddings) == 3
    assert all(isinstance(e, list) for e in embeddings)
    print("✅ Batch processing funcionando")
```

---

### **Fase 4: LangGraph para Self-RAG (1-2 semanas)**

#### 4.1. Por que LangGraph para Self-RAG?

**Benefícios do LangGraph:**
- **Visualização de fluxos**: Interface gráfica para ver o grafo de execução
- **State management integrado**: Gerenciamento automático do estado da conversa
- **Observabilidade melhorada**: Tracing automático de cada nó e borda
- **Flexibilidade**: Fácil adição/remoção de nós no grafo
- **Debugging simplificado**: Ver cada passo do processo de reflexão

**Arquitetura Atual vs LangGraph:**
```
Atual (Self-RAG Manual):
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  Retrieve   │────▶│  Evaluate   │
└──────┬──────┘     └──────┬──────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Generate   │◀────│  Refine     │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│  Response   │
└─────────────┘

LangGraph (Grafo Declarativo):
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│          State (Graph)              │
│  ┌─────────┐  ┌─────────┐          │
│  │Retrieve  │  │Generate  │          │
│  └────┬────┘  └────┬────┘          │
│       │            │                │
│       ▼            ▼                │
│  ┌─────────┐  ┌─────────┐          │
│  │Evaluate  │  │ Refine   │          │
│  └─────────┘  └─────────┘          │
│       │            │                │
│       └─────┬──────┘                │
│             │                       │
│      (Conditional Edges)            │
└─────────────────┬───────────────────┘
                  │
                  ▼
           ┌─────────────┐
           │  Response   │
           └─────────────┘
```

#### 4.2. Implementação do Grafo Self-RAG

**Arquivo**: [`src/core/self_rag_graph.py`](src/core/self_rag_graph.py) (novo)

```python
"""
Self-RAG com LangGraph.
Implementação do grafo de reflexão para RAG com avaliação e refinamento.
"""
from typing import TypedDict, Annotated, List, Literal
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.core.llm import get_langchain_llm
from src.core.rag.services.search_service import SearchService
from src.core.reranker import HybridReranker

# ============================================================================
# State do Grafo
# ============================================================================

class SelfRAGState(TypedDict):
    """Estado do grafo Self-RAG."""
    query: str
    documents: List[dict]
    response: str
    evaluation_score: float
    attempts: int
    max_attempts: int
    conversation_history: List[dict]
    retrieval_params: dict
    quality_threshold: float

# ============================================================================
# Nós do Grafo
# ============================================================================

def retrieve_node(state: SelfRAGState) -> SelfRAGState:
    """
    Nó de recuperação de documentos.
    
    Busca documentos relevantes usando os parâmetros de recuperação.
    """
    print("Self-RAG: Retrieve Node | query=%s | attempt=%d",
          state["query"], state["attempts"])
    
    # Usar SearchService existente
    search_service = SearchService()
    
    # Buscar documentos com parâmetros adaptativos
    results = search_service.search(
        query=state["query"],
        top_k=state["retrieval_params"].get("top_k", 10),
        min_similarity=state["retrieval_params"].get("min_similarity", 0.7),
        mode=state["retrieval_params"].get("mode", "hybrid")
    )
    
    # Rerank se necessário
    if state["retrieval_params"].get("use_reranker", False):
        reranker = HybridReranker()
        results = reranker.rerank(state["query"], results)
    
    state["documents"] = results[:state["retrieval_params"].get("top_k", 10)]
    
    print("Self-RAG: Retrieved %d documents", len(state["documents"]))
    
    return state


def generate_node(state: SelfRAGState) -> SelfRAGState:
    """
    Nó de geração de resposta.
    
    Gera resposta baseada nos documentos recuperados.
    """
    print("Self-RAG: Generate Node | documents=%d", len(state["documents"]))
    
    # Preparar contexto
    context = "\n\n".join([
        f"Documento {i+1}: {doc['content']}"
        for i, doc in enumerate(state["documents"])
    ])
    
    # Preparar prompt
    prompt = f"""
    Contexto:
    {context}
    
    Pergunta: {state["query"]}
    
    Gere uma resposta detalhada e precisa baseada apenas no contexto fornecido.
    """
    
    # Gerar resposta usando LangChain LLM
    llm = get_langchain_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    
    state["response"] = response.content
    
    print("Self-RAG: Generated response | length=%d", len(state["response"]))
    
    return state


def evaluate_node(state: SelfRAGState) -> SelfRAGState:
    """
    Nó de avaliação da resposta.
    
    Avalia a qualidade da resposta gerada.
    """
    print("Self-RAG: Evaluate Node")
    
    # Preparar prompt de avaliação
    evaluation_prompt = f"""
    Avalie a qualidade da seguinte resposta para a pergunta.
    
    Pergunta: {state["query"]}
    Resposta: {state["response"]}
    
    Critérios de avaliação:
    1. Relevância: A resposta responde diretamente à pergunta?
    2. Precisão: A informação está correta e baseada no contexto?
    3. Completude: A resposta cobre todos os aspectos importantes?
    4. Clareza: A resposta é clara e bem estruturada?
    
    Retorne um score de 0.0 a 1.0, onde:
    - 0.0-0.3: Ruim (precisa de refinamento)
    - 0.3-0.6: Aceitável (pode ser melhorada)
    - 0.6-1.0: Boa (pode ser retornada)
    
    Retorne APENAS o número (ex: 0.75).
    """
    
    # Avaliar usando LangChain LLM
    llm = get_langchain_llm()
    evaluation = llm.invoke([HumanMessage(content=evaluation_prompt)])
    
    try:
        score = float(evaluation.content.strip())
        state["evaluation_score"] = max(0.0, min(1.0, score))
    except ValueError:
        # Fallback se não conseguir parsear
        state["evaluation_score"] = 0.5
    
    print("Self-RAG: Evaluation score=%.2f", state["evaluation_score"])
    
    return state


def refine_node(state: SelfRAGState) -> SelfRAGState:
    """
    Nó de refinamento da resposta.
    
    Refina a resposta baseado na avaliação.
    """
    print("Self-RAG: Refine Node | score=%.2f", state["evaluation_score"])
    
    # Preparar prompt de refinamento
    refine_prompt = f"""
    A seguinte resposta foi avaliada com score {state["evaluation_score"]}.
    
    Pergunta: {state["query"]}
    Resposta atual: {state["response"]}
    
    Refine a resposta para melhorar:
    - Relevância para a pergunta
    - Precisão das informações
    - Completude da resposta
    - Clareza e estrutura
    
    Mantenha a resposta concisa e direta.
    """
    
    # Refinar usando LangChain LLM
    llm = get_langchain_llm()
    refined = llm.invoke([HumanMessage(content=refine_prompt)])
    
    state["response"] = refined.content
    state["attempts"] += 1
    
    print("Self-RAG: Refined response | attempt=%d", state["attempts"])
    
    return state

# ============================================================================
# Bordas Condicionais
# ============================================================================

def should_continue(state: SelfRAGState) -> Literal["refine", "end"]:
    """
    Decide se deve continuar refinando ou terminar.
    
    Retorna "refine" se a resposta precisa de melhoria, "end" se está boa.
    """
    score = state["evaluation_score"]
    attempts = state["attempts"]
    max_attempts = state["max_attempts"]
    threshold = state["quality_threshold"]
    
    print("Self-RAG: Decision | score=%.2f | attempts=%d | max_attempts=%d | threshold=%.2f",
          score, attempts, max_attempts, threshold)
    
    # Terminar se:
    # 1. Atingiu o threshold de qualidade
    # 2. Excedeu o número máximo de tentativas
    if score >= threshold or attempts >= max_attempts:
        print("Self-RAG: Ending | score=%.2f | attempts=%d", score, attempts)
        return "end"
    
    # Continuar refinando
    print("Self-RAG: Continuing | score=%.2f | attempts=%d", score, attempts)
    return "refine"

# ============================================================================
# Construção do Grafo
# ============================================================================

def build_self_rag_graph() -> StateGraph:
    """
    Constrói o grafo Self-RAG.
    
    Returns:
        Grafo compilado do LangGraph
    """
    # Criar grafo
    workflow = StateGraph(SelfRAGState)
    
    # Adicionar nós
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("refine", refine_node)
    
    # Definir bordas
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "evaluate")
    workflow.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "refine": "refine",
            "end": END
        }
    )
    workflow.add_edge("refine", "evaluate")
    
    # Compilar grafo
    app = workflow.compile()
    
    print("Self-RAG: Graph compiled successfully")
    
    return app

# ============================================================================
# Função Principal
# ============================================================================

def self_rag_with_graph(
    query: str,
    retrieval_params: dict = None,
    max_attempts: int = 3,
    quality_threshold: float = 0.7,
    conversation_history: List[dict] = None
) -> dict:
    """
    Executa Self-RAG usando LangGraph.
    
    Args:
        query: Pergunta do usuário
        retrieval_params: Parâmetros de recuperação (top_k, min_similarity, mode, use_reranker)
        max_attempts: Número máximo de tentativas de refinamento
        quality_threshold: Threshold de qualidade para parar refinamento
        conversation_history: Histórico de conversação
        
    Returns:
        Dicionário com response, documents, evaluation_score, attempts
    """
    # Parâmetros padrão
    retrieval_params = retrieval_params or {
        "top_k": 10,
        "min_similarity": 0.7,
        "mode": "hybrid",
        "use_reranker": True
    }
    
    # Estado inicial
    initial_state = SelfRAGState(
        query=query,
        documents=[],
        response="",
        evaluation_score=0.0,
        attempts=1,
        max_attempts=max_attempts,
        conversation_history=conversation_history or [],
        retrieval_params=retrieval_params,
        quality_threshold=quality_threshold
    )
    
    print("Self-RAG: Starting | query=%s | max_attempts=%d | threshold=%.2f",
          query, max_attempts, quality_threshold)
    
    # Executar grafo
    app = build_self_rag_graph()
    final_state = app.invoke(initial_state)
    
    print("Self-RAG: Completed | score=%.2f | attempts=%d",
          final_state["evaluation_score"], final_state["attempts"])
    
    return {
        "response": final_state["response"],
        "documents": final_state["documents"],
        "evaluation_score": final_state["evaluation_score"],
        "attempts": final_state["attempts"],
        "query": final_state["query"]
    }
```

#### 4.3. Integração com Pipeline RAG

**Atualizar**: [`src/core/rag/pipeline.py`](src/core/rag/pipeline.py:88)

```python
# Adicionar ao src/core/rag/pipeline.py

from src.core.self_rag_graph import self_rag_with_graph

class RAGPipeline:
    # ... código existente ...
    
    def query_with_self_rag_graph(
        self,
        query: str,
        retrieval_params: dict = None,
        max_attempts: int = 3,
        quality_threshold: float = 0.7,
        **kwargs
    ) -> dict:
        """
        Executa query RAG com Self-RAG usando LangGraph.
        
        Args:
            query: Pergunta do usuário
            retrieval_params: Parâmetros de recuperação
            max_attempts: Número máximo de tentativas de refinamento
            quality_threshold: Threshold de qualidade
            
        Returns:
            Dicionário com response, sources, evaluation_score, attempts
        """
        print("RAG Pipeline: Self-RAG Graph | query=%s", query)
        
        # Executar Self-RAG com LangGraph
        result = self_rag_with_graph(
            query=query,
            retrieval_params=retrieval_params,
            max_attempts=max_attempts,
            quality_threshold=quality_threshold,
            conversation_history=self.conversation_manager.get_messages()
        )
        
        # Adicionar ao histórico de conversação
        self.conversation_manager.add_message(
            role="user",
            content=query
        )
        self.conversation_manager.add_message(
            role="assistant",
            content=result["response"]
        )
        
        # Preparar sources
        sources = [
            {
                "id": doc.get("id"),
                "content": doc.get("content"),
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0.0)
            }
            for doc in result["documents"]
        ]
        
        print("RAG Pipeline: Self-RAG Graph completed | score=%.2f | attempts=%d",
              result["evaluation_score"], result["attempts"])
        
        return {
            "response": result["response"],
            "sources": sources,
            "evaluation_score": result["evaluation_score"],
            "attempts": result["attempts"],
            "query": query
        }
```

#### 4.4. Testes

```python
# tests/test_self_rag_graph.py

def test_self_rag_graph_basic():
    """Testa Self-RAG com LangGraph."""
    from src.core.self_rag_graph import self_rag_with_graph
    
    result = self_rag_with_graph(
        query="O que é RAG?",
        max_attempts=2,
        quality_threshold=0.6
    )
    
    assert "response" in result
    assert "evaluation_score" in result
    assert "attempts" in result
    assert result["evaluation_score"] >= 0.0
    assert result["evaluation_score"] <= 1.0
    assert result["attempts"] >= 1
    
    print(f"✅ Self-RAG Graph funcionando | score={result['evaluation_score']:.2f} | attempts={result['attempts']}")

def test_self_rag_graph_with_pipeline():
    """Testa Self-RAG Graph integrado com Pipeline."""
    from src.core.rag.pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    result = pipeline.query_with_self_rag_graph(
        query="Como funciona o Adaptive Retrieval?",
        max_attempts=3,
        quality_threshold=0.7
    )
    
    assert "response" in result
    assert "sources" in result
    assert "evaluation_score" in result
    assert len(result["response"]) > 0
    
    print(f"✅ Self-RAG Graph + Pipeline funcionando | score={result['evaluation_score']:.2f}")
```

#### 4.5. Visualização do Grafo

```python
# Para visualizar o grafo (opcional)

def visualize_self_rag_graph():
    """Gera visualização do grafo Self-RAG."""
    from src.core.self_rag_graph import build_self_rag_graph
    
    app = build_self_rag_graph()
    
    # Gerar visualização (requer graphviz)
    try:
        from IPython.display import Image, display
        display(Image(app.get_graph().draw_mermaid_png()))
    except ImportError:
        print("Instale graphviz para visualização: pip install graphviz")
        print("Grafo em formato Mermaid:")
        print(app.get_graph().print_ascii())
```

#### 4.6. Checklist de Implementação

- [ ] Criar arquivo [`src/core/self_rag_graph.py`](src/core/self_rag_graph.py)
- [ ] Implementar `SelfRAGState` TypedDict
- [ ] Implementar nós: retrieve, generate, evaluate, refine
- [ ] Implementar bordas condicionais
- [ ] Implementar função `build_self_rag_graph()`
- [ ] Implementar função `self_rag_with_graph()`
- [ ] Integrar com [`src/core/rag/pipeline.py`](src/core/rag/pipeline.py:88)
- [ ] Criar testes unitários
- [ ] Testar visualização do grafo
- [ ] Validar performance vs Self-RAG manual

---

### **Fase 5: Integração com OpenTelemetry (1-2 dias)**

#### 4.1. Atualizar [`src/core/observability.py`](src/core/observability.py)

- [ ] Adicionar métricas específicas para LangChain
- [ ] Instrumentar chamadas LangChain
- [ ] Validar tracing

```python
# Adicionar ao src/core/observability.py

# Métricas específicas para LangChain
langchain_llm_calls_total = meter.create_counter(
    "langchain_llm_calls_total",
    description="Número total de chamadas ao LLM via LangChain",
)

langchain_embedding_calls_total = meter.create_counter(
    "langchain_embedding_calls_total",
    description="Número total de chamadas de embeddings via LangChain",
)

def record_langchain_llm_call(duration_seconds: float, tokens: int = None):
    """Registra métricas de chamada LLM via LangChain."""
    langchain_llm_calls_total.add(1)
    llm_latency.record(duration_seconds)
    if tokens:
        # Métrica de tokens pode ser adicionada se necessário
        pass

def record_langchain_embedding_call(duration_seconds: float, batch_size: int = 1):
    """Registra métricas de chamada de embeddings via LangChain."""
    langchain_embedding_calls_total.add(batch_size)
    embedding_latency.record(duration_seconds)
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes (HTTP Direto) | Depois (LangChain + LangGraph) |
|----------|----------------------|-------------------------------|
| **Código Boilerplate** | ❌ Alto (requests manual) | ✅ Baixo (abstração LangChain) |
| **Observabilidade** | ❌ Manual (print statements) | ✅ Nativa (via OpenTelemetry) |
| **Streaming** | ⚠️ Manual (iter_lines) | ✅ Nativa (LangChain) |
| **Fallback** | ❌ Não existe | ✅ Automático |
| **Batch Processing** | ⚠️ Manual (loops) | ✅ Otimizado (LangChain) |
| **Cache** | ✅ Customizado | ✅ Customizado + Nativo |
| **Self-RAG** | ⚠️ Manual (loops de reflexão) | ✅ Declarativo (LangGraph) |
| **Visualização de Fluxos** | ❌ Não existe | ✅ Grafo visual (LangGraph) |
| **State Management** | ⚠️ Manual | ✅ Automático (LangGraph) |
| **Interface** | ✅ Existente | ✅ Mantida (compatível) |
| **Performance** | ✅ Boa | ✅ Boa (overhead <2%) |

---

## 🎯 Benefícios Esperados

### **Técnicos**
1. **Observabilidade nativa**: Tracing automático via OpenTelemetry
2. **Fallback automático**: LangChain tenta novamente em caso de erro
3. **Streaming simplificado**: Abstração nativa do LangChain
4. **Batch processing otimizado**: LangChain otimiza chamadas em lote
5. **Self-RAG declarativo**: LangGraph torna o fluxo de reflexão mais claro e manutenível
6. **Visualização de fluxos**: Grafo visual do processo de reflexão
7. **State management integrado**: Gerenciamento automático do estado da conversa
8. **Zero quebra de código**: Interface compatível mantida

### **De Negócio**
1. **Debugging acelerado**: Traces automáticos facilitam troubleshooting
2. **Melhoria de observabilidade**: Integração com Jaeger/Grafana
3. **Self-RAG mais inteligente**: Fluxo de reflexão mais robusto e observável
4. **Custo zero de software**: LangChain e LangGraph são open-source
5. **Manutenção facilitada**: Menos código boilerplate e fluxos mais claros
6. **Flexibilidade**: Fácil adicionar/remover nós no grafo Self-RAG

---

## 📋 Checklist de Implementação

### **Fase 1: Setup e Dependências**
- [ ] Adicionar dependências ao [`requirements/base.in`](requirements/base.in)
- [ ] Instalar dependências LangChain
- [ ] Testar instalação

### **Fase 2: LLM Wrapper**
- [ ] Atualizar [`src/core/llm.py`](src/core/llm.py:12) com wrapper LangChain
- [ ] Testar chamadas síncronas
- [ ] Testar streaming
- [ ] Validar compatibilidade com código existente
- [ ] Criar testes unitários

### **Fase 3: Embeddings Wrapper**
- [ ] Atualizar [`src/core/embeddings.py`](src/core/embeddings.py:14) com wrapper LangChain
- [ ] Testar geração individual
- [ ] Testar batch processing
- [ ] Validar compatibilidade com cache customizado
- [ ] Criar testes unitários

### **Fase 4: LangGraph para Self-RAG**
- [ ] Criar arquivo [`src/core/self_rag_graph.py`](src/core/self_rag_graph.py)
- [ ] Implementar `SelfRAGState` TypedDict
- [ ] Implementar nós: retrieve, generate, evaluate, refine
- [ ] Implementar bordas condicionais
- [ ] Implementar função `build_self_rag_graph()`
- [ ] Implementar função `self_rag_with_graph()`
- [ ] Integrar com [`src/core/rag/pipeline.py`](src/core/rag/pipeline.py:88)
- [ ] Criar testes unitários
- [ ] Testar visualização do grafo
- [ ] Validar performance vs Self-RAG manual

### **Fase 5: Integração com OpenTelemetry**
- [ ] Atualizar [`src/core/observability.py`](src/core/observability.py) com métricas LangChain
- [ ] Instrumentar chamadas LangChain
- [ ] Instrumentar nós do LangGraph
- [ ] Validar tracing
- [ ] Testar integração completa

---

## 🔧 Troubleshooting

### **Problema: LangChain não conecta ao LM Studio**

**Soluções:**
1. Verificar se LM Studio está rodando: `curl http://localhost:1234/v1/models`
2. Verificar `base_url` no código: deve ser `http://localhost:1234/v1`
3. Verificar logs do LM Studio
4. Testar com `curl` manualmente:
   ```bash
   curl -X POST http://localhost:1234/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"phi-3.5-mini-instruct","messages":[{"role":"user","content":"test"}],"stream":false}'
   ```

### **Problema: Cache customizado não funciona com LangChain**

**Soluções:**
1. Verificar se `disable_cache=True` está configurado no `OpenAIEmbeddings`
2. Verificar se cache customizado está sendo usado corretamente
3. Testar com e sem cache customizado

### **Problema: Streaming não funciona**

**Soluções:**
1. Verificar se `stream=True` está sendo passado corretamente
2. Verificar se generator está sendo consumido corretamente
3. Testar com `list()` para coletar todos os chunks

### **Problema: LangGraph não compila o grafo**

**Soluções:**
1. Verificar se todos os nós estão definidos corretamente
2. Verificar se as bordas condicionais retornam strings válidas
3. Verificar se o TypedDict do estado está completo
4. Testar com `app.get_graph().print_ascii()` para ver o grafo

### **Problema: LangGraph entra em loop infinito**

**Soluções:**
1. Verificar se a borda condicional `should_continue` está retornando "end" corretamente
2. Verificar se `max_attempts` está sendo incrementado
3. Adicionar logs em cada nó para debugar o fluxo
4. Testar com `max_attempts` baixo (ex: 2) para limitar o loop

---

## 📚 Referências

- [LangChain Documentation](https://python.langchain.com/docs/)
- [LangChain OpenAI Integration](https://python.langchain.com/docs/integrations/providers/openai/)
- [LangChain Streaming](https://python.langchain.com/docs/modules/model_io/chat/streaming/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Tutorials](https://langchain-ai.github.io/langgraph/tutorials/)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)

---

## ✅ Conclusão

Este plano implementa uma abordagem **seletiva** de adoção de LangChain e LangGraph, focando apenas em componentes onde agregam valor real:

1. **LLM Wrapper**: Observabilidade nativa e streaming simplificado
2. **Embeddings Wrapper**: Batch processing otimizado e cache nativo
3. **LangGraph para Self-RAG**: Visualização de fluxos, state management integrado e observabilidade melhorada
4. **Manter arquitetura customizada**: Preservar Adaptive Retrieval, Sentence Window, etc.
5. **Integrar com OpenTelemetry**: Observabilidade completa via [`plans/IMPLEMENTACAO_OPENTELEMETRY.md`](plans/IMPLEMENTACAO_OPENTELEMETRY.md)

A implementação é modular e de baixo risco, pois mantém a interface existente e apenas adiciona camadas de abstração sobre o código atual.

---

## 🔄 Próximos Passos

Após completar este plano, o próximo passo é implementar:

1. **Conversation History** com LangChain ([`src/core/conversation.py`](src/core/conversation.py:101))
2. **Query Expansion** com LangChain MultiQueryRetriever ([`src/core/query_expansion.py`](src/core/query_expansion.py:13))

Consulte [`plans/IMPLEMENTACAO_OPENTELEMETRY.md`](plans/IMPLEMENTACAO_OPENTELEMETRY.md) para detalhes da implementação de observabilidade.
