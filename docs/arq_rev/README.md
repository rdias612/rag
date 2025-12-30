# 📋 Planos de Implementação - Revisão de Arquitetura

Este diretório contém planos detalhados para tornar o sistema RAG mais production-ready.

---

## 🟢 Fase 1: Fundação (1-2 semanas)

| # | Plano | Esforço | Impacto |
|---|-------|---------|---------|
| [01](./01_refatorar_routes_blueprints.md) | Refatorar routes.py em Blueprints | Médio | Alto |
| [02](./02_dockerfile_api.md) | Criar Dockerfile para API | Baixo | Alto |
| [03](./03_pinning_dependencias.md) | Pinning de Dependências | Baixo | Médio |
| [04](./04_cors_restritivo.md) | CORS Restritivo | Baixo | Alto |

---

## 🟡 Fase 2: Qualidade (2-3 semanas)

| # | Plano | Esforço | Impacto |
|---|-------|---------|---------|
| [05](./05_repository_pattern.md) | Repository Pattern em database.py | Alto | Alto |
| [06](./06_ci_cd_github_actions.md) | Configurar CI/CD (GitHub Actions) | Médio | Alto |
| [07](./07_rate_limiting.md) | Rate Limiting | Baixo | Médio |
| [08](./08_structured_logging.md) | Structured Logging (JSON) | Médio | Médio |

---

## 🔴 Fase 3: Escalabilidade (3-4 semanas)

| # | Plano | Esforço | Impacto |
|---|-------|---------|---------|
| [09](./09_refatorar_rag_services.md) | Refatorar rag.py em Services | Alto | Alto |
| [10](./10_docker_compose_unificado.md) | Docker Compose Unificado | Médio | Alto |
| [11](./11_opentelemetry_tracing.md) | OpenTelemetry Tracing | Médio | Médio |
| [12](./12_autenticacao_api_keys.md) | Autenticação (API Keys/JWT) | Médio | Alto |

---

## 📊 Ordem de Execução Sugerida

```mermaid
graph LR
    subgraph Fase1[Fase 1 - Fundação]
        A[04 CORS] --> B[03 Deps]
        B --> C[02 Dockerfile]
        C --> D[01 Blueprints]
    end
    
    subgraph Fase2[Fase 2 - Qualidade]
        E[08 Logging] --> F[07 Rate Limit]
        F --> G[06 CI/CD]
        G --> H[05 Repository]
    end
    
    subgraph Fase3[Fase 3 - Escalabilidade]
        I[12 Auth] --> J[11 Tracing]
        J --> K[10 Compose]
        K --> L[09 Services]
    end
    
    Fase1 --> Fase2 --> Fase3
```

---

## 🚀 Quick Wins (Começar por aqui)

1. **04 - CORS Restritivo** - menos de 1 hora, impacto alto
2. **03 - Pinning** - 30 minutos, previne bugs futuros
3. **02 - Dockerfile** - 2 horas, habilita containerização

---

> **Dica**: Cada plano é independente. Você pode implementar em qualquer ordem, mas a sequência sugerida minimiza conflitos.
