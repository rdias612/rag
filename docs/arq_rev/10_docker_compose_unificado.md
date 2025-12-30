# 10 - Docker Compose Unificado

## Objetivo
Criar configuração Docker Compose para subir todo o ecossistema (DB + API + Frontend) com um único comando.

---

## Arquivos a Criar/Modificar

| Arquivo | Descrição |
|---------|-----------|
| `docker-compose.yml` | Orquestração principal |
| `docker-compose.override.yml` | Configurações de desenvolvimento |
| `docker-compose.prod.yml` | Configurações de produção |
| `frontend/Dockerfile` | Build do frontend |
| `frontend/nginx.conf` | Configuração do Nginx |

---

## Passos de Implementação

### Passo 1: Criar `docker-compose.yml` (Base)

```yaml
# docker-compose.yml
version: '3.8'

services:
  # =========================================================================
  # Database - PostgreSQL com pgvector
  # =========================================================================
  db:
    image: pgvector/pgvector:pg16
    container_name: rag-db
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-rag}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "${DB_PORT:-5433}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - rag-network

  # =========================================================================
  # Backend - Flask API
  # =========================================================================
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: rag-api
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=${DB_NAME:-rag}
      - DB_USER=${DB_USER:-postgres}
      - DB_PASSWORD=${DB_PASSWORD:-postgres}
      - LM_STUDIO_BASE_URL=${LM_STUDIO_BASE_URL:-http://host.docker.internal:1234/v1}
      - APP_ENV=${APP_ENV:-production}
    ports:
      - "5000:5000"
    volumes:
      - ./logs:/app/logs
      - documents:/app/documents
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - rag-network

  # =========================================================================
  # Frontend - React + Nginx
  # =========================================================================
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: rag-frontend
    depends_on:
      - api
    ports:
      - "80:80"
    networks:
      - rag-network

volumes:
  pgdata:
    driver: local
  documents:
    driver: local

networks:
  rag-network:
    driver: bridge
```

### Passo 2: Criar `docker-compose.override.yml` (Dev)

```yaml
# docker-compose.override.yml - Desenvolvimento
# Automaticamente aplicado em `docker-compose up`
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    environment:
      - APP_ENV=dev
      - FLASK_DEBUG=1
    volumes:
      # Hot reload do código
      - ./src:/app/src:ro
    command: python -m flask run --host=0.0.0.0 --reload

  frontend:
    build:
      context: ./frontend
      target: dev
    volumes:
      - ./frontend/src:/app/src:ro
    command: npm run dev -- --host 0.0.0.0
    ports:
      - "5173:5173"

  # Adminer para debug de banco
  adminer:
    image: adminer:latest
    container_name: rag-adminer
    ports:
      - "8080:8080"
    networks:
      - rag-network
```

### Passo 3: Criar `docker-compose.prod.yml` (Produção)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    environment:
      - APP_ENV=production
      - ENABLE_HTTPS=true
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
      restart_policy:
        condition: on-failure
        max_attempts: 3
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  # Redis para cache e rate limiting
  redis:
    image: redis:7-alpine
    container_name: rag-redis
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - rag-network

volumes:
  redis-data:
```

### Passo 4: Criar `frontend/Dockerfile`

```dockerfile
# frontend/Dockerfile
# =============================================================================
# Stage 1: Development (para compose override)
# =============================================================================
FROM node:20-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# =============================================================================
# Stage 2: Build
# =============================================================================
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# =============================================================================
# Stage 3: Production
# =============================================================================
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Passo 5: Criar `frontend/nginx.conf`

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy para API
    location /api/ {
        proxy_pass http://api:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Streaming support
        proxy_buffering off;
        proxy_cache off;
    }

    # Cache de assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## Comandos de Uso

```bash
# Desenvolvimento (com override automático)
docker-compose up -d

# Produção
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Build das imagens
docker-compose build

# Ver logs
docker-compose logs -f api

# Parar tudo
docker-compose down

# Parar e remover volumes
docker-compose down -v
```

---

## Verificação

```bash
# Subir ambiente completo
docker-compose up -d

# Verificar saúde
docker-compose ps
curl http://localhost:5000/api/health
curl http://localhost/

# Verificar logs
docker-compose logs api
docker-compose logs frontend
```

---

## Arquivo .env para Compose

```bash
# .env (usado pelo docker-compose)
DB_USER=postgres
DB_PASSWORD=sua_senha_segura
DB_NAME=rag
DB_PORT=5433
APP_ENV=production
LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
```
