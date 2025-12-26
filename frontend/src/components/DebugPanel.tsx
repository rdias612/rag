import { ChevronDown, ChevronUp, Clock, Cpu, Search, Zap, Brain, Settings2 } from 'lucide-react';
import { useState } from 'react';
import type { DebugInfo } from '../types';

interface DebugPanelProps {
    debugInfo: DebugInfo;
}

export function DebugPanel({ debugInfo }: DebugPanelProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    const formatMs = (ms?: number) => {
        if (ms === undefined) return '-';
        if (ms < 1000) return `${ms.toFixed(0)}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    // Calculate timing breakdown
    const timings = [
        { label: 'Embedding', value: debugInfo.embedding_time_ms, icon: Cpu, color: 'text-blue-400' },
        { label: 'Search', value: debugInfo.search_time_ms, icon: Search, color: 'text-emerald-400' },
        { label: 'Rerank', value: debugInfo.rerank_time_ms, icon: Zap, color: 'text-yellow-400' },
        { label: 'Compress', value: debugInfo.compression_time_ms, icon: Settings2, color: 'text-purple-400' },
        { label: 'LLM', value: debugInfo.llm_time_ms, icon: Brain, color: 'text-pink-400' },
    ].filter(t => t.value !== undefined);

    const totalTime = debugInfo.total_time_ms || 0;

    return (
        <div className="mt-3 bg-zinc-900/80 border border-white/10 rounded-lg overflow-hidden text-xs">
            {/* Header - Always visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Clock size={12} className="text-indigo-400" />
                    <span className="text-zinc-400">Debug</span>
                    <span className="text-white font-medium">{formatMs(totalTime)}</span>
                </div>
                <div className="flex items-center gap-3">
                    {/* Quick stats */}
                    <div className="hidden sm:flex items-center gap-2 text-zinc-500">
                        {debugInfo.hyde_applied && (
                            <span className="bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded text-[10px]">HyDE</span>
                        )}
                        {debugInfo.config?.enable_reranking && (
                            <span className="bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded text-[10px]">Rerank</span>
                        )}
                        <span className="text-zinc-600">|</span>
                        <span>{debugInfo.initial_chunks_found || 0} chunks</span>
                    </div>
                    {isExpanded ? <ChevronUp size={14} className="text-zinc-500" /> : <ChevronDown size={14} className="text-zinc-500" />}
                </div>
            </button>

            {/* Expanded content */}
            {isExpanded && (
                <div className="border-t border-white/5 px-3 py-3 space-y-3">
                    {/* Timing breakdown */}
                    <div>
                        <h4 className="text-zinc-500 mb-2 uppercase tracking-wide text-[10px]">Timing Breakdown</h4>
                        <div className="flex flex-wrap gap-2">
                            {timings.map(({ label, value, icon: Icon, color }) => (
                                <div key={label} className="flex items-center gap-1.5 bg-zinc-800/50 px-2 py-1 rounded">
                                    <Icon size={10} className={color} />
                                    <span className="text-zinc-400">{label}:</span>
                                    <span className="text-white font-medium">{formatMs(value)}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Chunks info */}
                    <div className="flex gap-4">
                        <div>
                            <span className="text-zinc-500">Chunks encontrados:</span>
                            <span className="text-white ml-1">{debugInfo.initial_chunks_found || 0}</span>
                        </div>
                        {debugInfo.chunks_after_rerank !== undefined && (
                            <div>
                                <span className="text-zinc-500">Após rerank:</span>
                                <span className="text-white ml-1">{debugInfo.chunks_after_rerank}</span>
                            </div>
                        )}
                        {debugInfo.chunks_rejected !== undefined && debugInfo.chunks_rejected > 0 && (
                            <div>
                                <span className="text-zinc-500">Rejeitados:</span>
                                <span className="text-red-400 ml-1">{debugInfo.chunks_rejected}</span>
                            </div>
                        )}
                    </div>

                    {/* Question type */}
                    {debugInfo.question_type && (
                        <div>
                            <span className="text-zinc-500">Tipo de pergunta:</span>
                            <span className="text-indigo-400 ml-1 capitalize">{debugInfo.question_type}</span>
                        </div>
                    )}

                    {/* HyDE document preview */}
                    {debugInfo.hyde_document && (
                        <div>
                            <h4 className="text-zinc-500 mb-1 uppercase tracking-wide text-[10px]">HyDE Document</h4>
                            <p className="text-zinc-400 bg-zinc-800/50 p-2 rounded text-[11px] leading-relaxed max-h-20 overflow-y-auto">
                                {debugInfo.hyde_document}
                            </p>
                        </div>
                    )}

                    {/* Active features */}
                    {debugInfo.config && (
                        <div>
                            <h4 className="text-zinc-500 mb-1 uppercase tracking-wide text-[10px]">Features Ativas</h4>
                            <div className="flex flex-wrap gap-1">
                                {Object.entries(debugInfo.config).map(([key, value]) => (
                                    <span
                                        key={key}
                                        className={`px-1.5 py-0.5 rounded text-[10px] ${value
                                                ? 'bg-emerald-500/20 text-emerald-400'
                                                : 'bg-zinc-700/50 text-zinc-500'
                                            }`}
                                    >
                                        {key.replace('enable_', '').replace('use_', '')}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
