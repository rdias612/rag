import { useState, useEffect } from 'react';
import {
    HardDrive,
    FolderOpen,
    FileText,
    RefreshCw,
    Database,
    Trash2,
    Play,
    AlertCircle,
    CheckCircle,
    Clock,
    Loader2,
    RotateCcw
} from 'lucide-react';
import { ConfirmModal } from '../ConfirmModal';
import { API_URL } from '../../api';

interface DocumentStats {
    total_files: number;
    files_by_type: Record<string, number>;
    indexed_chunks: number;
    total_size_mb?: number;
    documents_dir?: string;
}

interface IngestedDocument {
    id: number;
    file_path: string;
    file_name: string;
    file_hash: string;
    file_size: number;
    collection_id: string;
    chunks_count: number;
    status: string;
    ingested_at: string;
}
interface IngestionStatus {
    running: boolean;
    progress: number;
    total: number;
    current_file: string | null;
    message: string;
    results: Array<{
        file: string;
        status: string;
        message?: string;
        chunks?: number;
        total_chunks?: number;
    }>;
}



export function DocumentsPanel() {
    const [docStats, setDocStats] = useState<DocumentStats | null>(null);
    const [collections, setCollections] = useState<string[]>([]);
    const [ingestedDocs, setIngestedDocs] = useState<IngestedDocument[]>([]);
    const [ingestionStatus, setIngestionStatus] = useState<IngestionStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
    const [deleting, setDeleting] = useState<string | null>(null);

    // Modal states
    const [showReprocessModal, setShowReprocessModal] = useState(false);
    const [showScanModal, setShowScanModal] = useState(false);
    const [showNoFilesModal, setShowNoFilesModal] = useState(false);
    const [pendingFiles, setPendingFiles] = useState<any[]>([]);
    const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
    const [scanning, setScanning] = useState(false);

    const fetchWithTimeout = async (url: string, options: RequestInit = {}, timeout = 10000) => {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(id);
            return response;
        } catch (error) {
            clearTimeout(id);
            throw error;
        }
    };

    const fetchData = async () => {
        setLoading(true);
        try {
            const results = await Promise.allSettled([
                fetchWithTimeout(`${API_URL}/documents/stats`).then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                }),
                fetchWithTimeout(`${API_URL}/collections`).then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                }),
                fetchWithTimeout(`${API_URL}/documents/ingested`).then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                }),
                fetchWithTimeout(`${API_URL}/documents/ingest-status`).then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                })
            ]);

            // Extract data from settled promises
            const [docsResult, collectionsResult, ingestedResult, statusResult] = results;

            if (docsResult.status === 'fulfilled') {
                setDocStats(docsResult.value);
            } else {
                console.error('[DocumentsPanel] documents/stats failed:', docsResult.reason);
            }

            if (collectionsResult.status === 'fulfilled') {
                setCollections(collectionsResult.value.collections || []);
            } else {
                console.error('[DocumentsPanel] collections failed:', collectionsResult.reason);
                setCollections([]); // fallback
            }

            if (ingestedResult.status === 'fulfilled') {
                setIngestedDocs(ingestedResult.value.documents || []);
            } else {
                console.error('[DocumentsPanel] documents/ingested failed:', ingestedResult.reason);
                setIngestedDocs([]); // fallback
            }

            if (statusResult.status === 'fulfilled') {
                setIngestionStatus(statusResult.value);
            } else {
                console.error('[DocumentsPanel] documents/ingest-status failed:', statusResult.reason);
            }
        } catch (error) {
            console.error('[DocumentsPanel] Failed to fetch documents data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    // Polling condicional: apenas quando há uma ingestão rodando
    useEffect(() => {
        let interval: any;

        if (ingestionStatus?.running) {
            interval = setInterval(() => {
                fetchData();
            }, 3000); // 3 segundos é um bom equilíbrio
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [ingestionStatus?.running]);

    const startIngestion = async (force: boolean = false, files_to_ingest: string[] | null = null) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/documents/ingest-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    force,
                    files: files_to_ingest
                })
            });

            if (res.ok) {
                const data = await res.json();
                setIngestionStatus({
                    running: true,
                    progress: 0,
                    total: data.total_files || 0,
                    current_file: null,
                    message: files_to_ingest ? "Reprocessando selecionados..." : "Iniciando ingestão...",
                    results: []
                });
                if (files_to_ingest) {
                    setSelectedDocs([]);
                }
                // Iniciar polling
                fetchData();
            }
        } catch (error) {
            console.error("Error starting ingestion:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleScanClick = async () => {
        setScanning(true);
        try {
            const res = await fetch(`${API_URL}/documents/scan`);
            if (!res.ok) throw new Error("Failed to scan documents");
            const data = await res.json();

            if (data.pending && data.pending.length > 0) {
                setPendingFiles(data.pending);
                setShowScanModal(true);
            } else {
                setShowNoFilesModal(true);
            }
        } catch (error) {
            console.error("Error scanning:", error);
        } finally {
            setScanning(false);
        }
    };

    const reprocessKnowledgeBase = async () => {
        try {
            const res = await fetch(`${API_URL}/documents/reprocess`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (res.ok) {
                const data = await res.json();
                setIngestionStatus({
                    running: true,
                    progress: 0,
                    total: data.total_files,
                    current_file: null,
                    message: 'Base limpa. Reprocessando...',
                    results: []
                });
                // Atualizar lista de documentos ingeridos (agora vazia)
                setIngestedDocs([]);
            }
        } catch (error) {
            console.error('Failed to reprocess:', error);
        } finally {
            setShowReprocessModal(false);
        }
    };

    const deleteDocument = async (filePath: string) => {
        setDeleting(filePath);
        try {
            const res = await fetch(`${API_URL}/documents/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: filePath })
            });

            if (res.ok) {
                // Remover da lista local
                setIngestedDocs(prev => prev.filter(d => d.file_path !== filePath));
                setDeleteConfirm(null);
                // Atualizar estatísticas
                fetchData();
            }
        } catch (error) {
            console.error('Failed to delete document:', error);
        } finally {
            setDeleting(null);
        }
    };

    const formatBytes = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const formatDate = (dateStr: string) => {
        try {
            return new Date(dateStr).toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateStr;
        }
    };

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

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'success':
                return <CheckCircle size={14} className="text-emerald-400" />;
            case 'error':
                return <AlertCircle size={14} className="text-red-400" />;
            case 'skipped':
                return <Clock size={14} className="text-yellow-400" />;
            default:
                return <FileText size={14} className="text-zinc-400" />;
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
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleScanClick}
                        disabled={loading || scanning || ingestionStatus?.running}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {scanning ? (
                            <Loader2 size={14} className="animate-spin" />
                        ) : ingestionStatus?.running ? (
                            <Loader2 size={14} className="animate-spin" />
                        ) : (
                            <Play size={14} />
                        )}
                        {scanning ? 'Escaneando...' : ingestionStatus?.running ? 'Processando...' : 'Atualizar Base de Conhecimento'}
                    </button>
                    <button
                        onClick={() => setShowReprocessModal(true)}
                        disabled={loading || ingestionStatus?.running}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Limpa todos os dados e reprocessa do zero"
                    >
                        <RotateCcw size={14} />
                        Reprocessar Base
                    </button>
                    <button
                        onClick={fetchData}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors disabled:opacity-50"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        Atualizar
                    </button>
                </div>
            </div>

            {/* Ingestion Progress */}
            {ingestionStatus?.running && (
                <div className="bg-indigo-900/30 border border-indigo-500/30 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-indigo-300">
                            Ingestão em Andamento
                        </span>
                        <span className="text-sm text-indigo-400">
                            {ingestionStatus.progress} / {ingestionStatus.total}
                        </span>
                    </div>
                    <div className="w-full bg-indigo-900/50 rounded-full h-2 mb-2">
                        <div
                            className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${ingestionStatus.total > 0 ? (ingestionStatus.progress / ingestionStatus.total) * 100 : 0}%` }}
                        />
                    </div>
                    <p className="text-xs text-indigo-400 truncate">
                        {ingestionStatus.message}
                    </p>
                </div>
            )}

            {/* Ingestion Results */}
            {!ingestionStatus?.running && ingestionStatus?.results && ingestionStatus.results.length > 0 && (
                <div className="bg-zinc-900/60 border border-white/5 rounded-xl p-4">
                    <h3 className="text-sm font-medium text-zinc-300 mb-3">Última Ingestão</h3>
                    <p className="text-xs text-zinc-400 mb-3">{ingestionStatus.message}</p>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                        {ingestionStatus.results.map((result, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-xs">
                                {getStatusIcon(result.status)}
                                <span className="text-zinc-300 truncate flex-1">{result.file}</span>
                                {result.chunks !== undefined && (
                                    <span className="text-zinc-500">
                                        {result.chunks}
                                        {result.total_chunks && result.total_chunks !== result.chunks ? `/${result.total_chunks}` : ''} chunks
                                    </span>
                                )}
                                {result.message && result.status !== 'success' && (
                                    <span className="text-zinc-500">{result.message}</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw size={24} className="animate-spin text-zinc-500" />
                </div>
            ) : (
                <>
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-zinc-400 text-sm">Arquivos no Dir</span>
                                <FileText size={16} className="text-blue-400" />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {docStats?.total_files || 0}
                            </p>
                        </div>

                        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-zinc-400 text-sm">Docs Ingeridos</span>
                                <CheckCircle size={16} className="text-emerald-400" />
                            </div>
                            <p className="text-2xl font-bold text-white">
                                {ingestedDocs.length}
                            </p>
                        </div>

                        <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-zinc-400 text-sm">Chunks Indexados</span>
                                <Database size={16} className="text-purple-400" />
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

                    {/* Ingested Documents Table */}
                    <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl overflow-hidden">
                        <div className="p-4 border-b border-white/5 flex items-center justify-between">
                            <h3 className="text-sm font-medium text-zinc-300">Documentos Ingeridos</h3>
                            {selectedDocs.length > 0 && (
                                <button
                                    onClick={() => startIngestion(true, selectedDocs)}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/10"
                                >
                                    <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                                    Reprocessar {selectedDocs.length} Selecionado(s)
                                </button>
                            )}
                        </div>

                        {ingestedDocs.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="text-left text-xs text-zinc-500 border-b border-white/5">
                                            <th className="px-4 py-3 w-10">
                                                <input
                                                    type="checkbox"
                                                    className="rounded border-white/10 bg-white/5 text-indigo-500 focus:ring-indigo-500/50"
                                                    checked={selectedDocs.length === ingestedDocs.length && ingestedDocs.length > 0}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedDocs(ingestedDocs.map(d => d.file_path));
                                                        } else {
                                                            setSelectedDocs([]);
                                                        }
                                                    }}
                                                />
                                            </th>
                                            <th className="px-4 py-3 font-medium">Arquivo</th>
                                            <th className="px-4 py-3 font-medium">Coleção</th>
                                            <th className="px-4 py-3 font-medium">Chunks</th>
                                            <th className="px-4 py-3 font-medium">Tamanho</th>
                                            <th className="px-4 py-3 font-medium">Data</th>
                                            <th className="px-4 py-3 font-medium">Status</th>
                                            <th className="px-4 py-3 font-medium w-20">Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ingestedDocs.map((doc) => (
                                            <tr
                                                key={doc.id}
                                                className={`border-b border-white/5 hover:bg-white/5 transition-colors ${selectedDocs.includes(doc.file_path) ? 'bg-indigo-500/5' : ''
                                                    }`}
                                            >
                                                <td className="px-4 py-3">
                                                    <input
                                                        type="checkbox"
                                                        className="rounded border-white/10 bg-white/5 text-indigo-500 focus:ring-indigo-500/50"
                                                        checked={selectedDocs.includes(doc.file_path)}
                                                        onChange={(e) => {
                                                            if (e.target.checked) {
                                                                setSelectedDocs(prev => [...prev, doc.file_path]);
                                                            } else {
                                                                setSelectedDocs(prev => prev.filter(path => path !== doc.file_path));
                                                            }
                                                        }}
                                                    />
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-2">
                                                        <span>{getFileIcon(doc.file_name.substring(doc.file_name.lastIndexOf('.')))}</span>
                                                        <span className="text-sm text-white truncate max-w-[200px]" title={doc.file_name}>
                                                            {doc.file_name}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="text-xs px-2 py-1 bg-indigo-500/10 text-indigo-400 rounded">
                                                        {doc.collection_id}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-zinc-300">
                                                    {doc.chunks_count}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-zinc-400">
                                                    {formatBytes(doc.file_size)}
                                                </td>
                                                <td className="px-4 py-3 text-xs text-zinc-500">
                                                    {formatDate(doc.ingested_at)}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {getStatusIcon(doc.status)}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {deleteConfirm === doc.file_path ? (
                                                        <div className="flex items-center gap-1">
                                                            <button
                                                                onClick={() => deleteDocument(doc.file_path)}
                                                                disabled={deleting === doc.file_path}
                                                                className="text-xs px-2 py-1 bg-red-600 hover:bg-red-500 text-white rounded transition-colors disabled:opacity-50"
                                                            >
                                                                {deleting === doc.file_path ? '...' : 'Sim'}
                                                            </button>
                                                            <button
                                                                onClick={() => setDeleteConfirm(null)}
                                                                className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded transition-colors"
                                                            >
                                                                Não
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button
                                                            onClick={() => setDeleteConfirm(doc.file_path)}
                                                            className="p-1.5 hover:bg-red-500/10 text-zinc-500 hover:text-red-400 rounded transition-colors"
                                                            title="Deletar documento"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-8 text-center text-zinc-500">
                                <Database size={32} className="mx-auto mb-2 opacity-50" />
                                <p className="text-sm">Nenhum documento ingerido ainda</p>
                                <p className="text-xs mt-1">Clique em "Iniciar Ingestão" para processar documentos</p>
                            </div>
                        )}
                    </div>

                    {/* Files by Type */}
                    <div className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4">
                        <h3 className="text-sm font-medium text-zinc-300 mb-4">Arquivos por Tipo (no diretório)</h3>
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

                    {/* Documents Path */}
                    {docStats?.documents_dir && (
                        <div className="text-xs text-zinc-600 flex items-center gap-2">
                            <FolderOpen size={12} />
                            <span className="font-mono">{docStats.documents_dir}</span>
                        </div>
                    )}
                </>
            )}

            {/* Confirmation Modals */}
            <ConfirmModal
                isOpen={showReprocessModal}
                onClose={() => setShowReprocessModal(false)}
                onConfirm={reprocessKnowledgeBase}
                title="Reprocessar Base de Conhecimento"
                message="Esta ação irá APAGAR todos os documentos indexados e reprocessar tudo do zero. Isso pode levar vários minutos dependendo do volume de dados. Deseja continuar?"
                confirmText="Sim, Reprocessar"
                cancelText="Cancelar"
                variant="danger"
                loading={ingestionStatus?.running}
            />

            {/* Scan Modal */}
            {showScanModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowScanModal(false)} />
                    <div className="relative bg-zinc-900 border border-white/10 rounded-2xl shadow-2xl max-w-lg w-full mx-4 animate-fade-in overflow-hidden">
                        <div className="p-6">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-2 bg-indigo-500/10 rounded-xl">
                                    <RefreshCw className="text-indigo-400" size={24} />
                                </div>
                                <h3 className="text-lg font-semibold text-white">
                                    Documentos Pendentes
                                </h3>
                            </div>

                            <p className="text-zinc-400 text-sm mb-4">
                                Os seguintes arquivos foram detectados como novos ou modificados e serão processados:
                            </p>

                            <div className="max-h-60 overflow-y-auto space-y-2 mb-6 pr-2">
                                {pendingFiles.map((file, idx) => (
                                    <div key={idx} className="flex items-center justify-between p-2 bg-white/5 rounded-lg border border-white/5">
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${file.reason === 'new' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'
                                                }`}>
                                                {file.reason === 'new' ? 'Novo' : 'Modificado'}
                                            </span>
                                            <span className="text-zinc-300 text-sm truncate">{file.file}</span>
                                        </div>
                                        <span className="text-zinc-500 text-[10px] font-mono whitespace-nowrap">
                                            {(file.size / 1024).toFixed(1)} KB
                                        </span>
                                    </div>
                                ))}
                            </div>

                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowScanModal(false)}
                                    className="flex-1 px-4 py-2.5 text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={() => {
                                        setShowScanModal(false);
                                        startIngestion(false);
                                    }}
                                    className="flex-1 px-4 py-2.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition-colors shadow-lg shadow-indigo-500/20"
                                >
                                    Iniciar Ingestão
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* No Files Modal */}
            {showNoFilesModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowNoFilesModal(false)} />
                    <div className="relative bg-zinc-900 border border-white/10 rounded-2xl shadow-2xl max-w-sm w-full mx-4 animate-fade-in overflow-hidden">
                        <div className="p-6 text-center">
                            <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                <CheckCircle className="text-emerald-500" size={32} />
                            </div>
                            <h3 className="text-lg font-semibold text-white mb-2">
                                Tudo Atualizado!
                            </h3>
                            <p className="text-zinc-400 text-sm mb-6">
                                Nenhum arquivo novo ou modificado foi detectado no diretório de documentos.
                            </p>
                            <button
                                onClick={() => setShowNoFilesModal(false)}
                                className="w-full px-4 py-2.5 text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl transition-colors"
                            >
                                Entendido
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
