# Plano de Implementação: Observabilidade com OpenTelemetry

> **IMPORTANTE**: Este plano deve ser executado **APÓS** o plano de adoção de LangChain descrito em [`plans/IMPLEMENTACAO_LANGCHAIN.md`](plans/IMPLEMENTACAO_LANGCHAIN.md).

## 📋 Resumo Executivo

Este documento detalha o plano de implementação de observabilidade customizada utilizando **OpenTelemetry** para o sistema RAG, substituindo a dependência de LangSmith. A solução é 100% on-premise, gratuita e oferece cobertura completa de todo o código, incluindo componentes customizados.

> **⚠️ IMPORTANTE**: Este plano deve ser executado **APÓS** o plano de adoção de LangChain descrito em [`plans/IMPLEMENTACAO_LANGCHAIN.md`](plans/IMPLEMENTACAO_LANGCHAIN.md). A ordem de implementação é:
> 1. Primeiro: Implementar wrappers LangChain para LLM e Embeddings
> 2. Depois: Implementar observabilidade com OpenTelemetry

---

## 🎯 Objetivos

1. **Implementar tracing distribuído** com OpenTelemetry para todo o pipeline RAG
2. **Configurar Jaeger** para visualização de traces
3. **Criar dashboards Grafana** para métricas personalizadas
4. **Integrar com sistema existente** de logging e métricas Prometheus
5. **Garantir zero custo de software** (apenas infraestrutura básica)

> **⚠️ IMPORTANTE**: Este plano deve ser executado **APÓS** o plano de adoção de LangChain descrito em [`plans/IMPLEMENTACAO_LANGCHAIN.md`](plans/IMPLEMENTACAO_LANGCHAIN.md). A ordem de implementação é:
> 1. Primeiro: Implementar wrappers LangChain para LLM e Embeddings (2 semanas)
> 2. Depois: Implementar observabilidade com OpenTelemetry (1 semana)
> 3. Por fim: Considerar LangGraph para Self-RAG (opcional, 1-2 semanas)

1. **Implementar tracing distribuído** com OpenTelemetry para todo o pipeline RAG
2. **Configurar Jaeger** para visualização de traces
3. **Criar dashboards Grafana** para métricas personalizadas
4. **Integrar com sistema existente** de logging e métricas Prometheus
5. **Garantir zero custo de software** (apenas infraestrutura básica)

---

## 📊 Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│                     Aplicação RAG                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Pipeline   │  │   LLM/Embed  │  │   Services   │  │
│  │   RAG        │  │   (LangChain)│  │   Custom     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │            │
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
    │  Jaeger  │      │  Grafana  │     │Prometheus│
    │  (Traces)│      │ (Dashboards)│    │ (Metrics)│
    └──────────┘      └───────────┘     └─────────┘
```

---

## 🛠️ Componentes

### 1. **OpenTelemetry SDK (Python)**
- **Propósito**: Instrumentação automática e manual do código
- **Versão**: `opentelemetry-api==1.22.0`, `opentelemetry-sdk==1.22.0`
- **Exportadores**: Jaeger (traces), Prometheus (métricas)

### 2. **Jaeger**
- **Propósito**: Visualização de traces distribuídos
- **Versão**: 1.53 (latest)
- **Deploy**: Docker container
- **Armazenamento**: Elasticsearch (opcional) ou memória

### 3. **Grafana**
- **Propósito**: Dashboards de métricas personalizadas
- **Versão**: 10.3.0 (latest)
- **Deploy**: Docker container
- **Data Sources**: Prometheus, Jaeger

### 4. **Prometheus**
- **Propósito**: Coleta e armazenamento de métricas
- **Versão**: 2.48.0 (latest)
- **Deploy**: Docker container (já existe no projeto)

---

## 📅 Fase de Implementação

### **Fase 1: Setup de Infraestrutura (Semana 1)**

#### 1.1. Criar Docker Compose para Observabilidade

**Arquivo**: [`docker-compose.observability.yml`](docker-compose.observability.yml)

```yaml
version: '3.8'

services:
  # Jaeger para visualização de traces
  jaeger:
    image: jaegertracing/all-in-one:1.53
    ports:
      - "5775:5775/udp"   # accept zipkin.thrift over compact thrift
      - "6831:6831/udp"   # accept jaeger.thrift over compact thrift
      - "6832:6832/udp"   # accept jaeger.thrift over binary thrift
      - "5778:5778"       # accept zipkin.thrift over json
      - "16686:16686"     # serve frontend (Jaeger UI)
      - "14268:14268"     # serve http (Jaeger Collector)
      - "14250:14250"     # accept model.proto
      - "9411:9411"       # serve Zipkin compatible endpoints
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - observability

  # Prometheus para métricas (já existe, incluído para referência)
  prometheus:
    image: prom/prometheus:v2.48.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - observability

  # Grafana para dashboards
  grafana:
    image: grafana/grafana:10.3.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    depends_on:
      - prometheus
      - jaeger
    networks:
      - observability

networks:
  observability:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
```

#### 1.2. Configurar Prometheus

**Arquivo**: [`prometheus/prometheus.yml`](prometheus/prometheus.yml)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Métricas da aplicação RAG
  - job_name: 'rag-app'
    static_configs:
      - targets: ['host.docker.internal:5000']  # Flask app
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Métricas do OpenTelemetry Collector (opcional)
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:4318']
```

#### 1.3. Configurar Provisionamento do Grafana

**Arquivo**: [`grafana/provisioning/datasources/prometheus.yml`](grafana/provisioning/datasources/prometheus.yml)

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    editable: true
```

**Arquivo**: [`grafana/provisioning/dashboards/dashboard.yml`](grafana/provisioning/dashboards/dashboard.yml)

```yaml
apiVersion: 1

providers:
  - name: 'RAG Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

#### 1.4. Testar Infraestrutura

```bash
# Subir serviços de observabilidade
docker-compose -f docker-compose.observability.yml up -d

# Verificar se serviços estão rodando
docker-compose -f docker-compose.observability.yml ps

# Acessar interfaces
# Jaeger: http://localhost:16686
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

---

### **Fase 2: Implementar OpenTelemetry SDK (Semana 2)**

#### 2.1. Adicionar Dependências

**Arquivo**: [`requirements/base.in`](requirements/base.in)

```ini
# OpenTelemetry Core
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-semantic-conventions==0.43b0

# Exporters
opentelemetry-exporter-jaeger==1.21.0
opentelemetry-exporter-prometheus==1.46.0

# Instrumentation
opentelemetry-instrumentation-requests==0.45b0
opentelemetry-instrumentation-flask==0.45b0
opentelemetry-instrumentation-psycopg2==0.45b0

# Utilities
opentelemetry-util-http==0.45b0
```

#### 2.2. Criar Módulo de Observabilidade

**Arquivo**: [`src/core/observability.py`](src/core/observability.py)

```python
"""
Módulo de Observabilidade com OpenTelemetry.

Implementa tracing distribuído e métricas para o sistema RAG.
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource, SERVICE_VERSION
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

from src.config import APP_ENV

# Configurar Resource (identidade do serviço)
resource = Resource(attributes={
    SERVICE_NAME: "rag-system",
    SERVICE_VERSION: "1.0.0",
    "deployment.environment": APP_ENV,
    "service.language": "python",
})

# ============================================================================
# Tracing (Jaeger)
# ============================================================================

def setup_tracing(app=None):
    """
    Configura tracing distribuído com Jaeger.
    
    Args:
        app: Instância Flask (opcional)
    """
    # Configurar TracerProvider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()
    
    # Configurar Jaeger Exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
        agent_port=int(os.getenv("JAEGER_PORT", 6831)),
        max_tag_value_length=4096,
    )
    
    # Adicionar processador batch
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Instrumentar Flask (se app fornecido)
    if app:
        FlaskInstrumentor().instrument_app(app)
    
    # Instrumentar requests (HTTP)
    RequestsInstrumentor().instrument()
    
    # Instrumentar PostgreSQL
    Psycopg2Instrumentor().instrument()
    
    print("✅ OpenTelemetry Tracing configurado com Jaeger")

def get_tracer(name: str = __name__):
    """
    Obtém um tracer para o módulo especificado.
    
    Args:
        name: Nome do módulo
        
    Returns:
        Instância de Tracer
    """
    return trace.get_tracer(name)

# ============================================================================
# Métricas (Prometheus)
# ============================================================================

def setup_metrics():
    """
    Configura coleta de métricas com Prometheus.
    """
    # Configurar Prometheus Reader
    prometheus_reader = PrometheusMetricReader(
        endpoint="/metrics",
        prefix="rag_"
    )
    
    # Configurar MeterProvider
    meter_provider = MeterProvider(
        metric_readers=[prometheus_reader],
        resource=resource
    )
    metrics.set_meter_provider(meter_provider)
    
    print("✅ OpenTelemetry Metrics configurado com Prometheus")

def get_meter(name: str = __name__):
    """
    Obtém um meter para o módulo especificado.
    
    Args:
        name: Nome do módulo
        
    Returns:
        Instância de Meter
    """
    return metrics.get_meter(name)

# ============================================================================
# Métricas Customizadas
# ============================================================================

# Criar métricas específicas do RAG
meter = metrics.get_meter(__name__)

# Contadores
query_counter = meter.create_counter(
    "rag_queries_total",
    description="Número total de queries RAG processadas",
)

document_counter = meter.create_counter(
    "rag_documents_retrieved_total",
    description="Número total de documentos recuperados",
)

# Histogramas (para latência)
query_latency = meter.create_histogram(
    "rag_query_duration_seconds",
    description="Duração das queries RAG",
    unit="s",
)

embedding_latency = meter.create_histogram(
    "rag_embedding_duration_seconds",
    description="Duração da geração de embeddings",
    unit="s",
)

llm_latency = meter.create_histogram(
    "rag_llm_duration_seconds",
    description="Duração das chamadas ao LLM",
    unit="s",
)

# Gauges (para valores atuais)
cache_size = meter.create_gauge(
    "rag_cache_size",
    description="Tamanho atual do cache de embeddings",
)

similarity_score = meter.create_gauge(
    "rag_similarity_score",
    description="Score de similaridade médio",
)

# ============================================================================
# Funções Helper
# ============================================================================

def record_query(duration_seconds: float, documents_count: int, similarity: float):
    """
    Registra métricas de uma query RAG.
    
    Args:
        duration_seconds: Duração da query
        documents_count: Número de documentos recuperados
        similarity: Score de similaridade médio
    """
    query_counter.add(1)
    query_latency.record(duration_seconds)
    document_counter.add(documents_count)
    similarity_score.set(similarity)

def record_embedding(duration_seconds: float):
    """
    Registra métricas de geração de embedding.
    
    Args:
        duration_seconds: Duração da geração
    """
    embedding_latency.record(duration_seconds)

def record_llm_call(duration_seconds: float, tokens: int = None):
    """
    Registra métricas de chamada ao LLM.
    
    Args:
        duration_seconds: Duração da chamada
        tokens: Número de tokens (opcional)
    """
    llm_latency.record(duration_seconds)
    if tokens:
        # Métrica de tokens pode ser adicionada se necessário
        pass

# ============================================================================
# Inicialização
# ============================================================================

def initialize_observability(app=None):
    """
    Inicializa observabilidade completa (tracing + métricas).
    
    Args:
        app: Instância Flask (opcional)
    """
    setup_tracing(app)
    setup_metrics()
    print("✅ Observabilidade OpenTelemetry inicializada")
```

#### 2.3. Integrar com Aplicação Flask

**Arquivo**: [`src/app.py`](src/app.py)

```python
from flask import Flask
from src.core.observability import initialize_observability

app = Flask(__name__)

# Inicializar observabilidade
initialize_observability(app)

# Resto da aplicação...
```

---

### **Fase 3: Instrumentar Pipeline RAG (Semana 3)**

#### 3.1. Instrumentar Pipeline Principal

**Arquivo**: [`src/core/rag/pipeline.py`](src/core/rag/pipeline.py)

```python
from src.core.observability import get_tracer, record_query

tracer = get_tracer(__name__)

class RAGPipeline:
    """Orquestrador do pipeline RAG com injeção de dependências."""
    
    def query(
        self,
        question: str,
        top_k: int = TOP_K_RESULTS,
        temperature: float = 0.7,
        include_sources: bool = True,
        min_similarity: float = None,
        enable_compression: bool = None,
        use_hybrid_search: bool = None,
        hybrid_alpha: float = None,
        collection_id: str = None,
        response_style: str = "detailed",
        debug_mode: bool = False,
        history: str = None,
        enable_adaptive: bool = None,
        search_mode: Optional[Literal["auto", "hierarchical", "sentence"]] = None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """Executa query RAG completa com tracing."""
        
        # Criar span principal
        with tracer.start_as_current_span("rag_query") as span:
            # Adicionar atributos ao span
            span.set_attribute("rag.question", question[:100])
            span.set_attribute("rag.top_k", top_k)
            span.set_attribute("rag.temperature", temperature)
            span.set_attribute("rag.search_mode", search_mode)
            span.set_attribute("rag.collection_id", collection_id)
            
            start_time = time.time()
            
            try:
                # 1. Classificar pergunta
                with tracer.start_as_current_span("classification"):
                    question_type = classify_question(question)
                    span.set_attribute("rag.question_type", question_type)
                
                # 1.5 Aplicar Adaptive Retrieval
                with tracer.start_as_current_span("adaptive_retrieval"):
                    if ENABLE_ADAPTIVE_RETRIEVAL and enable_adaptive:
                        adaptive_result = get_adaptive_params(
                            question,
                            base_top_k=top_k,
                            base_min_similarity=min_similarity
                        )
                        top_k = adaptive_result["top_k"]
                        min_similarity = adaptive_result["min_similarity"]
                        
                        # Adicionar atributos de adaptive retrieval
                        span.set_attribute("adaptive.applied", True)
                        span.set_attribute("adaptive.complexity_score", 
                                         adaptive_result["analysis"]["complexity_score"])
                        span.set_attribute("adaptive.adjustment_reason", 
                                         adaptive_result["adjustment_reason"])
                
                # 2. Gerar embedding
                with tracer.start_as_current_span("embedding_generation"):
                    hyde_embedding = self.strategies.apply_hyde(question)
                    embedding = hyde_embedding or get_embedding(question)
                    span.set_attribute("embedding.dimension", len(embedding))
                
                # 3. Buscar documentos
                with tracer.start_as_current_span("search") as search_span:
                    if use_sentence_window:
                        initial_docs = self.search.search_with_sentence_window(
                            question=question,
                            query_embedding=embedding,
                            top_k=top_k,
                            window_size=SENTENCE_WINDOW_SIZE,
                            collection_id=collection_id,
                            request_id=request_id
                        )
                    else:
                        initial_docs = self.search.search(
                            question=question,
                            query_embedding=embedding,
                            top_k=top_k * 3,
                            min_similarity=min_similarity,
                            use_hybrid=use_hybrid_search,
                            hybrid_alpha=hybrid_alpha,
                            collection_id=collection_id,
                            request_id=request_id
                        )
                    
                    search_span.set_attribute("search.documents_found", len(initial_docs))
                    search_span.set_attribute("search.method", "sentence_window" if use_sentence_window else "vector")
                
                # 4. Refinar busca (MMR, Re-ranking)
                with tracer.start_as_current_span("reranking"):
                    documents, search_metrics = self.strategies.apply_phase2_pipeline(
                        question=question,
                        question_embedding=embedding,
                        initial_results=initial_docs,
                        final_top_k=top_k,
                        search_metrics=search_metrics
                    )
                    span.set_attribute("reranking.applied", search_metrics.get("mmr_applied", False))
                    span.set_attribute("reranking.documents_after", len(documents))
                
                # 5. Montar e comprimir contexto
                with tracer.start_as_current_span("context_building"):
                    raw_context = self.context.build_context(documents, request_id=request_id)
                    context_result = self.context.compress_if_needed(
                        raw_context,
                        question,
                        enable_compression,
                        request_id=request_id
                    )
                    span.set_attribute("context.length", len(raw_context))
                    span.set_attribute("context.compressed", context_result["was_compressed"])
                
                # 6. Construir prompt
                with tracer.start_as_current_span("prompt_building"):
                    prompt = self.prompts.build_prompt(
                        context=context_result["context"],
                        question=question,
                        question_type=question_type,
                        history=history,
                        response_style=response_style
                    )
                    span.set_attribute("prompt.length", len(prompt))
                
                # 7. Gerar resposta
                with tracer.start_as_current_span("llm_generation"):
                    answer = generate_response(prompt, temperature=temperature, request_id=request_id)
                    span.set_attribute("answer.length", len(answer))
                
                # 7.5. Auto-avaliação
                evaluation_metrics = {}
                if ENABLE_AUTO_EVALUATION:
                    with tracer.start_as_current_span("evaluation"):
                        evaluation_result = evaluate_rag_response(
                            question=question,
                            answer=answer,
                            context=raw_context,
                            chunks=documents
                        )
                        span.set_attribute("evaluation.score", evaluation_result["overall_score"])
                        span.set_attribute("evaluation.faithfulness", evaluation_result["faithfulness"])
                        span.set_attribute("evaluation.relevancy", evaluation_result["answer_relevancy"])
                
                # 7.6. Self-RAG
                self_rag_metrics = {}
                if ENABLE_SELF_RAG:
                    with tracer.start_as_current_span("self_rag"):
                        def additional_search(query: str, top_k: int):
                            expanded_queries = expand_query(query)
                            results = []
                            for eq in expanded_queries[:2]:
                                eq_embedding = get_embedding(eq)
                                results.extend(
                                    self.search.search(
                                        question=eq,
                                        query_embedding=eq_embedding,
                                        top_k=top_k,
                                        min_similarity=min_similarity,
                                        use_hybrid=use_hybrid_search,
                                        hybrid_alpha=hybrid_alpha,
                                        collection_id=collection_id
                                    )
                                )
                            return results[:top_k]
                        
                        answer, self_rag_metrics = self_rag_pipeline(
                            question=question,
                            answer=answer,
                            context=raw_context,
                            search_function=additional_search,
                            min_score=SELF_RAG_MIN_SCORE,
                            max_iterations=SELF_RAG_MAX_ITERATIONS
                        )
                        span.set_attribute("self_rag.iterations", self_rag_metrics.get("iterations", 0))
                        span.set_attribute("self_rag.was_refined", self_rag_metrics.get("was_refined", False))
                
                # 8. Formatar resposta
                total_duration = time.time() - start_time
                
                # Registrar métricas
                avg_similarity = sum(d.get("similarity", 0) for d in documents) / len(documents) if documents else 0
                record_query(total_duration, len(documents), avg_similarity)
                
                span.set_attribute("rag.duration_seconds", total_duration)
                span.set_attribute("rag.status", "success")
                
                return self.responses.format_response(
                    answer=answer,
                    documents=documents if include_sources else [],
                    question_type=question_type,
                    was_compressed=context_result["was_compressed"],
                    search_metrics=search_metrics,
                    self_rag_metrics=self_rag_metrics,
                    adaptive_params_used=adaptive_metrics,
                    evaluation_metrics=evaluation_metrics,
                    duration=total_duration
                )
                
            except Exception as e:
                span.set_attribute("rag.status", "error")
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise
```

#### 3.2. Instrumentar LLM

**Arquivo**: [`src/core/llm.py`](src/core/llm.py)

```python
from src.core.observability import get_tracer, record_llm_call

tracer = get_tracer(__name__)

def generate_response(
    prompt: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    stream: bool = False,
    request_id: str = None
) -> str:
    """Gera uma resposta usando o modelo Phi-3.5 Mini com tracing."""
    
    with tracer.start_as_current_span("llm_call") as span:
        # Adicionar atributos
        span.set_attribute("llm.model", LLM_MODEL)
        span.set_attribute("llm.prompt_length", len(prompt))
        span.set_attribute("llm.max_tokens", max_tokens)
        span.set_attribute("llm.temperature", temperature)
        span.set_attribute("llm.stream", stream)
        
        payload = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        start_time = time.time()
        
        try:
            if stream:
                return _generate_stream(payload)
            
            response = requests.post(
                f"{LM_STUDIO_BASE_URL}/chat/completions",
                json=payload,
                timeout=120
            )
            
            response.raise_for_status()
            data = response.json()
            
            result = data["choices"][0]["message"]["content"]
            duration = time.time() - start_time
            
            # Registrar métricas
            tokens = data.get("usage", {}).get("completion_tokens")
            record_llm_call(duration, tokens)
            
            # Adicionar atributos ao span
            span.set_attribute("llm.response_length", len(result))
            span.set_attribute("llm.duration_seconds", duration)
            if tokens:
                span.set_attribute("llm.tokens", tokens)
            
            return result
            
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            raise
```

#### 3.3. Instrumentar Embeddings

**Arquivo**: [`src/core/embeddings.py`](src/core/embeddings.py)

```python
from src.core.observability import get_tracer, record_embedding

tracer = get_tracer(__name__)

def get_embedding(text: str, use_cache: bool = True, request_id: str = None) -> list[float]:
    """Gera o embedding de um texto com tracing."""
    
    with tracer.start_as_current_span("embedding_generation") as span:
        span.set_attribute("embedding.model", EMBEDDING_MODEL)
        span.set_attribute("embedding.text_length", len(text))
        span.set_attribute("embedding.use_cache", use_cache)
        
        # Verificar cache
        if use_cache and EMBEDDING_CACHE_ENABLED:
            cached = embedding_cache.get(text)
            if cached is not None:
                span.set_attribute("embedding.from_cache", True)
                return cached
        
        span.set_attribute("embedding.from_cache", False)
        start_time = time.time()
        
        try:
            # Limpeza do texto
            text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Gerar embedding
            response = requests.post(
                f"{LM_STUDIO_BASE_URL}/embeddings",
                json={"model": EMBEDDING_MODEL, "input": text},
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            
            duration = time.time() - start_time
            
            # Registrar métricas
            record_embedding(duration)
            
            # Adicionar atributos ao span
            span.set_attribute("embedding.dimension", len(embedding))
            span.set_attribute("embedding.duration_seconds", duration)
            
            # Salvar no cache
            if use_cache and EMBEDDING_CACHE_ENABLED:
                embedding_cache.set(text, embedding)
            
            return embedding
            
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            raise
```

#### 3.4. Instrumentar Self-RAG

**Arquivo**: [`src/core/self_rag.py`](src/core/self_rag.py)

```python
from src.core.observability import get_tracer

tracer = get_tracer(__name__)

def self_rag_pipeline(
    question: str,
    answer: str,
    context: str,
    search_function: callable = None,
    min_score: int = 60,
    max_iterations: int = 1
) -> Tuple[str, dict]:
    """Pipeline completo de Self-RAG com tracing."""
    
    with tracer.start_as_current_span("self_rag_pipeline") as span:
        span.set_attribute("self_rag.min_score", min_score)
        span.set_attribute("self_rag.max_iterations", max_iterations)
        
        metrics = {
            "iterations": 0,
            "initial_score": 0,
            "final_score": 0,
            "was_refined": False,
            "total_time_ms": 0
        }
        
        start_time = time.time()
        current_answer = answer
        
        for i in range(max_iterations + 1):
            # Avaliar resposta atual
            with tracer.start_as_current_span("self_rag_evaluation"):
                evaluation = evaluate_response(question, current_answer, context)
                
                if i == 0:
                    metrics["initial_score"] = evaluation["score"]
                    span.set_attribute("self_rag.initial_score", evaluation["score"])
                
                metrics["iterations"] = i + 1
                metrics["final_score"] = evaluation["score"]
                span.set_attribute(f"self_rag.iteration_{i}_score", evaluation["score"])
                
                # Se completa ou atingiu limite, retornar
                if evaluation["is_complete"] and evaluation["score"] >= min_score:
                    span.set_attribute("self_rag.completed_early", True)
                    break
                
                if i >= max_iterations:
                    span.set_attribute("self_rag.completed_max_iterations", True)
                    break
            
            # Tentar refinar
            if search_function and not evaluation["is_complete"]:
                with tracer.start_as_current_span("self_rag_refinement"):
                    try:
                        # Buscar mais contexto
                        additional_results = search_function(question, top_k=3)
                        if additional_results:
                            additional_context = "\n\n".join([
                                r.get("content", "") for r in additional_results
                            ])
                            
                            current_answer = refine_response(
                                question=question,
                                previous_answer=current_answer,
                                reason=evaluation.get("reason", "Resposta incompleta"),
                                additional_context=additional_context
                            )
                            metrics["was_refined"] = True
                            span.set_attribute("self_rag.refined", True)
                            span.set_attribute("self_rag.refinement_reason", evaluation.get("reason"))
                    
                    except Exception as e:
                        span.record_exception(e)
                        break
        
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        span.set_attribute("self_rag.total_time_ms", metrics["total_time_ms"])
        
        return current_answer, metrics
```

---

### **Fase 4: Criar Dashboards Grafana (Semana 4)**

#### 4.1. Dashboard Principal RAG

**Arquivo**: [`grafana/dashboards/rag-main.json`](grafana/dashboards/rag-main.json)

```json
{
  "dashboard": {
    "title": "RAG System - Main Dashboard",
    "uid": "rag-main",
    "panels": [
      {
        "title": "Queries por Minuto",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(rag_queries_total[1m])",
            "legendFormat": "QPM"
          }
        ]
      },
      {
        "title": "Latência Média (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(rag_query_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "title": "Similaridade Média",
        "type": "gauge",
        "targets": [
          {
            "expr": "avg(rag_similarity_score)",
            "legendFormat": "Similaridade"
          }
        ]
      },
      {
        "title": "Documentos Recuperados por Query",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(rag_documents_retrieved_total[5m]) / rate(rag_queries_total[5m])",
            "legendFormat": "Docs/Query"
          }
        ]
      },
      {
        "title": "Latência LLM",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(rag_llm_duration_seconds_bucket[5m]))",
            "legendFormat": "LLM p95"
          }
        ]
      },
      {
        "title": "Latência Embeddings",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(rag_embedding_duration_seconds_bucket[5m]))",
            "legendFormat": "Embedding p95"
          }
        ]
      }
    ]
  }
}
```

#### 4.2. Dashboard de Adaptive Retrieval

**Arquivo**: [`grafana/dashboards/adaptive-retrieval.json`](grafana/dashboards/adaptive-retrieval.json)

```json
{
  "dashboard": {
    "title": "Adaptive Retrieval Metrics",
    "uid": "adaptive-retrieval",
    "panels": [
      {
        "title": "Complexidade Média das Queries",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rag_adaptive_complexity_score)",
            "legendFormat": "Complexidade"
          }
        ]
      },
      {
        "title": "Top K Ajustado",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rag_adaptive_top_k)",
            "legendFormat": "Top K"
          }
        ]
      },
      {
        "title": "Min Similarity Ajustado",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rag_adaptive_min_similarity)",
            "legendFormat": "Min Sim"
          }
        ]
      },
      {
        "title": "Distribuição de Motivos de Ajuste",
        "type": "piechart",
        "targets": [
          {
            "expr": "count by (adjustment_reason) (rag_adaptive_adjustments_total)",
            "legendFormat": "{{adjustment_reason}}"
          }
        ]
      }
    ]
  }
}
```

#### 4.3. Dashboard de Self-RAG

**Arquivo**: [`grafana/dashboards/self-rag.json`](grafana/dashboards/self-rag.json)

```json
{
  "dashboard": {
    "title": "Self-RAG Metrics",
    "uid": "self-rag",
    "panels": [
      {
        "title": "Taxa de Refinamento",
        "type": "gauge",
        "targets": [
          {
            "expr": "sum(rate(rag_self_rag_refined_total[5m])) / sum(rate(rag_self_rag_iterations_total[5m]))",
            "legendFormat": "Refinamento"
          }
        ]
      },
      {
        "title": "Iterações Médias por Query",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rag_self_rag_iterations)",
            "legendFormat": "Iterações"
          }
        ]
      },
      {
        "title": "Score Inicial vs Final",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rag_self_rag_initial_score)",
            "legendFormat": "Inicial"
          },
          {
            "expr": "avg(rag_self_rag_final_score)",
            "legendFormat": "Final"
          }
        ]
      },
      {
        "title": "Tempo de Self-RAG",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(rag_self_rag_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ]
      }
    ]
  }
}
```

---

### **Fase 5: Testes e Validação (Semana 5)**

#### 5.1. Teste de Tracing

```python
# tests/test_observability.py

def test_tracing_integration():
    """Testa se tracing está funcionando corretamente."""
    from src.core.observability import get_tracer
    
    tracer = get_tracer(__name__)
    
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("test.attribute", "value")
        span.add_event("test_event", {"key": "value"})
    
    # Verificar no Jaeger se o span foi criado
    print("✅ Verifique http://localhost:16686 para ver o trace")

def test_metrics_collection():
    """Testa se métricas estão sendo coletadas."""
    import requests
    
    response = requests.get("http://localhost:5000/metrics")
    assert response.status_code == 200
    
    metrics = response.text
    assert "rag_queries_total" in metrics
    assert "rag_query_duration_seconds" in metrics
    
    print("✅ Métricas sendo coletadas corretamente")
```

#### 5.2. Teste de End-to-End

```python
# tests/test_observability_e2e.py

def test_rag_query_with_observability():
    """Testa uma query RAG completa com observabilidade."""
    from src.core.rag.pipeline import RAGPipeline
    
    pipeline = RAGPipeline()
    
    result = pipeline.query(
        question="O que é GWPRP?",
        top_k=5,
        temperature=0.7,
        request_id="test-observability-001"
    )
    
    # Verificar resultado
    assert "answer" in result
    assert "documents" in result
    
    # Verificar no Jaeger se o trace completo foi criado
    # Deve conter spans: rag_query, classification, adaptive_retrieval, 
    # embedding_generation, search, reranking, context_building, 
    # prompt_building, llm_generation
    
    print("✅ Query RAG com observabilidade funcionando")
```

---

## 📊 Comparação: Antes vs Depois

| Aspecto | Antes (Logging Estruturado) | Depois (OpenTelemetry) |
|---------|------------------------------|------------------------|
| **Tracing** | ❌ Não existe | ✅ Distribuído completo |
| **Métricas** | ⚠️ Prometheus básico | ✅ Prometheus + métricas customizadas |
| **Visualização** | ❌ Logs em arquivo | ✅ Jaeger UI + Grafana |
| **Cobertura** | ⚠️ Parcial | ✅ 100% do código |
| **Custo** | $0 | $0 (apenas infra ~$10-50/mês) |
| **Vendor Lock-in** | Nenhum | Nenhum |
| **Performance** | Bom | Bom (overhead <5%) |
| **Debugging** | Difícil (grep logs) | Fácil (visualização de traces) |

---

## 💰 Análise de Custos

### **Custo Anual Estimado**

| Componente | Custo | Justificativa |
|------------|-------|---------------|
| OpenTelemetry SDK | $0 | Open-source |
| Jaeger | $0 | Open-source |
| Grafana | $0 | Open-source |
| Prometheus | $0 | Open-source |
| Infraestrutura (VPS) | $120-600/ano | Servidor pequeno para Jaeger+Grafana |
| **Total** | **$120-600/ano** | |

### **Comparação com LangSmith**

| Solução | Custo Anual | Diferença |
|---------|-------------|-----------|
| LangSmith (Plano Developer) | $468/ano | +$348 a +$648 |
| LangSmith (Plano Team) | $1.788/ano | +$1.188 a +$1.668 |
| **OpenTelemetry Customizado** | **$120-600/ano** | **Baseline** |

**Economia**: $348 a $1.668/ano

---

## 🎯 Benefícios Esperados

### **Técnicos**
1. **Tracing distribuído**: Visualização completa do fluxo de cada query
2. **Debugging acelerado**: Identificar gargalos em segundos vs horas
3. **Métricas customizadas**: Dashboards adaptados ao domínio RAG
4. **Zero vendor lock-in**: Solução 100% open-source
5. **Cobertura total**: Rastreia código LangChain + customizado

### **De Negócio**
1. **Redução de MTTR**: 70% mais rápido para resolver incidentes
2. **Melhoria de performance**: Identificar otimizações com dados reais
3. **Tomada de decisão baseada em dados**: Métricas de Adaptive Retrieval, Self-RAG
4. **Custo zero de software**: Economia de $348-1.668/ano
5. **Privacidade**: Dados nunca saem da infraestrutura

---

## 📋 Checklist de Implementação

### **Semana 1: Infraestrutura**
- [ ] Criar [`docker-compose.observability.yml`](docker-compose.observability.yml)
- [ ] Configurar Prometheus ([`prometheus/prometheus.yml`](prometheus/prometheus.yml))
- [ ] Configurar Grafana provisioning
- [ ] Subir serviços e testar acesso
- [ ] Documentar acesso (URLs, credenciais)

### **Semana 2: OpenTelemetry SDK**
- [ ] Adicionar dependências ao [`requirements/base.in`](requirements/base.in)
- [ ] Criar módulo [`src/core/observability.py`](src/core/observability.py)
- [ ] Integrar com [`src/app.py`](src/app.py)
- [ ] Testar tracing básico
- [ ] Testar métricas básicas

### **Semana 3: Instrumentação**
- [ ] Instrumentar [`src/core/rag/pipeline.py`](src/core/rag/pipeline.py)
- [ ] Instrumentar [`src/core/llm.py`](src/core/llm.py)
- [ ] Instrumentar [`src/core/embeddings.py`](src/core/embeddings.py)
- [ ] Instrumentar [`src/core/self_rag.py`](src/core/self_rag.py)
- [ ] Instrumentar outros componentes críticos

### **Semana 4: Dashboards**
- [ ] Criar dashboard principal RAG
- [ ] Criar dashboard Adaptive Retrieval
- [ ] Criar dashboard Self-RAG
- [ ] Criar dashboard de erros
- [ ] Testar e validar dashboards

### **Semana 5: Testes e Validação**
- [ ] Criar testes de observabilidade
- [ ] Executar testes E2E
- [ ] Validar traces no Jaeger
- [ ] Validar métricas no Grafana
- [ ] Documentar uso e troubleshooting

---

## 🔧 Troubleshooting

### **Problema: Traces não aparecem no Jaeger**

**Soluções:**
1. Verificar se Jaeger está rodando: `docker ps | grep jaeger`
2. Verificar logs do Jaeger: `docker logs jaeger`
3. Verificar se aplicação está enviando traces: `docker logs rag-app`
4. Verificar configuração de `JAEGER_HOST` e `JAEGER_PORT`
5. Testar conexão: `telnet localhost 6831`

### **Problema: Métricas não aparecem no Grafana**

**Soluções:**
1. Verificar se Prometheus está coletando: `http://localhost:9090/targets`
2. Verificar se endpoint `/metrics` está acessível: `curl http://localhost:5000/metrics`
3. Verificar datasource no Grafana: Configuration > Data Sources > Prometheus
4. Testar query no Grafana Explore

### **Problema: Alto overhead de performance**

**Soluções:**
1. Reduzir sampling rate: `Sampler(trace_id_ratio_based=0.1)` (10%)
2. Aumentar tamanho do batch: `BatchSpanProcessor(max_queue_size=2048)`
3. Desabilitar spans desnecessários
4. Usar exportador assíncrono

---

## 📚 Referências

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/reference/specification/trace/semantic_conventions/)

---

## 🗓️ Roadmap Completo de Implementação (3 Meses)

Este roadmap integra a implementação de OpenTelemetry com a estratégia híbrida de adoção seletiva de LangChain.

---

### **Mês 1: Melhorias Incrementais**

#### **Semana 1: Migrar LLM para LangChain (Wrapper Simples)**
- [ ] Instalar dependências LangChain (`langchain-openai`)
- [ ] Criar wrapper para [`src/core/llm.py`](src/core/llm.py:12)
- [ ] Implementar `ChatOpenAI` com `base_url="http://localhost:1234/v1"`
- [ ] Manter compatibilidade com interface existente
- [ ] Testar todas as chamadas LLM
- [ ] Validar streaming com LangChain

**Arquivos afetados**:
- [`src/core/llm.py`](src/core/llm.py:12)
- [`requirements/base.in`](requirements/base.in)

**Benefícios**:
- Observabilidade nativa
- Fallback automático
- Streaming simplificado

---

#### **Semana 2: Migrar Embeddings para LangChain**
- [ ] Instalar dependências LangChain (`langchain-openai`)
- [ ] Criar wrapper para [`src/core/embeddings.py`](src/core/embeddings.py:14)
- [ ] Implementar `OpenAIEmbeddings` com `base_url="http://localhost:1234/v1"`
- [ ] Manter cache customizado existente
- [ ] Testar geração de embeddings
- [ ] Validar batch processing

**Arquivos afetados**:
- [`src/core/embeddings.py`](src/core/embeddings.py:14)
- [`src/core/embedding_cache.py`](src/core/embedding_cache.py)
- [`requirements/base.in`](requirements/base.in)

**Benefícios**:
- Cache nativo (mantém customizado)
- Batch processing otimizado
- Observabilidade integrada

---

#### **Semana 3: Implementar OpenTelemetry para Observabilidade**
- [ ] Criar [`docker-compose.observability.yml`](docker-compose.observability.yml)
- [ ] Configurar Prometheus ([`prometheus/prometheus.yml`](prometheus/prometheus.yml))
- [ ] Configurar Grafana provisioning
- [ ] Criar módulo [`src/core/observability.py`](src/core/observability.py)
- [ ] Integrar com [`src/app.py`](src/app.py)
- [ ] Testar tracing básico
- [ ] Testar métricas básicas

**Arquivos afetados**:
- `docker-compose.observability.yml` (novo)
- `prometheus/prometheus.yml` (novo)
- `grafana/provisioning/datasources/prometheus.yml` (novo)
- `grafana/provisioning/dashboards/dashboard.yml` (novo)
- `src/core/observability.py` (novo)
- `src/app.py`

**Benefícios**:
- Tracing distribuído completo
- Métricas customizadas
- Zero custo de software

---

#### **Semana 4: Configurar Jaeger + Grafana Dashboards**
- [ ] Subir serviços de observabilidade
- [ ] Criar dashboard principal RAG ([`grafana/dashboards/rag-main.json`](grafana/dashboards/rag-main.json))
- [ ] Criar dashboard Adaptive Retrieval ([`grafana/dashboards/adaptive-retrieval.json`](grafana/dashboards/adaptive-retrieval.json))
- [ ] Criar dashboard Self-RAG ([`grafana/dashboards/self-rag.json`](grafana/dashboards/self-rag.json))
- [ ] Testar dashboards
- [ ] Documentar acesso (URLs, credenciais)

**Arquivos afetados**:
- `grafana/dashboards/rag-main.json` (novo)
- `grafana/dashboards/adaptive-retrieval.json` (novo)
- `grafana/dashboards/self-rag.json` (novo)

**Benefícios**:
- Visualização completa de métricas
- Dashboards adaptados ao domínio RAG
- Monitoramento em tempo real

---

### **Mês 2: Otimizações**

#### **Semana 1: Migrar Conversation History para LangChain**
- [ ] Implementar `BaseChatMessageHistory` customizado
- [ ] Adaptar [`src/core/conversation.py`](src/core/conversation.py:101) para LangChain
- [ ] Manter compatibilidade com banco de dados PostgreSQL
- [ ] Testar histórico de conversas
- [ ] Validar suporte a streaming

**Arquivos afetados**:
- [`src/core/conversation.py`](src/core/conversation.py:101)
- [`src/api/routes/sessions.py`](src/api/routes/sessions.py)

**Benefícios**:
- Integração nativa com LangChain chains
- Suporte a streaming
- Histórico persistente

---

#### **Semana 2: Adotar MultiQueryRetriever para Query Expansion**
- [ ] Implementar `MultiQueryRetriever` do LangChain
- [ ] Adaptar [`src/core/query_expansion.py`](src/core/query_expansion.py:13)
- [ ] Manter lógica de RRF (Reciprocal Rank Fusion)
- [ ] Testar query expansion
- [ ] Comparar com implementação atual

**Arquivos afetados**:
- [`src/core/query_expansion.py`](src/core/query_expansion.py:13)
- [`src/core/rag/strategies/retrieval_strategy.py`](src/core/rag/strategies/retrieval_strategy.py:17)

**Benefícios**:
- Implementação testada
- Integração nativa
- Menos código customizado

---

#### **Semana 3: Implementar LangGraph para Self-RAG (Opcional)**
- [ ] Avaliar necessidade de LangGraph para Self-RAG
- [ ] Implementar grafo com nós: retrieve, generate, grade
- [ ] Migrar lógica de [`src/core/self_rag.py`](src/core/self_rag.py:162) para LangGraph
- [ ] Implementar bordas condicionais
- [ ] Testar Self-RAG com LangGraph
- [ ] Comparar performance

**Arquivos afetados**:
- `src/core/self_rag_langgraph.py` (novo, se implementado)
- [`src/core/self_rag.py`](src/core/self_rag.py:162)

**Benefícios**:
- Visualização de fluxos
- State management integrado
- Observabilidade melhorada

---

#### **Semana 4: Testes E2E e Documentação**
- [ ] Criar testes E2E para LangChain wrappers
- [ ] Criar testes E2E para OpenTelemetry
- [ ] Validar integração completa
- [ ] Documentar arquitetura híbrida
- [ ] Criar guias de troubleshooting
- [ ] Atualizar README

**Arquivos afetados**:
- `tests/test_langchain_integration.py` (novo)
- `tests/test_observability_e2e.py` (novo)
- `README.md`
- `docs/ARQUITETURA_HIBRIDA.md` (novo)

**Benefícios**:
- Confiança em implementações
- Documentação completa
- Onboarding facilitado

---

### **Mês 3: Melhorias de Negócio**

> Baseado em [`docs/MELHORIAS_RECOMENDADAS.md`](docs/MELHORIAS_RECOMENDADAS.md)

#### **Semana 1: Sistema de Autenticação JWT**
- [ ] Implementar JWT com access tokens (curto prazo) e refresh tokens (longo prazo)
- [ ] Criar tabelas de usuários e refresh tokens
- [ ] Implementar endpoints: `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`
- [ ] Proteger endpoints sensíveis com `@jwt_required()`
- [ ] Implementar blacklist de tokens
- [ ] Testar fluxo completo de autenticação

**Arquivos afetados**:
- `src/core/auth.py` (novo)
- `src/data/repositories/user_repository.py` (novo)
- `src/data/repositories/refresh_token_repository.py` (novo)
- `src/api/routes/auth.py` (novo)
- `alembic/versions/` (nova migration)

**Benefícios**:
- Segurança robusta
- Experiência fluida para usuário
- Revogação de tokens

---

#### **Semana 2: Rate Limiting Granular**
- [ ] Implementar rate limiting com Redis
- [ ] Configurar limites por endpoint, usuário, tier
- [ ] Implementar middleware de rate limiting
- [ ] Criar endpoints para gerenciar limites
- [ ] Testar rate limiting
- [ ] Documentar limites padrão

**Arquivos afetados**:
- `src/api/middleware/rate_limiter.py` (já existe, expandir)
- `src/config.py` (adicionar configurações)
- `requirements/base.in` (adicionar `flask-limiter`, `redis`)

**Benefícios**:
- Prevenção de abuso e DDoS
- Controle de custos
- Proteção de recursos críticos

---

#### **Semana 3: Dashboard de Monitoramento Avançado**
- [ ] Expandir dashboards Grafana existentes
- [ ] Adicionar métricas de autenticação
- [ ] Adicionar métricas de rate limiting
- [ ] Criar alertas automáticos
- [ ] Implementar predições baseadas em tendências
- [ ] Testar dashboards e alertas

**Arquivos afetados**:
- `grafana/dashboards/rag-main.json` (expansão)
- `grafana/dashboards/security.json` (novo)
- `grafana/dashboards/performance.json` (novo)

**Benefícios**:
- Detecção imediata de problemas
- Visibilidade completa do sistema
- Tomada de decisão informada

---

#### **Semana 4: Sistema de Backup Automatizado**
- [ ] Implementar backup de banco de dados
- [ ] Implementar backup de configurações
- [ ] Implementar backup de documentos metadata
- [ ] Agendar backups automáticos (diário/semanal)
- [ ] Implementar endpoint `/api/admin/backup`
- [ ] Implementar endpoint `/api/admin/restore`
- [ ] Testar backup e restore

**Arquivos afetados**:
- `src/core/backup_manager.py` (novo)
- `src/api/routes/admin.py` (expansão)
- `docker-compose.yml` (adicionar serviço de backup)
- `scripts/backup.sh` (novo)

**Benefícios**:
- Proteção contra perda de dados
- Recuperação rápida de desastres
- Peace of mind para administrador

---

## 📊 Resumo do Roadmap

| Mês | Foco | Principais Entregas | Benefícios |
|------|-------|-------------------|------------|
| **Mês 1** | Melhorias Incrementais | LangChain LLM/Embeddings, OpenTelemetry, Dashboards | Observabilidade, componentes prontos |
| **Mês 2** | Otimizações | Conversation History, Query Expansion, LangGraph Self-RAG, Testes | Integração nativa, visualização de fluxos |
| **Mês 3** | Melhorias de Negócio | Autenticação JWT, Rate Limiting, Dashboard Avançado, Backup | Segurança, monitoramento, proteção de dados |

---

## 🎯 Priorização e Dependências

### **Dependências Críticas**
1. **OpenTelemetry** deve ser implementado antes de LangChain wrappers (para tracing)
2. **LangChain LLM** deve ser implementado antes de Conversation History
3. **Autenticação JWT** deve ser implementado antes de Rate Limiting granular

### **Paralelismo Possível**
- Semana 1 (LLM) e Semana 2 (Embeddings) podem ser feitas em paralelo por desenvolvedores diferentes
- Semana 3 (OpenTelemetry) pode ser feita em paralelo com Semana 1-2
- Mês 3 (Melhorias de Negócio) pode ser feito em paralelo com Mês 2 (Otimizações)

### **Cronograma Recomendado**
- **Sprint 1** (4 semanas): Mês 1 completo
- **Sprint 2** (4 semanas): Mês 2 completo
- **Sprint 3** (4 semanas): Mês 3 completo

---

## ✅ Conclusão

Este plano implementa uma solução de observabilidade completa, gratuita e 100% on-premise para o sistema RAG, integrada com uma estratégia híbrida de adoção seletiva de LangChain. A solução oferece:

1. **Tracing distribuído** com Jaeger para visualização completa
2. **Métricas customizadas** com Prometheus e dashboards Grafana
3. **Cobertura total** de código LangChain + customizado
4. **Zero custo de software** (apenas infraestrutura básica)
5. **Zero vendor lock-in** (solução open-source)
6. **Adoção inteligente** de LangChain apenas onde agrega valor

A implementação é modular, permitindo adicionar novos componentes de observabilidade conforme necessário, sem comprometer a arquitetura existente. O roadmap de 3 meses fornece um caminho claro e priorizado para modernizar o sistema RAG mantendo seus investimentos em código customizado avançado.
