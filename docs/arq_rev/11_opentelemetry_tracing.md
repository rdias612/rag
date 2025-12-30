# 11 - OpenTelemetry Tracing

## Objetivo
Implementar distributed tracing para depurar latência e entender o fluxo de requisições.

---

## Arquivos a Criar/Modificar

| Arquivo | Descrição |
|---------|-----------|
| `requirements.txt` | Adicionar opentelemetry |
| `src/core/telemetry.py` | Configuração do tracer |
| `src/app.py` | Instrumentar Flask |
| `src/core/rag/pipeline.py` | Adicionar spans |

---

## Passos de Implementação

### Passo 1: Adicionar Dependências

```bash
pip install opentelemetry-api opentelemetry-sdk \
    opentelemetry-instrumentation-flask \
    opentelemetry-instrumentation-requests \
    opentelemetry-exporter-otlp
```

Adicionar ao `requirements.txt`:
```txt
# Observability - Tracing
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0
opentelemetry-instrumentation-flask>=0.42b0
opentelemetry-instrumentation-requests>=0.42b0
opentelemetry-exporter-otlp>=1.21.0
```

### Passo 2: Criar `telemetry.py`

```python
"""
Configuração do OpenTelemetry para distributed tracing.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from src.config import APP_ENV, settings


class TelemetryConfig:
    """Configuração centralizada de telemetria."""
    
    OTLP_ENDPOINT = getattr(settings, 'OTLP_ENDPOINT', 'localhost:4317')
    ENABLE_TRACING = getattr(settings, 'ENABLE_TRACING', APP_ENV != 'dev')


def init_telemetry(app=None):
    """
    Inicializa OpenTelemetry tracing.
    
    Args:
        app: Instância Flask para instrumentar
    """
    if not TelemetryConfig.ENABLE_TRACING:
        return
    
    # Criar provider com informações do serviço
    resource = Resource.create({
        SERVICE_NAME: "rag-api",
        "service.version": "2.0.0",
        "deployment.environment": APP_ENV
    })
    
    provider = TracerProvider(resource=resource)
    
    # Configurar exporters
    if APP_ENV == "dev":
        # Console para desenvolvimento
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )
    else:
        # OTLP para produção (Jaeger, Tempo, etc.)
        otlp_exporter = OTLPSpanExporter(
            endpoint=TelemetryConfig.OTLP_ENDPOINT,
            insecure=True
        )
        provider.add_span_processor(
            BatchSpanProcessor(otlp_exporter)
        )
    
    trace.set_tracer_provider(provider)
    
    # Instrumentar bibliotecas
    RequestsInstrumentor().instrument()
    
    if app:
        FlaskInstrumentor().instrument_app(app)
    
    return trace.get_tracer(__name__)


# Tracer global para uso nos módulos
tracer = trace.get_tracer("rag-api")


# =============================================================================
# Decorators e helpers para tracing
# =============================================================================

def traced(span_name: str = None):
    """
    Decorator para adicionar span a uma função.
    
    Usage:
        @traced("process_query")
        def my_function():
            ...
    """
    def decorator(func):
        name = span_name or func.__name__
        
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def add_span_attributes(attributes: dict):
    """Adiciona atributos ao span atual."""
    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
```

### Passo 3: Atualizar `app.py`

```python
from src.core.telemetry import init_telemetry


def create_app() -> Flask:
    app = Flask(__name__)
    
    # ... configurações existentes ...
    
    # Inicializar telemetria
    init_telemetry(app)
    
    # ... resto do código ...
```

### Passo 4: Instrumentar Pipeline RAG

Editar `src/core/rag/pipeline.py`:

```python
from src.core.telemetry import tracer, add_span_attributes


class RAGPipeline:
    
    def query(self, question: str, **kwargs) -> dict:
        with tracer.start_as_current_span("rag_pipeline") as span:
            span.set_attribute("question.length", len(question))
            span.set_attribute("top_k", kwargs.get("top_k", 5))
            
            # 1. Classificar
            with tracer.start_as_current_span("classify_question"):
                question_type = classify_question(question)
                add_span_attributes({"question.type": question_type})
            
            # 2. Embedding
            with tracer.start_as_current_span("generate_embedding"):
                embedding = generate_embedding(question)
            
            # 3. Search
            with tracer.start_as_current_span("search_documents") as search_span:
                documents = self.search.search(question, embedding, **kwargs)
                search_span.set_attribute("documents.count", len(documents))
            
            # 4. Context
            with tracer.start_as_current_span("build_context"):
                context = self.context.build_context(documents)
            
            # 5. Compress
            with tracer.start_as_current_span("compress_context") as ctx_span:
                result = self.context.compress_if_needed(context, question)
                ctx_span.set_attribute("compression.ratio", result["compression_ratio"])
            
            # 6. LLM
            with tracer.start_as_current_span("llm_generation") as llm_span:
                answer = generate_response(prompt)
                llm_span.set_attribute("answer.length", len(answer))
            
            return {...}
```

### Passo 5: Adicionar ao Docker Compose

```yaml
# docker-compose.prod.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: rag-jaeger
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - rag-network

  api:
    environment:
      - ENABLE_TRACING=true
      - OTLP_ENDPOINT=jaeger:4317
```

---

## Visualização de Traces

### Jaeger UI
Acessar `http://localhost:16686`:

1. Selecionar Service: `rag-api`
2. Ver traces com tempo de cada span
3. Identificar gargalos

### Exemplo de Trace
```
rag_pipeline (1.2s)
├── classify_question (10ms)
├── generate_embedding (180ms)
├── search_documents (45ms)
├── build_context (5ms)
├── compress_context (120ms)
└── llm_generation (840ms)
```

---

## Verificação

```bash
# Subir Jaeger
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Fazer requisição
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "O que é RAG?"}'

# Ver trace no Jaeger
open http://localhost:16686
```

---

## Configuração (config.py)

```python
class Settings(BaseSettings):
    # Tracing
    ENABLE_TRACING: bool = False
    OTLP_ENDPOINT: str = "localhost:4317"
```
