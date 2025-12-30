# 06 - Configurar CI/CD (GitHub Actions)

## Objetivo
Implementar pipeline de CI/CD para validação automática e deploys consistentes.

---

## Arquivos a Criar

| Arquivo | Descrição |
|---------|-----------|
| `.github/workflows/ci.yml` | Pipeline de Integração Contínua |
| `.github/workflows/cd.yml` | Pipeline de Deploy (opcional) |
| `.github/dependabot.yml` | Atualizações automáticas de deps |

---

## Passos de Implementação

### Passo 1: Criar Estrutura

```bash
mkdir -p .github/workflows
```

### Passo 2: Criar `ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"

jobs:
  # =========================================================================
  # Backend Tests
  # =========================================================================
  backend:
    name: Backend (Python)
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: rag_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
      
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov black mypy isort flake8
          python -m spacy download pt_core_news_sm
      
      - name: Lint - Black
        run: black --check src/
      
      - name: Lint - isort
        run: isort --check-only src/
      
      - name: Lint - flake8
        run: flake8 src/ --max-line-length=100 --ignore=E501,W503
      
      - name: Type Check - mypy
        run: mypy src/ --ignore-missing-imports || true
      
      - name: Run Tests
        env:
          DB_HOST: localhost
          DB_PORT: 5432
          DB_NAME: rag_test
          DB_USER: postgres
          DB_PASSWORD: postgres
        run: |
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=html
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  # =========================================================================
  # Frontend Tests
  # =========================================================================
  frontend:
    name: Frontend (React)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
      
      - name: Lint
        run: npm run lint || true
      
      - name: Type Check
        run: npx tsc --noEmit
      
      - name: Build
        run: npm run build

  # =========================================================================
  # Docker Build Test
  # =========================================================================
  docker:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build API Image
        run: docker build -t rag-api:test .
      
      - name: Build Frontend Image
        run: docker build -t rag-frontend:test ./frontend
```

### Passo 3: Criar `dependabot.yml`

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    groups:
      python-minor:
        patterns:
          - "*"
        update-types:
          - minor
          - patch

  # NPM dependencies
  - package-ecosystem: npm
    directory: "/frontend"
    schedule:
      interval: weekly
    open-pull-requests-limit: 5

  # GitHub Actions
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: monthly
```

### Passo 4: (Opcional) Pipeline de Deploy

```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.REGISTRY_URL }}
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ secrets.REGISTRY_URL }}/rag-api:${{ github.ref_name }}
      
      - name: Deploy
        run: |
          # Seu comando de deploy aqui
          # kubectl apply -f k8s/
          # docker-compose pull && docker-compose up -d
          echo "Deploy completed"
```

---

## Branch Protection Rules

Configurar no GitHub:
1. Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Marcar:
   - [x] Require a pull request before merging
   - [x] Require status checks to pass before merging
   - [x] Require branches to be up to date

---

## Verificação

```bash
# Testar localmente antes de commit
black --check src/
isort --check-only src/
pytest tests/ -v
```

---

## Badges para README

```markdown
![CI](https://github.com/SEU_USER/rag/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/gh/SEU_USER/rag/branch/main/graph/badge.svg)](https://codecov.io/gh/SEU_USER/rag)
```
