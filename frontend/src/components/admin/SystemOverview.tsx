import { useState, useEffect } from 'react';
import {
    Activity,
    Database,
    Zap,
    Clock,
    RefreshCw,
    HardDrive,
    BarChart3
} from 'lucide-react';
import { API_URL } from '../../api';
import { createLogger } from '../../logger';

const logger = createLogger('SystemOverview');

interface HealthData {
    status: string;
    database: string;
}

interface StatsData {
    documents_count: number;
}

interface CacheStats {
    size: number;
    max_size: number;
    hits: number;
    misses: number;
    hit_rate_percent: number;
    uptime_seconds: number;
}

interface DocumentStats {
    total_files: number;
    files_by_type: Record<string, number>;
    indexed_chunks: number;
    total_size_mb?: number;
}

interface MetricsStatus {
    prometheus_available: boolean;
    metrics_enabled: boolean;
}

interface IngestionStatus {
    running: boolean;
    progress: number;
    total: number;
    current_file: string | null;
    message: string;
}


export function SystemOverview() {
    const [health, setHealth] = useState<HealthData | null>(null);
    const [stats, setStats] = useState<StatsData | null>(null);
    const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
    const [docStats, setDocStats] = useState<DocumentStats | null>(null);
    const [metricsStatus, setMetricsStatus] = useState<MetricsStatus | null>(null);
    const [ingestionStatus, setIngestionStatus] = useState<IngestionStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

    const fetchData = async () => {
        setLoading(true);
        try {
            const [healthRes, statsRes, cacheRes, docsRes, metricsRes, ingestRes] = await Promise.all([
                fetch(`${API_URL}/health`).then(r => r.json()),
                fetch(`${API_URL}/stats`).then(r => r.json()),
                fetch(`${API_URL}/cache/stats`).then(r => r.json()),
                fetch(`${API_URL}/documents/stats`).then(r => r.json()),
                fetch(`${API_URL}/metrics/status`).then(r => r.json()).catch(() => ({ prometheus_available: false, metrics_enabled: false })),
                fetch(`${API_URL}/documents/ingest-status`).then(r => r.json())
            ]);

            setHealth(healthRes);
            setStats(statsRes);
            setCacheStats(cacheRes);
            setDocStats(docsRes);
            setMetricsStatus(metricsRes);
            setIngestionStatus(ingestRes);
            setLastRefresh(new Date());
        } catch (error) {
            logger.error('Failed to fetch system data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    const formatUptime = (seconds: number) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-text-primary flex items-center gap-2">
                    <Activity size={24} className="text-accent-primary" />
                    Visão Geral do Sistema
                </h2>
                <button
                    onClick={fetchData}
                    disabled={loading}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface hover:bg-surface/80 text-text-primary rounded-lg transition-colors disabled:opacity-50 border border-border"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    Atualizar
                </button>
            </div>

            {/* Status Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

                {/* Health Status */}
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-text-secondary text-sm">Status</span>
                        <div className={`w-2.5 h-2.5 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                    </div>
                    <p className="text-2xl font-bold text-text-primary capitalize">
                        {health?.status || 'Carregando...'}
                    </p>
                    <p className="text-xs text-text-secondary mt-1">
                        Database: {health?.database || '...'}
                    </p>
                </div>

                {/* Documents Count */}
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-text-secondary text-sm">Chunks Indexados</span>
                        <Database size={16} className="text-accent-primary" />
                    </div>
                    <p className="text-2xl font-bold text-text-primary">
                        {stats?.documents_count?.toLocaleString() || '0'}
                    </p>
                    <p className="text-xs text-text-secondary mt-1">
                        {docStats?.total_files || 0} arquivos processados
                    </p>
                </div>

                {/* Cache Hit Rate */}
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-text-secondary text-sm">Cache Hit Rate</span>
                        <Zap size={16} className="text-yellow-400" />
                    </div>
                    <p className="text-2xl font-bold text-text-primary">
                        {cacheStats?.hit_rate_percent?.toFixed(1) || '0'}%
                    </p>
                    <p className="text-xs text-text-secondary mt-1">
                        {cacheStats?.hits || 0} hits / {cacheStats?.misses || 0} misses
                    </p>
                </div>

                {/* Uptime */}
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-text-secondary text-sm">Cache Uptime</span>
                        <Clock size={16} className="text-emerald-400" />
                    </div>
                    <p className="text-2xl font-bold text-text-primary">
                        {cacheStats ? formatUptime(cacheStats.uptime_seconds) : '...'}
                    </p>
                    <p className="text-xs text-text-secondary mt-1">
                        {cacheStats?.size || 0} / {cacheStats?.max_size || 1000} entries
                    </p>
                </div>

                {/* Ingestion Status Card */}
                <div className={`glass rounded-xl p-4 transition-colors ${ingestionStatus?.running ? 'border-accent-primary/50 bg-accent-primary/5' : ''}`}>
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-text-secondary text-sm">Ingestão</span>
                        {ingestionStatus?.running ? (
                            <RefreshCw size={16} className="text-accent-primary animate-spin" />
                        ) : (
                            <HardDrive size={16} className="text-text-secondary" />
                        )}
                    </div>
                    {ingestionStatus?.running ? (
                        <>
                            <p className="text-2xl font-bold text-text-primary">
                                {Math.round((ingestionStatus.progress / ingestionStatus.total) * 100)}%
                            </p>
                            <div className="w-full bg-surface rounded-full h-1.5 mt-2">
                                <div
                                    className="bg-accent-primary h-1.5 rounded-full transition-all duration-500"
                                    style={{ width: `${(ingestionStatus.progress / ingestionStatus.total) * 100}%` }}
                                />
                            </div>
                            <p className="text-[10px] text-text-secondary mt-1 truncate">
                                {ingestionStatus.current_file || 'Processando...'}
                            </p>
                        </>
                    ) : (
                        <>
                            <p className="text-2xl font-bold text-text-secondary">
                                Inativa
                            </p>
                            <p className="text-xs text-text-secondary/60 mt-1">
                                Sistema pronto
                            </p>
                        </>
                    )}
                </div>
            </div>

            {/* Additional Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                {/* Documents by Type */}
                <div className="glass rounded-xl p-4">
                    <h3 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
                        <HardDrive size={14} />
                        Documentos por Tipo
                    </h3>
                    {docStats?.files_by_type && Object.keys(docStats.files_by_type).length > 0 ? (
                        <div className="space-y-2">
                            {Object.entries(docStats.files_by_type).map(([ext, count]) => (
                                <div key={ext} className="flex items-center justify-between">
                                    <span className="text-text-secondary text-sm">{ext.toUpperCase()}</span>
                                    <span className="text-text-primary font-medium">{count}</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-text-secondary text-sm">Nenhum documento indexado</p>
                    )}
                </div>

                {/* Prometheus Status */}
                <div className="glass rounded-xl p-4">
                    <h3 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
                        <BarChart3 size={14} />
                        Métricas Prometheus
                    </h3>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-text-secondary text-sm">Prometheus Disponível</span>
                            <span className={`text-sm font-medium ${metricsStatus?.prometheus_available ? 'text-emerald-400' : 'text-red-400'}`}>
                                {metricsStatus?.prometheus_available ? 'Sim' : 'Não'}
                            </span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-text-secondary text-sm">Métricas Habilitadas</span>
                            <span className={`text-sm font-medium ${metricsStatus?.metrics_enabled ? 'text-emerald-400' : 'text-text-secondary'}`}>
                                {metricsStatus?.metrics_enabled ? 'Sim' : 'Não'}
                            </span>
                        </div>
                        {metricsStatus?.prometheus_available && (
                            <a
                                href={`${API_URL}/metrics`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-block mt-2 text-xs text-accent-primary hover:text-accent-hover underline"
                            >
                                Ver métricas raw →
                            </a>
                        )}
                    </div>
                </div>
            </div>

            {/* Last Update */}
            <p className="text-xs text-text-secondary/60 text-center">
                Última atualização: {lastRefresh.toLocaleTimeString()}
            </p>
        </div>
    );
}
