import React, { useState, useEffect } from 'react';
import { RefreshCw, TrendingUp, Target, Activity } from 'lucide-react';
import { API_URL } from '../../api';
import { useToast } from '../../hooks/useToast';
import { createLogger } from '../../logger';

const logger = createLogger('QualityMetricsPanel');

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
      logger.error('Error loading quality metrics:', error);
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
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-primary"></div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-text-secondary">Não há dados disponíveis</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-semibold text-text-primary">
            Métricas de Qualidade RAG
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Avaliação de qualidade das respostas geradas
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <select 
            value={days} 
            onChange={(e) => setDays(Number(e.target.value))}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-primary focus:outline-none"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={30}>Últimos 30 dias</option>
            <option value={90}>Últimos 90 dias</option>
          </select>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as 'day' | 'week')}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-primary focus:outline-none"
          >
            <option value="day">Diário</option>
            <option value="week">Semanal</option>
          </select>
          <button 
            onClick={loadQualityMetrics} 
            className="flex items-center gap-2 px-4 py-2 bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors"
          >
            <RefreshCw size={16} />
            Atualizar
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <Activity size={20} className="text-blue-400" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Total de Avaliações</p>
              <p className="text-2xl font-bold text-text-primary">{stats.total_evaluations}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Target size={20} className="text-green-400" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Score Médio</p>
              <p 
                className="text-2xl font-bold" 
                style={{ color: getScoreColor(stats.avg_score) }}
              >
                {formatScore(stats.avg_score)}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Target size={20} className="text-purple-400" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Fidelidade Média</p>
              <p 
                className="text-2xl font-bold" 
                style={{ color: getScoreColor(stats.avg_faithfulness) }}
              >
                {formatScore(stats.avg_faithfulness)}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg">
              <TrendingUp size={20} className="text-amber-400" />
            </div>
            <div>
              <p className="text-sm text-text-secondary">Relevância Média</p>
              <p 
                className="text-2xl font-bold" 
                style={{ color: getScoreColor(stats.avg_relevancy) }}
              >
                {formatScore(stats.avg_relevancy)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Metrics */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">
          Métricas Detalhadas
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-surface rounded-lg p-4">
            <p className="text-sm text-text-secondary">Score Mínimo</p>
            <p className="text-xl font-semibold text-text-primary mt-1">
              {formatScore(stats.min_score)}
            </p>
          </div>
          <div className="bg-surface rounded-lg p-4">
            <p className="text-sm text-text-secondary">Score Máximo</p>
            <p className="text-xl font-semibold text-text-primary mt-1">
              {formatScore(stats.max_score)}
            </p>
          </div>
          <div className="bg-surface rounded-lg p-4">
            <p className="text-sm text-text-secondary">Mediana</p>
            <p className="text-xl font-semibold text-text-primary mt-1">
              {formatScore(stats.median_score)}
            </p>
          </div>
          <div className="bg-surface rounded-lg p-4">
            <p className="text-sm text-text-secondary">Precisão de Contexto</p>
            <p 
              className="text-xl font-semibold mt-1"
              style={{ color: getScoreColor(stats.avg_precision) }}
            >
              {formatScore(stats.avg_precision)}
            </p>
          </div>
        </div>
      </div>

      {/* Trend Section */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">
          Tendência de Qualidade
        </h3>
        {trends.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 text-text-secondary font-medium">Período</th>
                  <th className="text-left py-3 px-4 text-text-secondary font-medium">Avaliações</th>
                  <th className="text-left py-3 px-4 text-text-secondary font-medium">Score Médio</th>
                  <th className="text-left py-3 px-4 text-text-secondary font-medium">Fidelidade</th>
                  <th className="text-left py-3 px-4 text-text-secondary font-medium">Relevância</th>
                </tr>
              </thead>
              <tbody>
                {trends.map((trend, idx) => (
                  <tr key={idx} className="border-b border-border hover:bg-surface/50">
                    <td className="py-3 px-4 text-text-primary">{trend.period}</td>
                    <td className="py-3 px-4 text-text-primary">{trend.evaluations_count}</td>
                    <td 
                      className="py-3 px-4 font-medium"
                      style={{ color: getScoreColor(trend.avg_score) }}
                    >
                      {formatScore(trend.avg_score)}
                    </td>
                    <td 
                      className="py-3 px-4 font-medium"
                      style={{ color: getScoreColor(trend.avg_faithfulness) }}
                    >
                      {formatScore(trend.avg_faithfulness)}
                    </td>
                    <td 
                      className="py-3 px-4 font-medium"
                      style={{ color: getScoreColor(trend.avg_relevancy) }}
                    >
                      {formatScore(trend.avg_relevancy)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-text-secondary">Sem dados de tendência</div>
        )}
      </div>

      {/* Recent Evaluations */}
      <div className="bg-card border border-border rounded-lg p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">
          Avaliações Recentes
        </h3>
        {recentEvaluations.length > 0 ? (
          <div className="space-y-4">
            {recentEvaluations.map((evaluation) => (
              <div 
                key={evaluation.id} 
                className="bg-surface border border-border rounded-lg overflow-hidden hover:shadow-md transition-shadow"
              >
                <div 
                  className="p-4 cursor-pointer hover:bg-surface/80 transition-colors"
                  onClick={() => setExpandedEval(expandedEval === evaluation.id ? null : evaluation.id)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="flex-1 text-text-primary font-medium">{evaluation.question}</p>
                    <div 
                      className="px-4 py-2 rounded-lg font-bold text-white text-sm whitespace-nowrap"
                      style={{ backgroundColor: getScoreColor(evaluation.overall_score) }}
                    >
                      {formatScore(evaluation.overall_score)}
                    </div>
                  </div>
                </div>
                
                {expandedEval === evaluation.id && (
                  <div className="px-4 pb-4 border-t border-border">
                    <div className="py-3 flex justify-between items-center border-b border-border">
                      <span className="text-text-secondary">Fidelidade</span>
                      <span 
                        className="font-semibold text-text-primary"
                        style={{ color: getScoreColor(evaluation.faithfulness) }}
                      >
                        {formatScore(evaluation.faithfulness)}
                      </span>
                    </div>
                    <div className="py-3 flex justify-between items-center border-b border-border">
                      <span className="text-text-secondary">Relevância</span>
                      <span 
                        className="font-semibold text-text-primary"
                        style={{ color: getScoreColor(evaluation.answer_relevancy) }}
                      >
                        {formatScore(evaluation.answer_relevancy)}
                      </span>
                    </div>
                    <div className="py-3 flex justify-between items-center border-b border-border">
                      <span className="text-text-secondary">Precisão do Contexto</span>
                      <span 
                        className="font-semibold text-text-primary"
                        style={{ color: getScoreColor(evaluation.context_precision) }}
                      >
                        {formatScore(evaluation.context_precision)}
                      </span>
                    </div>
                    {evaluation.evaluation_summary && (
                      <div className="pt-3">
                        <p className="text-text-secondary font-medium mb-2">Resumo da Avaliação</p>
                        <p className="bg-card rounded-lg p-3 text-text-primary text-sm">
                          {evaluation.evaluation_summary}
                        </p>
                      </div>
                    )}
                    <div className="pt-3 text-right text-xs text-text-secondary">
                      Criado em: {new Date(evaluation.created_at).toLocaleString('pt-BR')}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-text-secondary">Nenhuma avaliação recente</div>
        )}
      </div>
    </div>
  );
};

export default QualityMetricsPanel;
