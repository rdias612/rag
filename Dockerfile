# =============================================================================
# RAG API - Production Dockerfile
# =============================================================================

# Stage 1: Builder (instala dependências)
FROM python:3.11-slim AS builder

WORKDIR /app

# Dependências de sistema para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python em ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Baixar modelos spaCy
RUN python -m spacy download pt_core_news_sm \
    && python -m spacy download en_core_web_sm

# =============================================================================
# Stage 2: Runtime (imagem final leve)
FROM python:3.11-slim AS runtime

WORKDIR /app

# Apenas runtime libs necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar ambiente virtual do builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código da aplicação
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Usuário não-root para segurança
RUN useradd --create-home appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

EXPOSE 5000

# Usar gunicorn para produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "src.app:create_app()"]
