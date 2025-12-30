import { useState, useEffect } from 'react';
import { Target, Clock, TrendingUp, Activity } from 'lucide-react';

interface AdaptiveStats {
    total_queries: number;
    adaptive_applied_pct: number;
    avg_complexity: number;
    avg_top_k: number;
    avg_min_similarity: number;
    complexity_distribution: {
        simple: number;
        medium: number;
        complex: number;
    };
    complexity_by_score: Record<number, number>;
    days: number;
}

interface AdaptiveMetric {
    id: number;
    question: string;
    complexity_score: number;
    word_count: number;
    top_k_original: number;
    top_k_adjusted: number;
    min_similarity_original: number;
    min_similarity_adjusted: number;
    adjustment_reason: string;
    characteristics: Record<string, boolean>;
    duration_ms: number | null;
    created_at: string;
}

interface RecentMetricsResponse {
    metrics: AdaptiveMetric[];
    count: number;
}

export function AdaptiveRetrievalMetrics() {
    const [stats, setStats] = useState<AdaptiveStats | null>(null);
    const [recentMetrics, setRecentMetrics] = useState<AdaptiveMetric[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [days, setDays] = useState(7);

    useEffect(() => {
        loadMetrics();
    }, [days]);

    async function loadMetrics() {
        setLoading(true);
        setError(null);
        try {
            // Carregar estatísticas
            const statsRes = await fetch(`http://localhost:5000/api/metrics/adaptive-retrieval/stats?days=${days}`);
            if (!statsRes.ok) throw new Error('Failed to load stats');
            const statsData = await statsRes.json();
            setStats(statsData);

            // Carregar métricas recentes
            const recentRes = await fetch('http://localhost:5000/api/metrics/adaptive-retrieval/recent?limit=50');
            if (!recentRes.ok) throw new Error('Failed to load recent metrics');
            const recentData: RecentMetricsResponse = await recentRes.json();
            setRecentMetrics(recentData.metrics);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-primary"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-red-400">
                    <p className="font-medium">Erro ao carregar métricas</p>
                    <p className="text-sm mt-2">{error}</p>
                </div>
            </div>
        );
    }

    if (!stats) {
        return (
            <div className="flex items-center justify-center h-96">
                <p className="text-text-secondary">Nenhuma métrica disponível</p>
            </div>
        );
    }

    const total = stats.complexity_distribution.simple + 
                 stats.complexity_distribution.medium + 
                 stats.complexity_distribution.complex;

    const simplePct = total > 0 ? (stats.complexity_distribution.simple / total) * 100 : 0;
    const mediumPct = total > 0 ? (stats.complexity_distribution.medium / total) * 100 : 0;
    const complexPct = total > 0 ? (stats.complexity_distribution.complex / total) * 100 : 0;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-semibold text-text-primary">
                        Adaptive Retrieval Metrics
                    </h2>
                    <p className="text-sm text-text-secondary mt-1">
                        Análise de complexidade de queries e ajustes dinâmicos
                    </p>
                </div>
                <select
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                    className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:border-accent-primary focus:outline-none"
                >
                    <option value={1}>Últimas 24h</option>
                    <option value={7}>Últimos 7 dias</option>
                    <option value={30}>Últimos 30 dias</option>
                </select>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/20 rounded-lg">
                            <Target size={20} className="text-blue-400" />
                        </div>
                        <div>
                            <p className="text-sm text-text-secondary">Total de Queries</p>
                            <p className="text-2xl font-bold text-text-primary">{stats.total_queries}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-500/20 rounded-lg">
                            <Activity size={20} className="text-green-400" />
                        </div>
                        <div>
                            <p className="text-sm text-text-secondary">Complexidade Média</p>
                            <p className="text-2xl font-bold text-text-primary">{stats.avg_complexity.toFixed(1)}/10</p>
                        </div>
                    </div>
                </div>

                <div className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-500/20 rounded-lg">
                            <TrendingUp size={20} className="text-amber-400" />
                        </div>
                        <div>
                            <p className="text-sm text-text-secondary">Top K Médio</p>
                            <p className="text-2xl font-bold text-text-primary">{stats.avg_top_k.toFixed(1)}</p>
                        </div>
                    </div>
                </div>

                <div className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-500/20 rounded-lg">
                            <Clock size={20} className="text-purple-400" />
                        </div>
                        <div>
                            <p className="text-sm text-text-secondary">Min Similaridade</p>
                            <p className="text-2xl font-bold text-text-primary">{(stats.avg_min_similarity * 100).toFixed(0)}%</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Complexity Distribution Chart */}
            <div className="bg-card border border-border rounded-lg p-6">
                <h3 className="text-lg font-semibold text-text-primary mb-4">
                    Distribuição de Complexidade
                </h3>
                
                {total === 0 ? (
                    <p className="text-text-secondary text-center py-8">Sem dados para exibir</p>
                ) : (
                    <div className="space-y-4">
                        {/* Simple */}
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-text-primary">Simple (0-3)</span>
                                <span className="text-text-secondary">
                                    {stats.complexity_distribution.simple} queries ({simplePct.toFixed(1)}%)
                                </span>
                            </div>
                            <div className="h-3 bg-surface rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-green-500 transition-all duration-500"
                                    style={{ width: `${simplePct}%` }}
                                />
                            </div>
                        </div>

                        {/* Medium */}
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-text-primary">Medium (4-6)</span>
                                <span className="text-text-secondary">
                                    {stats.complexity_distribution.medium} queries ({mediumPct.toFixed(1)}%)
                                </span>
                            </div>
                            <div className="h-3 bg-surface rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-amber-500 transition-all duration-500"
                                    style={{ width: `${mediumPct}%` }}
                                />
                            </div>
                        </div>

                        {/* Complex */}
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-text-primary">Complex (7-10)</span>
                                <span className="text-text-secondary">
                                    {stats.complexity_distribution.complex} queries ({complexPct.toFixed(1)}%)
                                </span>
                            </div>
                            <div className="h-3 bg-surface rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-red-500 transition-all duration-500"
                                    style={{ width: `${complexPct}%` }}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Legend */}
                <div className="flex gap-6 mt-6 text-sm">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                        <span className="text-text-secondary">Simple</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
                        <span className="text-text-secondary">Medium</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                        <span className="text-text-secondary">Complex</span>
                    </div>
                </div>
            </div>

            {/* Recent Queries Table */}
            <div className="bg-card border border-border rounded-lg p-6">
                <h3 className="text-lg font-semibold text-text-primary mb-4">
                    Queries Recentes (últimas 50)
                </h3>
                
                {recentMetrics.length === 0 ? (
                    <p className="text-text-secondary text-center py-8">Nenhuma query registrada</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border">
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Pergunta</th>
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Complexidade</th>
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Palavras</th>
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Top K</th>
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Min Sim</th>
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Motivo</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentMetrics.slice(0, 20).map((metric) => (
                                    <tr key={metric.id} className="border-b border-border hover:bg-surface/50">
                                        <td className="py-3 px-4 text-text-primary max-w-md truncate">
                                            {metric.question}
                                        </td>
                                        <td className="py-3 px-4">
                                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                metric.complexity_score <= 3 
                                                    ? 'bg-green-500/20 text-green-400'
                                                    : metric.complexity_score <= 6
                                                    ? 'bg-amber-500/20 text-amber-400'
                                                    : 'bg-red-500/20 text-red-400'
                                            }`}>
                                                {metric.complexity_score}/10
                                            </span>
                                        </td>
                                        <td className="py-3 px-4 text-text-secondary">
                                            {metric.word_count}
                                        </td>
                                        <td className="py-3 px-4 text-text-primary">
                                            {metric.top_k_original} → {metric.top_k_adjusted}
                                        </td>
                                        <td className="py-3 px-4 text-text-primary">
                                            {(metric.min_similarity_original * 100).toFixed(0)}% → {(metric.min_similarity_adjusted * 100).toFixed(0)}%
                                        </td>
                                        <td className="py-3 px-4 text-text-secondary text-xs max-w-xs truncate">
                                            {metric.adjustment_reason}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Refresh Button */}
            <div className="flex justify-end">
                <button
                    onClick={loadMetrics}
                    className="flex items-center gap-2 px-4 py-2 bg-accent-primary hover:bg-accent-primary/80 text-white rounded-lg transition-colors"
                >
                    <Activity size={16} />
                    Atualizar Métricas
                </button>
            </div>
        </div>
    );
}
