import React, { useState, useEffect } from 'react';
import { API_URL } from '../../api';
import { useToast } from '../../hooks/useToast';
import './AdaptiveRetrievalMetrics.css'; // Reutilizando estilos do AdaptiveRetrievalMetrics

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

interface Evaluation {
  id: number;
  question: string;
  overall_score: number;
  faithfulness: number;
  answer_relevancy: number;
  context_precision: number;
  evaluation_summary: string;
  created_at: string;
}

interface TrendPoint {
  period: string;
  evaluations_count: number;
  avg_score: number;
  avg_faithfulness: number;
  avg_relevancy: number;
}

export const QualityMetricsPanel: React.FC = () => {
  const [stats, setStats] = useState<QualityStats | null>(null);
  const [recentEvaluations, setRecentEvaluations] = useState<Evaluation[]>([]);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [groupBy, setGroupBy] = useState<'day' | 'week'>('day');
  const [expandedEval, setExpandedEval] = useState<number | null>(null);
  const { showToast } = useToast();

  useEffect(() => {
    loadQualityMetrics();
  }, [days, groupBy]);

  const loadQualityMetrics = async () => {
    try {
      setLoading(true);

      // Carregar estatísticas gerais
      const statsRes = await fetch(`${API_URL}/metrics/quality/stats?days=${days}`);
      if (!statsRes.ok) throw new Error('Failed to fetch stats');
      const statsData = await statsRes.json();
      setStats(statsData);

      // Carregar avaliações recentes
      const recentRes = await fetch(`${API_URL}/metrics/quality/recent?limit=20`);
      if (!recentRes.ok) throw new Error('Failed to fetch recent evaluations');
      const recentData = await recentRes.json();
      setRecentEvaluations(recentData.evaluations);

      // Carregar tendências
      const trendsRes = await fetch(`${API_URL}/metrics/quality/trends?days=${days}&group_by=${groupBy}`);
      if (!trendsRes.ok) throw new Error('Failed to fetch trends');
      const trendsData = await trendsRes.json();
      setTrends(trendsData.trends);

    } catch (error) {
      console.error('Error loading quality metrics:', error);
      showToast('Erro ao carregar métricas de qualidade', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score: number): string => {
    return `${(score * 100).toFixed(1)}%`;
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'var(--color-success)';
    if (score >= 0.6) return 'var(--color-warning)';
    return 'var(--color-danger)';
  };

  if (loading) {
    return <div className="loading-spinner">Carregando métricas...</div>;
  }

  if (!stats) {
    return <div className="error-message">Não há dados disponíveis</div>;
  }

  return (
    <div className="adaptive-retrieval-panel">
      <div className="panel-header">
        <h2>Métricas de Qualidade RAG</h2>
        <div className="controls">
          <select 
            value={days} 
            onChange={(e) => setDays(Number(e.target.value))}
            className="period-select"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
          </select>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as 'day' | 'week')}
            className="groupby-select"
          >
            <option value="day">Diário</option>
            <option value="week">Semanal</option>
          </select>
          <button onClick={loadQualityMetrics} className="refresh-btn">
            Atualizar
          </button>
        </div>
      </div>

      {/* Cards de Estatísticas Gerais */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total de Avaliações</div>
          <div className="metric-value">{stats.total_evaluations}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Score Médio</div>
          <div 
            className="metric-value" 
            style={{ color: getScoreColor(stats.avg_score) }}
          >
            {formatScore(stats.avg_score)}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Fidelidade Média</div>
          <div 
            className="metric-value" 
            style={{ color: getScoreColor(stats.avg_faithfulness) }}
          >
            {formatScore(stats.avg_faithfulness)}
          </div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Relevância Média</div>
          <div 
            className="metric-value" 
            style={{ color: getScoreColor(stats.avg_relevancy) }}
          >
            {formatScore(stats.avg_relevancy)}
          </div>
        </div>
      </div>

      {/* Métricas Detalhadas */}
      <div className="detailed-metrics">
        <h3>Métricas Detalhadas</h3>
        <div className="detailed-grid">
          <div className="detailed-item">
            <span className="detailed-label">Score Mínimo:</span>
            <span className="detailed-value">{formatScore(stats.min_score)}</span>
          </div>
          <div className="detailed-item">
            <span className="detailed-label">Score Máximo:</span>
            <span className="detailed-value">{formatScore(stats.max_score)}</span>
          </div>
          <div className="detailed-item">
            <span className="detailed-label">Mediana:</span>
            <span className="detailed-value">{formatScore(stats.median_score)}</span>
          </div>
          <div className="detailed-item">
            <span className="detailed-label">Precisão de Contexto:</span>
            <span 
              className="detailed-value"
              style={{ color: getScoreColor(stats.avg_precision) }}
            >
              {formatScore(stats.avg_precision)}
            </span>
          </div>
        </div>
      </div>

      {/* Gráfico de Tendência */}
      <div className="trend-section">
        <h3>Tendência de Qualidade</h3>
        {trends.length > 0 ? (
          <div className="trend-chart">
            <table className="trend-table">
              <thead>
                <tr>
                  <th>Período</th>
                  <th>Avaliações</th>
                  <th>Score Médio</th>
                  <th>Fidelidade</th>
                  <th>Relevância</th>
                </tr>
              </thead>
              <tbody>
                {trends.map((trend, idx) => (
                  <tr key={idx}>
                    <td>{trend.period}</td>
                    <td>{trend.evaluations_count}</td>
                    <td style={{ color: getScoreColor(trend.avg_score) }}>
                      {formatScore(trend.avg_score)}
                    </td>
                    <td style={{ color: getScoreColor(trend.avg_faithfulness) }}>
                      {formatScore(trend.avg_faithfulness)}
                    </td>
                    <td style={{ color: getScoreColor(trend.avg_relevancy) }}>
                      {formatScore(trend.avg_relevancy)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-data">Sem dados de tendência</div>
        )}
      </div>

      {/* Avaliações Recentes */}
      <div className="recent-section">
        <h3>Avaliações Recentes</h3>
        {recentEvaluations.length > 0 ? (
          <div className="evaluations-list">
          {recentEvaluations.map((evaluation) => (
            <div 
              key={evaluation.id} 
              className={`evaluation-item ${expandedEval === evaluation.id ? 'expanded' : ''}`}
            >
              <div 
                className="evaluation-header"
                onClick={() => setExpandedEval(expandedEval === evaluation.id ? null : evaluation.id)}
              >
                <div className="evaluation-question">{evaluation.question}</div>
                <div 
                  className="evaluation-score"
                  style={{ 
                    backgroundColor: getScoreColor(evaluation.overall_score),
                    color: 'white',
                    padding: '4px 12px',
                    borderRadius: '4px',
                    fontWeight: 'bold'
                  }}
                >
                  {formatScore(evaluation.overall_score)}
                </div>
              </div>
              
              {expandedEval === evaluation.id && (
                <div className="evaluation-details">
                  <div className="detail-row">
                    <span className="detail-label">Fidelidade:</span>
                    <span 
                      className="detail-value"
                      style={{ color: getScoreColor(evaluation.faithfulness) }}
                    >
                      {formatScore(evaluation.faithfulness)}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Relevância:</span>
                    <span 
                      className="detail-value"
                      style={{ color: getScoreColor(evaluation.answer_relevancy) }}
                    >
                      {formatScore(evaluation.answer_relevancy)}
                    </span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Precisão do Contexto:</span>
                    <span 
                      className="detail-value"
                      style={{ color: getScoreColor(evaluation.context_precision) }}
                    >
                      {formatScore(evaluation.context_precision)}
                    </span>
                  </div>
                  {evaluation.evaluation_summary && (
                    <div className="detail-summary">
                      <span className="detail-label">Resumo da Avaliação:</span>
                      <p>{evaluation.evaluation_summary}</p>
                    </div>
                  )}
                  <div className="detail-date">
                    Criado em: {new Date(evaluation.created_at).toLocaleString('pt-BR')}
                  </div>
                </div>
              )}
            </div>
          ))}
          </div>
        ) : (
          <div className="no-data">Nenhuma avaliação recente</div>
        )}
      </div>
    </div>
  );
};

export default QualityMetricsPanel;
