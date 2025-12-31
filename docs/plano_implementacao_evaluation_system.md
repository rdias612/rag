# Plano de Implementação - Evaluation System

**Data:** 31/12/2025  
**Objetivo:** Integrar o Evaluation System ao sistema RAG existente para monitoramento de qualidade de respostas

---

## 📋 Visão Geral

### Objetivos Principais

1. **Dashboard Administrativo**: Permitir administradores visualizarem métricas históricas de qualidade das respostas
2. **Interface de Chat**: Permitir usuários finais avaliarem respostas sob demanda
3. **Avaliação Automática**: Opcional, avaliar automaticamente todas as respostas geradas

### Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (React)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────┐           │
│  │ AdminDashboard │  │ MessageList    │           │
│  └──────┬───────┘  └───────┬────────┘           │
│         │                   │                         │
│  ┌──────▼──────────┐  ┌──▼──────────────────┐   │
│  │QualityMetricsPanel│  │ EvaluationModal     │   │
│  │(Dashboard Admin)  │  │(Botão no Chat)     │   │
│  └──────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼ API Calls
┌─────────────────────────────────────────────────────────────┐
│              Backend (Flask API)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐    │
│  │   /api/metrics/quality/* (Novos Endpoints) │    │
│  │   /api/query (Modificado)                 │    │
│  │   /api/chat (Modificado)                  │    │
│  └───────────┬───────────────────────────────┘    │
│              │                                      │
│  ┌───────────▼───────────────────────────────┐    │
│  │ EvaluationRepository (Novo)               │    │
│  │ evaluation_repository.py                  │    │
│  └───────────┬───────────────────────────────┘    │
│              │                                      │
│  ┌───────────▼───────────────────────────────┐    │
│  │ PostgreSQL - tabela rag_evaluations       │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Benefícios Esperados

- ✅ **Monitoramento Contínuo**: Visibilidade histórica da qualidade do RAG
- ✅ **Transparência**: Usuários podem entender qualidade das respostas
- ✅ **Melhoria Contínua**: Dados para ajustar prompts e configurações
- ✅ **Compliance**: Auditoria de qualidade para regulatórios
- ✅ **Feedback**: Identificação de padrões de problemas

---

## 🗄️ Fase 1: Backend - Infraestrutura de Dados

### Objetivo
Criar estrutura de banco de dados para armazenar avaliações

### Tarefas

#### 1.1 Criar Tabela no Banco

**Arquivo:** `alembic/versions/<timestamp>_add_rag_evaluations_table.py`

```python
"""add rag_evaluations table

Revision ID: <id>
Revises: 
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '<id>'
down_revision = '<id-da-anterior>'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rag_evaluations',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('faithfulness', sa.Float(), nullable=True),
        sa.Column('answer_relevancy', sa.Float(), nullable=True),
        sa.Column('context_precision', sa.Float(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('evaluation_summary', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('chunks_retrieved', sa.Integer(), nullable=True),
        sa.Column('search_mode', sa.String(20), nullable=True),
        sa.Column('adaptive_used', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Índices para performance
    op.create_index('idx_evaluations_created', 'rag_evaluations', ['created_at'])
    op.create_index('idx_evaluations_score', 'rag_evaluations', ['overall_score'])
    op.create_index('idx_evaluations_session', 'rag_evaluations', ['session_id'])


def downgrade():
    op.drop_index('idx_evaluations_session', 'rag_evaluations')
    op.drop_index('idx_evaluations_score', 'rag_evaluations')
    op.drop_index('idx_evaluations_created', 'rag_evaluations')
    op.drop_table('rag_evaluations')
```

**Validação:**
```bash
# Criar migration
alembic revision -m "Add rag_evaluations table"

# Aplicar
alembic upgrade head

# Verificar tabela
psql -h localhost -p 5433 -U postgres -d ragdb -c "\d rag_evaluations"
```

#### 1.2 Criar Repository

**Arquivo:** `src/data/repositories/evaluation_repository.py`

```python
"""Repository para gerenciamento de avaliações RAG."""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.data.repositories.base import BaseRepository
from src.core.evaluation import evaluate_rag_response


class EvaluationRepository(BaseRepository):
    """Repository para operações de avaliação."""
    
    def save_evaluation(
        self,
        question: str,
        answer: str,
        context: str,
        scores: Dict[str, float],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        chunks_retrieved: Optional[int] = None,
        search_mode: Optional[str] = None,
        adaptive_used: bool = False
    ) -> int:
        """
        Salva uma avaliação no banco.
        
        Args:
            question: Pergunta do usuário
            answer: Resposta gerada
            context: Contexto usado
            scores: Dict com scores das métricas
            session_id: ID da sessão (opcional)
            user_id: ID do usuário (opcional)
            chunks_retrieved: Número de chunks recuperados
            search_mode: Modo de busca usado
            adaptive_used: Se adaptive retrieval foi usado
            
        Returns:
            ID do registro inserido
        """
        query = """
            INSERT INTO rag_evaluations (
                question, answer, context, 
                faithfulness, answer_relevancy, context_precision, overall_score,
                evaluation_summary,
                session_id, user_id, chunks_retrieved, search_mode, adaptive_used,
                created_at
            ) VALUES (
                %(question)s, %(answer)s, %(context)s,
                %(faithfulness)s, %(answer_relevancy)s, %(context_precision)s, %(overall_score)s,
                %(evaluation_summary)s,
                %(session_id)s, %(user_id)s, %(chunks_retrieved)s, %(search_mode)s, %(adaptive_used)s,
                NOW()
            ) RETURNING id
        """
        
        params = {
            'question': question,
            'answer': answer,
            'context': context,
            'faithfulness': scores.get('faithfulness'),
            'answer_relevancy': scores.get('answer_relevancy'),
            'context_precision': scores.get('context_precision'),
            'overall_score': scores.get('overall_score', 0),
            'evaluation_summary': scores.get('evaluation_summary', ''),
            'session_id': session_id,
            'user_id': user_id,
            'chunks_retrieved': chunks_retrieved,
            'search_mode': search_mode,
            'adaptive_used': adaptive_used
        }
        
        result = self.execute_query(query, params)
        return result[0]['id'] if result else None
    
    def get_stats(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Retorna estatísticas agregadas das avaliações.
        
        Args:
            days: Número de dias para filtrar (default: 7)
            
        Returns:
            Dict com estatísticas agregadas
        """
        query = """
            SELECT 
                COUNT(*) as total_evaluations,
                AVG(overall_score) as avg_score,
                AVG(faithfulness) as avg_faithfulness,
                AVG(answer_relevancy) as avg_relevancy,
                AVG(context_precision) as avg_precision,
                MIN(overall_score) as min_score,
                MAX(overall_score) as max_score,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY overall_score) as median_score
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL '%s days'
        """
        
        result = self.execute_query(query, (days,))
        return result[0] if result else {}
    
    def get_trends(
        self,
        days: int = 30,
        group_by: str = 'day'
    ) -> List[Dict[str, Any]]:
        """
        Retorna tendência temporal de qualidade.
        
        Args:
            days: Número de dias para analisar
            group_by: Como agrupar ('day', 'week')
            
        Returns:
            Lista de pontos temporais com métricas
        """
        if group_by == 'day':
            date_format = 'YYYY-MM-DD'
            date_trunc = 'DATE(created_at)'
        else:
            date_format = 'YYYY-"W"WW'
            date_trunc = 'EXTRACT(WEEK FROM created_at)'
        
        query = f"""
            SELECT 
                TO_CHAR({date_trunc}, '{date_format}') as period,
                COUNT(*) as evaluations_count,
                AVG(overall_score) as avg_score,
                AVG(faithfulness) as avg_faithfulness,
                AVG(answer_relevancy) as avg_relevancy
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL %s days
            GROUP BY {date_trunc}
            ORDER BY period ASC
        """
        
        return self.execute_query(query, (days,))
    
    def get_recent_evaluations(
        self,
        limit: int = 50,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retorna avaliações recentes.
        
        Args:
            limit: Número máximo de registros
            min_score: Score mínimo para filtrar
            
        Returns:
            Lista de avaliações recentes
        """
        query = """
            SELECT 
                id, question, answer, overall_score,
                faithfulness, answer_relevancy, context_precision,
                evaluation_summary, created_at
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """
        
        params = []
        if min_score is not None:
            query += " AND overall_score >= %s"
            params.append(min_score)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))
    
    def get_top_worst_queries(
        self,
        limit: int = 5,
        days: int = 7
    ) -> Dict[str, List[Dict]]:
        """
        Retorna as piores queries (para identificar problemas).
        
        Returns:
            Dict com 'best' e 'worst' queries
        """
        query = """
            (SELECT 
                'best' as category,
                question, overall_score, created_at
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL %s days
            ORDER BY overall_score DESC
            LIMIT %s)
            
            UNION ALL
            
            (SELECT 
                'worst' as category,
                question, overall_score, created_at
            FROM rag_evaluations
            WHERE created_at >= NOW() - INTERVAL %s days
            ORDER BY overall_score ASC
            LIMIT %s)
        """
        
        results = self.execute_query(query, (days, limit, days, limit))
        
        return {
            'best': [r for r in results if r['category'] == 'best'],
            'worst': [r for r in results if r['category'] == 'worst']
        }
    
    def delete_old_evaluations(self, days: int = 90) -> int:
        """
        Remove avaliações antigas para economizar espaço.
        
        Args:
            days: Número de dias para manter
            
        Returns:
            Número de registros deletados
        """
        query = """
            DELETE FROM rag_evaluations
            WHERE created_at < NOW() - INTERVAL %s days
            RETURNING COUNT(*)
        """
        
        result = self.execute_query(query, (days,))
        return result[0]['count'] if result else 0


# Instância global
evaluation_repo = EvaluationRepository()
```

#### 1.3 Atualizar Repositories

**Arquivo:** `src/data/repositories/__init__.py`

```python
# Adicionar import
from .evaluation_repository import evaluation_repo, EvaluationRepository

# Adicionar export
__all__ = [
    # ... outros
    "evaluation_repo",
    "EvaluationRepository"
]
```

**Validação:**
```python
# Testar import
from src.data.repositories import evaluation_repo
print(evaluation_repo)
```

**Checklist Fase 1:**
- [ ] Criar migration para tabela `rag_evaluations`
- [ ] Aplicar migration (`alembic upgrade head`)
- [ ] Criar `evaluation_repository.py`
- [ ] Implementar métodos do repository
- [ ] Atualizar `__init__.py` dos repositories
- [ ] Testar criação de tabela
- [ ] Testar repository com operações básicas

---

## 🔄 Fase 2: Backend - Integração com Pipeline RAG

### Objetivo
Integrar avaliação automática no pipeline RAG existente

### Tarefas

#### 2.1 Modificar Configuração

**Arquivo:** `src/config.py`

```python
# Adicionar ao class Settings:

# Evaluation System
ENABLE_AUTO_EVALUATION: bool = Field(
    default=False, 
    validation_alias="ENABLE_AUTO_EVALUATION"
)
ENABLE_EVALUATION_UI: bool = Field(
    default=True, 
    validation_alias="ENABLE_EVALUATION_UI"
)
EVALUATION_MIN_SCORE_THRESHOLD: float = 0.4  # Mínimo para considerar avaliação válida

# Exportar para compatibilidade
ENABLE_AUTO_EVALUATION = settings.ENABLE_AUTO_EVALUATION
ENABLE_EVALUATION_UI = settings.ENABLE_EVALUATION_UI
EVALUATION_MIN_SCORE_THRESHOLD = settings.EVALUATION_MIN_SCORE_THRESHOLD
```

#### 2.2 Modificar Pipeline Principal

**Arquivo:** `src/core/rag/pipeline.py`

```python
# Adicionar imports
from src.core.evaluation import evaluate_rag_response
from src.data.repositories import evaluation_repo
from src.config import ENABLE_AUTO_EVALUATION, EVALUATION_MIN_SCORE_THRESHOLD

# No método RAGPipeline.query(), após gerar a resposta:

# 7.5. Auto-avaliação (opcional)
evaluation_metrics = {}
if ENABLE_AUTO_EVALUATION:
    with LatencyTracker("evaluation"):
        # Avaliar resposta
        evaluation_result = evaluate_rag_response(
            question=question,
            answer=answer,
            context=raw_context,
            chunks=documents
        )
        
        # Filtrar avaliações muito baixas
        if evaluation_result["overall_score"] >= EVALUATION_MIN_SCORE_THRESHOLD:
            evaluation_metrics = evaluation_result
            
            # Salvar no banco (assíncrono para não impactar performance)
            try:
                evaluation_repo.save_evaluation(
                    question=question,
                    answer=answer,
                    context=raw_context,
                    scores=evaluation_result,
                    session_id=collection_id,  # Usando collection_id temporariamente
                    chunks_retrieved=len(documents),
                    search_mode=search_mode,
                    adaptive_used=adaptive_metrics.get("applied", False)
                )
                logger.debug(f"Evaluation saved: score={evaluation_result['overall_score']:.2%}")
            except Exception as e:
                logger.warning(f"Failed to save evaluation: {e}")

# 8. Formatar resposta (já existe, apenas adicionar evaluation_metrics)
return self.responses.format_response(
    answer=answer,
    documents=documents if include_sources else [],
    question_type=question_type,
    was_compressed=context_result["was_compressed"],
    search_metrics=search_metrics,
    self_rag_metrics=self_rag_metrics,
    adaptive_params_used=adaptive_metrics,
    evaluation_metrics=evaluation_metrics,  # NOVO
    duration=total_duration
)
```

#### 2.3 Modificar Response Service

**Arquivo:** `src/core/rag/services/response_service.py`

```python
# Modificar format_response para incluir evaluation_metrics

def format_response(
    self,
    answer: str,
    documents: List[Dict],
    question_type: str,
    was_compressed: bool,
    search_metrics: Dict,
    self_rag_metrics: Dict,
    adaptive_params_used: Dict,
    evaluation_metrics: Dict = None,  # NOVO PARÂMETRO
    duration: float
) -> Dict[str, Any]:
    """Formata a resposta final do RAG."""
    
    # ... código existente ...
    
    result = {
        "answer": answer,
        # ... outros campos ...
        "evaluation": evaluation_metrics  # NOVO
    }
    
    return result
```

**Validação:**
```bash
# Testar com auto-avaliação desativada
export ENABLE_AUTO_EVALUATION=false
curl -X POST http://localhost:5000/api/query -H "Content-Type: application/json" \
  -d '{"question": "Test question", "include_explanation": false}'

# Testar com auto-avaliação ativada
export ENABLE_AUTO_EVALUATION=true
curl -X POST http://localhost:5000/api/query -H "Content-Type: application/json" \
  -d '{"question": "Test question", "include_explanation": false}'

# Verificar se foi salvo no banco
psql -h localhost -p 5433 -U postgres -d ragdb -c \
  "SELECT * FROM rag_evaluations ORDER BY created_at DESC LIMIT 5"
```

**Checklist Fase 2:**
- [ ] Adicionar configurações `ENABLE_AUTO_EVALUATION` e `ENABLE_EVALUATION_UI`
- [ ] Modificar `rag/pipeline.py` para chamar `evaluate_rag_response()`
- [ ] Salvar avaliações no banco via `evaluation_repo`
- [ ] Adicionar `evaluation_metrics` ao response
- [ ] Testar com `ENABLE_AUTO_EVALUATION=false`
- [ ] Testar com `ENABLE_AUTO_EVALUATION=true`
- [ ] Verificar performance da avaliação automática

---

## 🌐 Fase 3: Backend - API Endpoints

### Objetivo
Criar endpoints para consulta de métricas de qualidade

### Tarefas

#### 3.1 Criar Blueprint de Métricas de Qualidade

**Arquivo:** `src/api/routes/quality_metrics.py`

```python
"""Blueprint para métricas de qualidade de respostas RAG."""
import logging
from flask import Blueprint, jsonify, request

from src.data.repositories import evaluation_repo
from src.core.evaluation import evaluate_rag_response
from src.api.middleware.rate_limiter import limiter, LIMITS
from src.core.logger import api_logger, log_api_request, log_api_response
import time

quality_bp = Blueprint("quality_metrics", __name__)


@quality_bp.route("/stats", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_quality_stats():
    """
    Retorna estatísticas agregadas de qualidade.
    
    Query Params:
        - days: Número de dias para filtrar (default: 7)
        
    Returns:
        Dict com médias, min, max, median das métricas
    """
    start_time = time.time()
    days = request.args.get('days', 7, type=int)
    
    try:
        stats = evaluation_repo.get_stats(days=days)
        
        log_api_response("/api/metrics/quality/stats", 200, time.time() - start_time)
        return jsonify(stats)
        
    except Exception as e:
        api_logger.error(f"Error getting quality stats: {e}")
        log_api_response("/api/metrics/quality/stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/recent", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_recent_evaluations():
    """
    Retorna avaliações recentes.
    
    Query Params:
        - limit: Número máximo de registros (default: 50)
        - min_score: Score mínimo para filtrar (opcional)
        
    Returns:
        Lista de avaliações recentes
    """
    start_time = time.time()
    limit = request.args.get('limit', 50, type=int)
    min_score = request.args.get('min_score', type=float)
    
    try:
        evaluations = evaluation_repo.get_recent_evaluations(limit, min_score)
        
        log_api_response("/api/metrics/quality/recent", 200, time.time() - start_time)
        return jsonify({"evaluations": evaluations})
        
    except Exception as e:
        api_logger.error(f"Error getting recent evaluations: {e}")
        log_api_response("/api/metrics/quality/recent", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/trends", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_quality_trends():
    """
    Retorna tendência temporal de qualidade.
    
    Query Params:
        - days: Número de dias para analisar (default: 30)
        - group_by: 'day' ou 'week' (default: 'day')
        
    Returns:
        Lista de pontos temporais com métricas
    """
    start_time = time.time()
    days = request.args.get('days', 30, type=int)
    group_by = request.args.get('group_by', 'day', type=str)
    
    try:
        trends = evaluation_repo.get_trends(days, group_by)
        
        log_api_response("/api/metrics/quality/trends", 200, time.time() - start_time)
        return jsonify({"trends": trends})
        
    except Exception as e:
        api_logger.error(f"Error getting quality trends: {e}")
        log_api_response("/api/metrics/quality/trends", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/top-worst", methods=["GET"])
@limiter.limit(LIMITS["health"])
def get_top_worst():
    """
    Retorna as melhores e piores queries.
    
    Query Params:
        - limit: Número de registros (default: 5)
        - days: Período em dias (default: 7)
        
    Returns:
        Dict com 'best' e 'worst' queries
    """
    start_time = time.time()
    limit = request.args.get('limit', 5, type=int)
    days = request.args.get('days', 7, type=int)
    
    try:
        top_worst = evaluation_repo.get_top_worst_queries(limit, days)
        
        log_api_response("/api/metrics/quality/top-worst", 200, time.time() - start_time)
        return jsonify(top_worst)
        
    except Exception as e:
        api_logger.error(f"Error getting top/worst queries: {e}")
        log_api_response("/api/metrics/quality/top-worst", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@quality_bp.route("/evaluate", methods=["POST"])
@limiter.limit(LIMITS["query"])
def evaluate_response_endpoint():
    """
    Avalia uma resposta sob demanda.
    
    Body:
        - question: Pergunta original
        - answer: Resposta gerada
        - context: Contexto usado
        - chunks: Chunks recuperados (opcional)
        
    Returns:
        Dict com scores da avaliação
    """
    start_time = time.time()
    data = request.get_json() or {}
    
    # Validar campos obrigatórios
    required_fields = ['question', 'answer', 'context']
    for field in required_fields:
        if field not in data:
            log_api_response("/api/metrics/quality/evaluate", 400, time.time() - start_time)
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        # Avaliar
        result = evaluate_rag_response(
            question=data['question'],
            answer=data['answer'],
            context=data['context'],
            chunks=data.get('chunks')
        )
        
        # Salvar se habilitado
        from src.config import ENABLE_AUTO_EVALUATION
        if ENABLE_AUTO_EVALUATION:
            evaluation_repo.save_evaluation(
                question=data['question'],
                answer=data['answer'],
                context=data['context'],
                scores=result,
                user_id=data.get('user_id'),
                chunks_retrieved=len(data.get('chunks', []))
            )
        
        log_api_response("/api/metrics/quality/evaluate", 200, time.time() - start_time)
        return jsonify(result)
        
    except Exception as e:
        api_logger.error(f"Error evaluating response: {e}")
        log_api_response("/api/metrics/quality/evaluate", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
```

#### 3.2 Registrar Blueprint Principal

**Arquivo:** `src/api/routes/__init__.py`

```python
# Adicionar import
from src.api.routes.quality_metrics import quality_bp

# Registrar blueprint
api.register_blueprint(quality_bp, url_prefix="/metrics/quality")
```

**Validação de Endpoints:**

```bash
# Testar estatísticas
curl http://localhost:5000/api/metrics/quality/stats?days=7

# Testar avaliações recentes
curl http://localhost:5000/api/metrics/quality/recent?limit=10

# Testar tendências
curl http://localhost:5000/api/metrics/quality/trends?days=30&group_by=day

# Testar top/worst
curl http://localhost:5000/api/metrics/quality/top-worst?limit=3

# Testar avaliação manual
curl -X POST http://localhost:5000/api/metrics/quality/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é o preço do produto?",
    "answer": "O produto custa R$ 100,00.",
    "context": "O preço do produto X é R$ 100,00 conforme tabela de preços.",
    "chunks": [{"content": "O preço do produto X é R$ 100,00"}]
  }'
```

**Checklist Fase 3:**
- [ ] Criar `quality_metrics.py` blueprint
- [ ] Implementar `/stats` endpoint
- [ ] Implementar `/recent` endpoint
- [ ] Implementar `/trends` endpoint
- [ ] Implementar `/top-worst` endpoint
- [ ] Implementar `/evaluate` endpoint (POST)
- [ ] Registrar blueprint em `__init__.py`
- [ ] Testar todos os endpoints manualmente
- [ ] Documentar endpoints em README

---

## 🎨 Fase 4: Frontend - Dashboard Administrativo

### Objetivo
Criar dashboard para visualização de métricas históricas

### Tarefas

#### 4.1 Criar Componente de Métricas

**Arquivo:** `frontend/src/components/admin/QualityMetricsPanel.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { api } from '../../api';

interface QualityStats {
  total_evaluations: number;
  avg_score: number;
  avg_faithfulness: number;
  avg_relevancy: number;
  avg_precision: number;
  min_score: number;
  max_score: number;
  median_score: number;
}

interface TrendPoint {
  period: string;
  evaluations_count: number;
  avg_score: number;
  avg_faithfulness: number;
  avg_relevancy: number;
}

export default function QualityMetricsPanel() {
  const [stats, setStats] = useState<QualityStats | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [recent, setRecent] = useState<any[]>([]);
  const [topWorst, setTopWorst] = useState<{ best: any[]; worst: any[] }>({ best: [], worst: [] });
  const [loading, setLoading] = useState(true);
  const [daysFilter, setDaysFilter] = useState(7);

  useEffect(() => {
    fetchMetrics();
  }, [daysFilter]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      // Buscar estatísticas
      const statsRes = await api.get(`/metrics/quality/stats?days=${daysFilter}`);
      setStats(statsRes.data);

      // Buscar tendências
      const trendsRes = await api.get(`/metrics/quality/trends?days=${daysFilter}&group_by=day`);
      setTrends(trendsRes.data.trends);

      // Buscar avaliações recentes
      const recentRes = await api.get(`/metrics/quality/recent?limit=20`);
      setRecent(recentRes.data.evaluations);

      // Buscar top/worst
      const topWorstRes = await api.get(`/metrics/quality/top-worst?limit=5&days=${daysFilter}`);
      setTopWorst(topWorstRes.data);
    } catch (error) {
      console.error('Error fetching quality metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-500';
    if (score >= 0.6) return 'text-blue-500';
    if (score >= 0.4) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getQualityLabel = (score: number) => {
    if (score >= 0.8) return 'Excelente';
    if (score >= 0.6) return 'Boa';
    if (score >= 0.4) return 'Moderada';
    return 'Precisa melhorar';
  };

  if (loading || !stats) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          📊 Métricas de Qualidade RAG
        </h2>
        <select
          value={daysFilter}
          onChange={(e) => setDaysFilter(Number(e.target.value))}
          className="border rounded-lg px-4 py-2"
        >
          <option value={1}>Últimas 24h</option>
          <option value={7}>Últimos 7 dias</option>
          <option value={30}>Últimos 30 dias</option>
          <option value={90}>Últimos 90 dias</option>
        </select>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Total de Avaliações</div>
          <div className="text-3xl font-bold text-gray-900 dark:text-white">
            {stats.total_evaluations.toLocaleString()}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Score Médio Geral</div>
          <div className={`text-3xl font-bold ${getScoreColor(stats.avg_score)}`}>
            {(stats.avg_score * 100).toFixed(1)}%
          </div>
          <div className="text-sm mt-1">
            {getQualityLabel(stats.avg_score)}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Fidelidade Média</div>
          <div className={`text-3xl font-bold ${getScoreColor(stats.avg_faithfulness)}`}>
            {(stats.avg_faithfulness * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <div className="text-sm text-gray-500">Relevância Média</div>
          <div className={`text-3xl font-bold ${getScoreColor(stats.avg_relevancy)}`}>
            {(stats.avg_relevancy * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Gráfico de Tendência */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">📈 Tendência de Qualidade</h3>
        <div className="h-64">
          <LineChart
            width={800}
            height={256}
            data={trends}
            xKey="period"
            yKeys={['avg_score']}
            colors={['#3B82F6']}
          />
        </div>
      </div>

      {/* Top e Worst Queries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Melhores Queries */}
        <div className="bg-green-50 dark:bg-green-900 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">✅ Top Queries (Melhores)</h3>
          <div className="space-y-3">
            {topWorst.best.map((item, idx) => (
              <div key={idx} className="bg-white dark:bg-gray-800 p-3 rounded">
                <div className="flex justify-between">
                  <span className="text-sm font-medium">
                    {item.question.substring(0, 60)}...
                  </span>
                  <span className="text-green-600 font-bold">
                    {(item.overall_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Piores Queries */}
        <div className="bg-red-50 dark:bg-red-900 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">❌ Queries Problemáticas (Piores)</h3>
          <div className="space-y-3">
            {topWorst.worst.map((item, idx) => (
              <div key={idx} className="bg-white dark:bg-gray-800 p-3 rounded">
                <div className="flex justify-between">
                  <span className="text-sm font-medium">
                    {item.question.substring(0, 60)}...
                  </span>
                  <span className="text-red-600 font-bold">
                    {(item.overall_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Avaliações Recentes */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">📋 Avaliações Recentes</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-2 text-left">Pergunta</th>
                <th className="px-4 py-2 text-center">Score</th>
                <th className="px-4 py-2 text-center">Fidelidade</th>
                <th className="px-4 py-2 text-center">Relevância</th>
                <th className="px-4 py-2 text-center">Precisão</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((eval, idx) => (
                <tr key={idx} className="border-b">
                  <td className="px-4 py-2">
                    {eval.question.substring(0, 80)}...
                  </td>
                  <td className={`px-4 py-2 text-center font-bold ${getScoreColor(eval.overall_score)}`}>
                    {(eval.overall_score * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-2 text-center">
                    {eval.faithfulness ? (eval.faithfulness * 100).toFixed(1) + '%' : '-'}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {eval.answer_relevancy ? (eval.answer_relevancy * 100).toFixed(1) + '%' : '-'}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {eval.context_precision ? (eval.context_precision * 100).toFixed(1) + '%' : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

#### 4.2 Integrar no Admin Dashboard

**Arquivo:** `frontend/src/components/AdminDashboard.tsx`

```typescript
// Adicionar import
import QualityMetricsPanel from './admin/QualityMetricsPanel';

// Adicionar estado
const [activeTab, setActiveTab] = useState('overview');

// Adicionar botão na tab bar
<button
  onClick={() => setActiveTab('quality')}
  className={`px-4 py-2 rounded-lg ${activeTab === 'quality' ? 'bg-blue-500 text-white' : ''}`}
>
  📊 Qualidade
</button>

// Adicionar conteúdo no render
{activeTab === 'quality' && <QualityMetricsPanel />}
```

**Checklist Fase 4:**
- [ ] Criar `QualityMetricsPanel.tsx`
- [ ] Implementar estatísticas gerais (cards)
- [ ] Implementar gráfico de tendências
- [ ] Implementar tabela de avaliações recentes
- [ ] Implementar seção top/worst
- [ ] Adicionar filtros por período
- [ ] Integrar no Admin Dashboard
- [ ] Testar renderização e responsividade

---

## 💬 Fase 5: Frontend - Interface de Chat

### Objetivo
Adicionar botão de avaliação na interface de chat

### Tarefas

#### 5.1 Criar Modal de Avaliação

**Arquivo:** `frontend/src/components/EvaluationModal.tsx`

```typescript
import React from 'react';

interface EvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  question: string;
  answer: string;
  evaluation: {
    faithfulness?: number;
    answer_relevancy?: number;
    context_precision?: number;
    overall_score: number;
    evaluation_summary?: string;
  };
}

export default function EvaluationModal({ isOpen, onClose, question, answer, evaluation }: EvaluationModalProps) {
  if (!isOpen) return null;

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-50';
    if (score >= 0.6) return 'text-blue-600 bg-blue-50';
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.8) return 'Excelente';
    if (score >= 0.6) return 'Boa';
    if (score >= 0.4) return 'Moderada';
    return 'Precisa melhorar';
  };

  const getProgressBar = (score: number) => {
    const percentage = score * 100;
    const color = score >= 0.6 ? 'bg-green-500' : score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500';
    return (
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            📊 Avaliação da Resposta
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Score Geral */}
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-2">Qualidade Geral</div>
            <div className={`text-6xl font-bold mb-2 ${getScoreColor(evaluation.overall_score).split(' ')[0]}`}>
              {(evaluation.overall_score * 100).toFixed(0)}%
            </div>
            <div className="text-lg font-medium text-gray-700 dark:text-gray-300">
              {getScoreLabel(evaluation.overall_score)}
            </div>
            {getProgressBar(evaluation.overall_score)}
          </div>

          {/* Métricas Individuais */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Fidelidade */}
            {evaluation.faithfulness !== undefined && (
              <div className="bg-green-50 dark:bg-green-900 rounded-lg p-4">
                <div className="flex items-center mb-2">
                  <span className="text-2xl mr-2">✅</span>
                  <div className="text-sm text-gray-500">Fidelidade ao Contexto</div>
                </div>
                <div className={`text-4xl font-bold ${getScoreColor(evaluation.faithfulness).split(' ')[0]}`}>
                  {(evaluation.faithfulness * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  A resposta é baseada no contexto fornecido
                </div>
                {getProgressBar(evaluation.faithfulness)}
              </div>
            )}

            {/* Relevância */}
            {evaluation.answer_relevancy !== undefined && (
              <div className="bg-blue-50 dark:bg-blue-900 rounded-lg p-4">
                <div className="flex items-center mb-2">
                  <span className="text-2xl mr-2">🎯</span>
                  <div className="text-sm text-gray-500">Relevância à Pergunta</div>
                </div>
                <div className={`text-4xl font-bold ${getScoreColor(evaluation.answer_relevancy).split(' ')[0]}`}>
                  {(evaluation.answer_relevancy * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  A resposta aborda diretamente o que foi perguntado
                </div>
                {getProgressBar(evaluation.answer_relevancy)}
              </div>
            )}

            {/* Precisão do Contexto */}
            {evaluation.context_precision !== undefined && (
              <div className="bg-purple-50 dark:bg-purple-900 rounded-lg p-4">
                <div className="flex items-center mb-2">
                  <span className="text-2xl mr-2">🎯</span>
                  <div className="text-sm text-gray-500">Precisão dos Chunks</div>
                </div>
                <div className={`text-4xl font-bold ${getScoreColor(evaluation.context_precision).split(' ')[0]}`}>
                  {(evaluation.context_precision * 100).toFixed(0)}%
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  Os chunks recuperados são relevantes
                </div>
                {getProgressBar(evaluation.context_precision)}
              </div>
            )}
          </div>

          {/* Pergunta e Resposta */}
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
            <div className="mb-4">
              <div className="text-sm font-medium text-gray-500 mb-1">❓ Pergunta</div>
              <div className="text-gray-900 dark:text-white">{question}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500 mb-1">💬 Resposta</div>
              <div className="text-gray-900 dark:text-white">{answer}</div>
            </div>
          </div>

          {/* Sumário */}
          {evaluation.evaluation_summary && (
            <div className="bg-yellow-50 dark:bg-yellow-900 rounded-lg p-4">
              <div className="flex items-center mb-2">
                <span className="text-2xl mr-2">💡</span>
                <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Observação
                </div>
              </div>
              <div className="text-gray-900 dark:text-white">
                {evaluation.evaluation_summary}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex justify-end">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

#### 5.2 Modificar MessageList

**Arquivo:** `frontend/src/components/MessageList.tsx`

```typescript
// Adicionar state para modal de avaliação
const [evaluationModalOpen, setEvaluationModalOpen] = useState(false);
const [currentEvaluation, setCurrentEvaluation] = useState<any>(null);

// Adicionar função para abrir avaliação
const handleEvaluate = async (message: any) => {
  try {
    // Chamar endpoint de avaliação
    const response = await api.post('/metrics/quality/evaluate', {
      question: message.question,
      answer: message.answer,
      context: message.context,
      chunks: message.sources
    });
    
    setCurrentEvaluation({
      question: message.question,
      answer: message.answer,
      evaluation: response.data
    });
    setEvaluationModalOpen(true);
  } catch (error) {
    console.error('Error evaluating response:', error);
    // Mostrar toast de erro
  }
};

// Adicionar botão de avaliação ao lado de cada mensagem de assistente
{message.role === 'assistant' && (
  <div className="flex gap-2 mt-2">
    {/* Botão de explicação (já existe) */}
    {message.explanation && (
      <button
        onClick={() => setShowExplanation(message.id)}
        className="px-3 py-1 text-sm bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded hover:bg-purple-200"
      >
        ✨ Explicação
      </button>
    )}
    
    {/* Novo botão de avaliação */}
    <button
      onClick={() => handleEvaluate(message)}
      className="px-3 py-1 text-sm bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded hover:bg-green-200"
      title="Avaliar qualidade da resposta"
    >
      📊 Avaliar
    </button>
  </div>
)}

// Adicionar modal ao final do componente
<EvaluationModal
  isOpen={evaluationModalOpen}
  onClose={() => setEvaluationModalOpen(false)}
  question={currentEvaluation?.question || ''}
  answer={currentEvaluation?.answer || ''}
  evaluation={currentEvaluation?.evaluation || {}}
/>
```

**Checklist Fase 5:**
- [ ] Criar `EvaluationModal.tsx`
- [ ] Implementar visualização de scores
- [ ] Implementar progress bars
- [ ] Implementar cores baseadas em scores
- [ ] Adicionar botão em `MessageList.tsx`
- [ ] Implementar chamada ao endpoint `/evaluate`
- [ ] Testar modal de avaliação
- [ ] Testar integração com chat

---

## ⚙️ Fase 6: Configuração e Documentação

### Objetivo
Adicionar configurações e atualizar documentação

### Tarefas

#### 6.1 Atualizar Arquivo .env.example

**Arquivo:** `.env.example`

```bash
# ... configurações existentes ...

# ===========================================================================
# Evaluation System (Fase 9)
# ===========================================================================
# Avaliação automática de respostas RAG
ENABLE_AUTO_EVALUATION=false

# UI de avaliação no chat
ENABLE_EVALUATION_UI=true

# Threshold mínimo para considerar avaliação válida
EVALUATION_MIN_SCORE_THRESHOLD=0.4
```

#### 6.2 Atualizar README

**Arquivo:** `README.md`

Adicionar seção nova após "Funcionalidades Principais":

```markdown
### 📊 Sistema de Avaliação de Qualidade
- **Avaliação Automática**: Avalia respostas automaticamente (opcional)
- **Dashboard de Métricas**: Visibilidade histórica da qualidade (Admin)
- **Botão de Avaliação**: Usuários podem avaliar respostas sob demanda
- **Métricas RAGAS**:
  - Faithfulness: Fidelidade ao contexto
  - Answer Relevancy: Relevância à pergunta
  - Context Precision: Precisão dos chunks recuperados
  - Overall Score: Score geral combinado
- **Tendências**: Monitoramento temporal de qualidade
- **Top/Worst Queries**: Identificação de queries problemáticas e exemplares
- **Filtros por Período**: 24h, 7 dias, 30 dias
```

Adicionar endpoints em "API Endpoints":

```markdown
### Métricas de Qualidade

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/metrics/quality/stats` | GET | Estatísticas agregadas |
| `/api/metrics/quality/recent` | GET | Avaliações recentes |
| `/api/metrics/quality/trends` | GET | Tendência temporal |
| `/api/metrics/quality/top-worst` | GET | Top e piores queries |
| `/api/metrics/quality/evaluate` | POST | Avaliação sob demanda |
```

#### 6.3 Criar Guia de Uso

**Arquivo:** `docs/evaluation_system_guide.md`

```markdown
# Guia de Uso - Evaluation System

## 1. Habilitando o Sistema

### Avaliação Automática

Para habilitar a avaliação automática de todas as respostas:

```bash
# Adicionar ao .env
ENABLE_AUTO_EVALUATION=true

# Reiniciar aplicação
python run_app.py
```

### UI de Avaliação no Chat

Para habilitar o botão de avaliação no chat:

```bash
# Adicionar ao .env
ENABLE_EVALUATION_UI=true

# Reiniciar frontend
cd frontend
npm run dev
```

## 2. Usando o Dashboard Administrativo

1. Acesse o Admin Dashboard
2. Clique na aba "📊 Qualidade"
3. Use os filtros por período (24h, 7d, 30d, 90d)
4. Analise:
   - Cards de resumo (total, score médio, etc.)
   - Gráfico de tendências
   - Top queries (melhores e piores)
   - Tabela de avaliações recentes

## 3. Avaliando Respostas no Chat

### Avaliação Manual

1. Faça uma pergunta no chat
2. Após receber a resposta, clique no botão "📊 Avaliar"
3. O modal mostrará:
   - Score geral (0-100%)
   - Fidelidade ao contexto
   - Relevância à pergunta
   - Precisão dos chunks
4. Leia a observação (se houver)

### Avaliação Automática

Se `ENABLE_AUTO_EVALUATION=true`, todas as respostas são automaticamente:
1. Avaliadas após serem geradas
2. Salvas no banco de dados
3. Disponíveis no dashboard administrativo

## 4. Interpretando os Scores

| Score | Qualidade | Ação |
|--------|------------|--------|
| 80-100% | Excelente | Manter configurações |
| 60-79% | Boa | Monitorar tendência |
| 40-59% | Moderada | Investigar causas |
| 0-39% | Ruim | Ajustar prompts/config |

## 5. Usando as Métricas para Melhorias

### Identificando Problemas

1. **Score baixo de Fidelidade**: Respostas inventando informações
   - Solução: Melhorar contexto ou prompts

2. **Score baixo de Relevância**: Respostas fora do escopo
   - Solução: Ajustar question_classifier

3. **Score baixo de Precisão**: Chunks irrelevantes
   - Solução: Ajustar top_k ou min_similarity

### Melhores Práticas

1. Monitorar tendências semanais
2. Investigar queries com score < 40%
3. Comparar antes/depois de mudanças
4. Ajustar configurações baseado em dados
5. Manter histórico de alterações
```

**Checklist Fase 6:**
- [ ] Atualizar `.env.example`
- [ ] Adicionar seção ao README
- [ ] Atualizar lista de endpoints no README
- [ ] Criar guia de uso
- [ ] Documentar configurações
- [ ] Adicionar exemplos de uso

---

## 🧪 Fase 7: Testes

### Objetivo
Garantir qualidade e funcionalidade

### Tarefas

#### 7.1 Testes Unitários

**Arquivo:** `tests/test_evaluation_system.py`

```python
"""Testes do sistema de avaliação."""
import pytest
from src.core.evaluation import (
    calculate_faithfulness,
    calculate_answer_relevancy,
    calculate_context_precision,
    evaluate_rag_response
)

def test_calculate_faithfulness():
    """Testa cálculo de fidelidade."""
    answer = "O sistema usa PostgreSQL e pgvector."
    context = "O sistema RAG é construído com PostgreSQL e extensão pgvector para busca vetorial."
    
    result = calculate_faithfulness(answer, context)
    
    assert 0 <= result <= 1.0
    assert result > 0.5  # Deve ser fidelidade alta

def test_calculate_answer_relevancy():
    """Testa cálculo de relevância."""
    question = "Qual banco de dados é usado?"
    answer = "PostgreSQL com pgvector."
    
    result = calculate_answer_relevancy(question, answer)
    
    assert 0 <= result <= 1.0
    assert result > 0.5

def test_calculate_context_precision():
    """Testa cálculo de precisão do contexto."""
    question = "Qual o banco de dados?"
    chunks = [
        {"content": "PostgreSQL é usado", "similarity": 0.9},
        {"content": "MySQL não é usado", "similarity": 0.3}
    ]
    
    result = calculate_context_precision(question, chunks)
    
    assert 0 <= result <= 1.0
    assert result > 0.5

def test_evaluate_rag_response():
    """Testa avaliação completa."""
    question = "Qual tecnologia de embeddings?"
    answer = "BGE-M3"
    context = "O modelo BGE-M3 é usado para embeddings de 1024 dimensões."
    chunks = [{"content": "BGE-M3", "similarity": 0.95}]
    
    result = evaluate_rag_response(question, answer, context, chunks)
    
    assert "faithfulness" in result
    assert "answer_relevancy" in result
    assert "overall_score" in result
    assert 0 <= result["overall_score"] <= 1.0
```

Executar testes:
```bash
pytest tests/test_evaluation_system.py -v
```

#### 7.2 Testes de Integração

**Arquivo:** `tests/test_evaluation_integration.py`

```python
"""Testes de integração do sistema de avaliação."""
import pytest
from src.data.repositories import evaluation_repo
from src.core.evaluation import evaluate_rag_response

@pytest.fixture
def clean_evaluations():
    """Limpa avaliações antes de cada teste."""
    evaluation_repo.delete_old_evaluations(days=0)
    yield
    evaluation_repo.delete_old_evaluations(days=0)

def test_save_evaluation(clean_evaluations):
    """Testa salvamento de avaliação."""
    result = evaluate_rag_response(
        question="Teste",
        answer="Resposta teste",
        context="Contexto teste"
    )
    
    id = evaluation_repo.save_evaluation(
        question="Teste",
        answer="Resposta teste",
        context="Contexto teste",
        scores=result
    )
    
    assert id is not None
    
    # Verificar se foi salvo
    stats = evaluation_repo.get_stats(days=1)
    assert stats['total_evaluations'] >= 1

def test_get_stats(clean_evaluations):
    """Testa obtenção de estatísticas."""
    # Criar avaliações de teste
    for i in range(10):
        result = evaluate_rag_response(
            question=f"Pergunta {i}",
            answer=f"Resposta {i}",
            context=f"Contexto {i}"
        )
        evaluation_repo.save_evaluation(
            question=f"Pergunta {i}",
            answer=f"Resposta {i}",
            context=f"Contexto {i}",
            scores=result
        )
    
    stats = evaluation_repo.get_stats(days=1)
    
    assert stats['total_evaluations'] == 10
    assert 0 < stats['avg_score'] < 1.0
```

Executar testes:
```bash
pytest tests/test_evaluation_integration.py -v
```

#### 7.3 Testes Manuais

1. **Testar Dashboard:**
   - [ ] Abrir Admin Dashboard
   - [ ] Navegar para aba "Qualidade"
   - [ ] Verificar filtros de período
   - [ ] Verificar cards de estatísticas
   - [ ] Verificar gráfico de tendências
   - [ ] Verificar tabela de avaliações

2. **Testar Chat:**
   - [ ] Fazer uma pergunta no chat
   - [ ] Verificar botão "📊 Avaliar"
   - [ ] Clicar no botão
   - [ ] Verificar modal de avaliação
   - [ ] Verificar se scores são razoáveis

3. **Testar API:**
   ```bash
   # Testar todos os endpoints
   curl http://localhost:5000/api/metrics/quality/stats
   curl http://localhost:5000/api/metrics/quality/recent
   curl http://localhost:5000/api/metrics/quality/trends
   curl http://localhost:5000/api/metrics/quality/top-worst
   curl -X POST http://localhost:5000/api/metrics/quality/evaluate
   ```

**Checklist Fase 7:**
- [ ] Criar testes unitários
- [ ] Criar testes de integração
- [ ] Executar `pytest` e verificar覆盖率
- [ ] Testar dashboard manualmente
- [ ] Testar interface de chat
- [ ] Testar endpoints via curl
- [ ] Documentar bugs encontrados
- [ ] Corrigir issues críticos

---

## ✅ Fase 8: Deploy e Monitoramento

### Objetivo
Lançar em produção e monitorar

### Tarefas

#### 8.1 Preparação de Deploy

- [ ] Backup do banco de dados antes da migration
- [ ] Revisar configurações de produção
- [ ] Testar migration em ambiente de staging
- [ ] Validar performance da avaliação automática

#### 8.2 Deploy em Produção

- [ ] Aplicar migrations: `alembic upgrade head`
- [ ] Atualizar configurações no servidor
- [ ] Reiniciar serviços
- [ ] Verificar logs de erros

#### 8.3 Monitoramento Inicial

- [ ] Verificar se avaliações estão sendo salvas
- [ ] Validar métricas do dashboard
- [ ] Monitorar performance (overhead da avaliação)
- [ ] Coletar feedback dos usuários

#### 8.4 Otimizações Pós-Deploy

- [ ] Ajustar `EVALUATION_MIN_SCORE_THRESHOLD` se necessário
- [ ] Habilitar/desabilitar auto-avaliação baseado em feedback
- [ ] Otimizar queries SQL se houver lentidão
- [ ] Configurar limpeza automática de registros antigos

---

## 📊 Cronograma Estimado

| Fase | Duração Estimada | Dependências |
|-------|------------------|--------------|
| **Fase 1: Infraestrutura** | 4-6 horas | Nenhuma |
| **Fase 2: Integração Pipeline** | 6-8 horas | Fase 1 |
| **Fase 3: API Endpoints** | 4-6 horas | Fase 2 |
| **Fase 4: Dashboard Frontend** | 8-12 horas | Fase 3 |
| **Fase 5: Chat Interface** | 4-6 horas | Fase 3 |
| **Fase 6: Configuração** | 2-3 horas | Fase 4, 5 |
| **Fase 7: Testes** | 4-6 horas | Todas anteriores |
| **Fase 8: Deploy** | 2-4 horas | Todas anteriores |
| **TOTAL** | **34-51 horas** (~5-7 dias) |

---

## ⚠️ Pontos de Atenção

### Performance

**Avaliação automática adiciona overhead:**
- Tempo extra: ~100-200ms por query
- Custo adicional: 1-2 chamadas ao LLM por query
- **Recomendação**: Monitorar e desabilitar se impactar muito

### Storage

**Crescimento do banco:**
- ~1KB por avaliação
- 1000 queries/dia ≈ 1MB/dia
- **Solução**: Limpeza automática de registros > 90 dias

### Usabilidade

**Botão de avaliação:**
- Deve ser sutil (não incomodar usuário)
- Deve estar disponível apenas em respostas do assistente
- Deve mostrar loading durante avaliação

### Privacidade

**Dados coletados:**
- Perguntas (já são armazenadas no histórico)
- Respostas (já são armazenadas)
- Scores de avaliação (NOVO)
- **NÃO é coletado**: Identificação do usuário (a menos que autenticado)

---

## 🎯 Critérios de Sucesso

O sistema será considerado **implementado com sucesso** quando:

- [ ] Tabela `rag_evaluations` criada no banco
- [ ] Repository `evaluation_repository.py` funcional
- [ ] Avaliação automática integrada ao pipeline
- [ ] Endpoints API funcionando
- [ ] Dashboard administrativo visualizando métricas
- [ ] Botão de avaliação presente no chat
- [ ] Modal de avaliação exibindo scores
- [ ] Documentação atualizada
- [ ] Testes passando (mínimo 80% coverage)
- [ ] Deploy em produção sem bugs críticos
- [ ] Monitoramento ativo e funcionando

---

## 📝 Resumo Final

Este plano implementa o **Evaluation System** de forma completa, proporcionando:

1. **Monitoramento Contínuo**: Dashboard administrativo com métricas históricas
2. **Transparência**: Botão de avaliação no chat para usuários
3. **Qualidade**: Sistema baseado em RAGAS com métricas validadas
4. **Flexibilidade**: Habilitável/desabilitável via configuração
5. **Escalabilidade**: Arquitetura modular e performática

**Próximos Passos:**
1. Revisar e ajustar este plano conforme necessário
2. Começar pela Fase 1 (Infraestrutura)
3. Progressar sequencialmente pelas fases
4. Testar extensivamente antes do deploy
5. Coletar feedback pós-deploy para melhorias

---

**Documento criado:** 31/12/2025  
**Versão:** 1.0  
**Status:** Pronto para implementação
