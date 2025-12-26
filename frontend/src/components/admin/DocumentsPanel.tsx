import { useState, useEffect } from 'react';
import {
    HardDrive,
    FolderOpen,
    FileText,
    RefreshCw,
    Database
} from 'lucide-react';

interface DocumentStats {
    total_files: number;
    files_by_type: Record<string, number>;
    indexed_chunks: number;
    total_size_mb?: number;
    documents_dir?: string;
}

interface Collection {
    name: string;
}

const API_URL = "http://localhost:5000/api";

export function DocumentsPanel() {
    const [docStats, setDocStats] = useState<DocumentStats | null>(null);
    const [collections, setCollections] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [docsRes, collectionsRes] = await Promise.all([
                fetch(`${API_URL}/documents/stats`).then(r => r.json()),
                fetch(`${API_URL}/collections`).then(r => r.json())
            ]);

            setDocStats(docsRes);
            setCollections(collectionsRes.collections || []);
        } catch (error) {
            console.error('Failed to fetch documents data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const getFileIcon = (ext: string) => {
        switch (ext.toLowerCase()) {
            case '.pdf': return '📄';
            case '.docx': return '📝';
            case '.txt': return '📃';
            case '.md': return '📋';
            case '.html':
            case '.htm': return '🌐';
            default: return '📁';
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <HardDrive size={24} className="text-indigo-400" />
                    Documentos
                </h2>
                <button
                    onClick={fetchData}
                    disabled={loading}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors disabled:opacity-50"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    Atualizar
                </button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw size={24} className="animate-spin text-zinc-500" />
                </div>
            ) : (
                <>
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-zinc-400 text-sm">Total Arquivos</span>
                                <FileText size={16} className="text-blue-400" />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {docStats?.total_files || 0}
                            </p>
                        </div>

                        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-zinc-400 text-sm">Chunks Indexados</span>
                                <Database size={16} className="text-emerald-400" />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {docStats?.indexed_chunks?.toLocaleString() || 0}
                            </p>
                        </div>

                        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-zinc-400 text-sm">Collections</span>
                                <FolderOpen size={16} className="text-yellow-400" />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {collections.length}
                            </p>
                        </div>
                    </div>

                    {/* Files by Type */}
                    <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                        <h3 className="text-sm font-medium text-zinc-300 mb-4">Arquivos por Tipo</h3>
                        {docStats?.files_by_type && Object.keys(docStats.files_by_type).length > 0 ? (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {Object.entries(docStats.files_by_type).map(([ext, count]) => (
                                    <div
                                        key={ext}
                                        className="flex items-center gap-2 bg-zinc-800/50 rounded-lg p-3"
                                    >
                                        <span className="text-xl">{getFileIcon(ext)}</span>
                                        <div>
                                            <p className="text-white font-medium">{count}</p>
                                            <p className="text-xs text-zinc-500 uppercase">{ext}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-zinc-500 text-sm">Nenhum documento encontrado</p>
                        )}
                    </div>

                    {/* Collections List */}
                    <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                        <h3 className="text-sm font-medium text-zinc-300 mb-4">Collections Disponíveis</h3>
                        {collections.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {collections.map((collection) => (
                                    <span
                                        key={collection}
                                        className="px-3 py-1.5 bg-indigo-500/10 text-indigo-400 rounded-lg text-sm border border-indigo-500/20"
                                    >
                                        {collection}
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <p className="text-zinc-500 text-sm">Usando collection padrão</p>
                        )}
                    </div>

                    {/* Documents Path */}
                    {docStats?.documents_dir && (
                        <div className="text-xs text-zinc-600 flex items-center gap-2">
                            <FolderOpen size={12} />
                            <span className="font-mono">{docStats.documents_dir}</span>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
