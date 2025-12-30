# =============================================================================
# RAG API - Production Dockerfile (Ultra Leve - 3-4GB)
# =============================================================================

# Stage 1: Builder (instala dependências)
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar dependências de sistema para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get clean

# Configurar pip com otimizações agressivas
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random

# Criar venv e atualizar pip
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel

# Copiar requirements (mantém cache se requirements.txt não mudou)
COPY requirements/base.txt requirements.txt

# Instalar dependências sem cache e sem arquivos de desenvolvimento
# CRUCIAL: Remover dist-info e egg-info imediatamente após instalação
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyo" -delete 2>/dev/null || true

# =============================================================================
# Stage 2: Runtime (imagem final ultra leve)
FROM python:3.11-slim AS runtime

WORKDIR /app

# Labels de metadados
LABEL maintainer="rag-api@example.com" \
      version="2.2" \
      description="RAG API Production Image - Ultra Optimized"

# Apenas runtime libs essenciais - instalar tudo em um RUN
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache /root/.local /var/cache/apt/*

# Criar usuário não-root
RUN groupadd -r appuser && \
    useradd -r -g appuser --create-home appuser && \
    chown -R appuser:appuser /app

# Copiar ambiente virtual do builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Limpeza EXTREMA do venv após cópia
RUN find /opt/venv -type d -name __pycache__ -prune -exec rm -rf {} \; 2>/dev/null || true && \
    find /opt/venv -type f -name '*.pyc' -delete 2>/dev/null || true && \
    find /opt/venv -type f -name '*.pyo' -delete 2>/dev/null || true && \
    find /opt/venv -type d -name "*.dist-info" -prune -exec rm -rf {} \; 2>/dev/null || true && \
    find /opt/venv -type d -name "*.egg-info" -prune -exec rm -rf {} \; 2>/dev/null || true && \
    find /opt/venv -type d -name "tests" -prune -exec rm -rf {} \; 2>/dev/null || true && \
    find /opt/venv -type d -name "test" -prune -exec rm -rf {} \; 2>/dev/null || true

# Copiar código da aplicação com chown
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini .

# Variáveis de ambiente otimizadas
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1

# Script de inicialização para baixar modelos spaCy (primeira execução)
RUN echo '#!/bin/sh\n\
python -m spacy download pt_core_news_sm && \\\n\
python -m spacy download en_core_web_sm && \\\n\
python -m spacy validate && \\\n\
echo "spaCy models downloaded successfully"\n' > /app/download_spacy.sh && \
    chmod +x /app/download_spacy.sh && \
    chown appuser:appuser /app/download_spacy.sh

# Switch para usuário não-root
USER appuser

# Health check mantido com requests (conforme solicitado)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')" || exit 1

EXPOSE 5000

# Usar gunicorn para produção com workers dinâmicos
CMD ["sh", "-c", "[ ! -f /models/.spacy_initialized ] && /app/download_spacy.sh && touch /models/.spacy_initialized || true && gunicorn \
    --bind 0.0.0.0:5000 \
    --workers ${GUNICORN_WORKERS:-4} \
    --threads ${GUNICORN_THREADS:-2} \
    --worker-class sync \
    --worker-tmp-dir /dev/shm \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    src.app:create_app()"]
