import { useState, useEffect, useRef, useCallback } from 'react';
import {
    HardDrive,
    FolderOpen,
    FileText,
    RefreshCw,
    Database,
    Trash2,
    Play,
    AlertCircle,
    AlertTriangle,
    XCircle,
    CheckCircle,
    Clock,
    Loader2,
    RotateCcw
} from 'lucide-react';
import { ConfirmModal } from '../ConfirmModal';
import { ChunkingSelectionModal } from '../ChunkingSelectionModal';
import { API_URL } from '../../api';

interface DocumentStats {
    total_files: number;
    files_by_type: Record<string, number>;
    indexed_chunks: number;
    total_size_mb?: number;
    documents_dir?: string;
}

interface IngestedDocument {
    id?: number;
    file_path: string;
    file_name: string;
    file_hash?: string;
    file_size: number;
    collection_id: string;
    chunks_count: number;
    status: string;
    ingested_at: string | null;
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
    const [showNoFilesModal, setShowNoFilesModal] = useState(false);
    const [showChunkingSelectionModal, setShowChunkingSelectionModal] = useState(false);
    const [pendingFiles, setPendingFiles] = useState<any[]>([]);
    const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
    const [scanning, setScanning] = useState(false);
    const [isReprocessing, setIsReprocessing] = useState(false); // Diferenciar entre atualizar e reprocessar

    // Column resizing states
    const [fileColumnWidth, setFileColumnWidth] = useState(300);
    const isResizing = useRef(false);
    const startX = useRef(0);
    const startWidth = useRef(0);

    const handleMouseMove = useCallback((e: MouseEvent) => {
        if (!isResizing.current) return;
        const deltaX = e.clientX - startX.current;
        const newWidth = Math.max(100, Math.min(800, startWidth.current + deltaX));
        setFileColumnWidth(newWidth);
    }, []);

    const handleMouseUp = useCallback(() => {
        isResizing.current = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'default';
        document.body.style.userSelect = 'auto';
    }, [handleMouseMove]);

    const handleMouseDown = (e: React.MouseEvent) => {
        isResizing.current = true;
        startX.current = e.clientX;
        startWidth.current = fileColumnWidth;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    };

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
                fetchWithTimeout(`${API_URL}/documents/directory`).then(r => {
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

    const startIngestion = async (force: boolean = false, files_to_ingest: string[] | null = null, files_with_chunking: any[] | null = null) => {
        setLoading(true);
        try {
            const body: any = {
                force
            };

            if (files_with_chunking) {
                body.files = files_with_chunking;
            } else if (files_to_ingest) {
                body.files = files_to_ingest;
            }

            const res = await fetch(`${API_URL}/documents/ingest-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
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
        setIsReprocessing(false); // Modo atualizar
        try {
            const res = await fetch(`${API_URL}/documents/scan-with-selection`);
            if (!res.ok) throw new Error("Failed to scan documents");
            const data = await res.json();

            if (data.pending && data.pending.length > 0) {
                setPendingFiles(data.pending);
                setShowChunkingSelectionModal(true);
            } else {
                setShowNoFilesModal(true);
            }
        } catch (error) {
            console.error("Error scanning:", error);
        } finally {
            setScanning(false);
        }
    };

    const handleChunkingSelectionConfirm = (filesWithChunking: any[]) => {
        setShowChunkingSelectionModal(false);
        // Converter para formato esperado pelo backend
        const filesForBackend = filesWithChunking.map(f => ({
            file_path: f.path,
            chunking_type: f.chunkingType
        }));

        // Se for reprocessamento, usa /documents/reprocess, senão usa /documents/ingest-all
        if (isReprocessing) {
            startReprocessWithChunking(filesForBackend);
        } else {
            startIngestion(true, null, filesForBackend);
        }
    };

    const startReprocessWithChunking = async (filesWithChunking: any[]) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/documents/reprocess`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: filesWithChunking })
            });

            if (res.ok) {
                const data = await res.json();
                setIngestionStatus({
                    running: true,
                    progress: 0,
                    total: data.total_files,
                    current_file: null,
                    message: 'Base limpa. Reprocessando com seleção de chunking...',
                    results: []
                });
                // Atualizar lista de documentos ingeridos (agora vazia)
                setIngestedDocs([]);
                // Iniciar polling
                fetchData();
            }
        } catch (error) {
            console.error("Error starting reprocess:", error);
        } finally {
            setLoading(false);
        }
    };

    const reprocessKnowledgeBase = async () => {
        setShowReprocessModal(false);
        setIsReprocessing(true); // Marca como modo reprocessamento
        setScanning(true);
        try {
            const res = await fetch(`${API_URL}/documents/scan-all`);
            if (!res.ok) throw new Error("Failed to scan documents");
            const data = await res.json();

            if (data.pending && data.pending.length > 0) {
                setPendingFiles(data.pending);
                setShowChunkingSelectionModal(true);
            } else {
                setShowNoFilesModal(true);
            }
        } catch (error) {
            console.error('Failed to scan all documents:', error);
        } finally {
            setScanning(false);
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

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return '-';
            return date.toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return '-';
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
            case 'ok':
            case 'completed':
                return <CheckCircle size={16} className="text-emerald-400" />;
            case 'not_processed':
                return <XCircle size={16} className="text-rose-400" />;
            case 'outdated':
                return <AlertTriangle size={16} className="text-amber-400" />;
            case 'processing':
                return <Loader2 size={16} className="text-accent-primary animate-spin" />;
            case 'failed':
            case 'error':
                return <AlertCircle size={16} className="text-rose-400" />;
            case 'pending':
                return <Clock size={16} className="text-amber-400" />;
            default:
                return <Clock size={16} className="text-text-secondary" />;
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-text-primary flex items-center gap-2">
                    <HardDrive size={24} className="text-accent-primary" />
                    Documentos
                </h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleScanClick}
                        disabled={loading || scanning || ingestionStatus?.running}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-accent-primary hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {scanning ? (
                            <Loader2 size={14} className="animate-spin" />
                        ) : ingestionStatus?.running ? (
                            <Loader2 size={14} className="animate-spin" />
                        ) : (
                            <Play size={14} />
                        )}
                        {scanning ? 'Escaneando...' : ingestionStatus?.running ? 'Processando...' : 'Atualizar'}
                    </button>
                    <button
                        onClick={() => setShowReprocessModal(true)}
                        disabled={loading || ingestionStatus?.running}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-amber-600 hover:bg-amber-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Limpa todos os dados e permite escolher tipo de chunking para cada documento"
                    >
                        <RotateCcw size={14} />
                        Reprocessar Base
                    </button>
                    <button
                        onClick={fetchData}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface hover:bg-surface/80 text-text-primary rounded-lg transition-colors disabled:opacity-50 border border-border"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                        Atualizar
                    </button>
                </div>
            </div>

            {/* Warning for unsupported formats */}
            <div className="flex items-center gap-2 px-4 py-2 bg-amber-500/5 border border-amber-500/10 rounded-xl text-[11px] text-amber-500/80">
                <AlertCircle size={14} />
                <span>
                    <strong>Nota:</strong> Atualmente, o processamento de arquivos de <strong>imagem</strong> (.jpg, .png, etc.) e <strong>áudio</strong> (.mp3, .wav, etc.) está desabilitado, pois requerem integração com APIs multimodais.
                </span>
            </div>

            {/* Ingestion Progress */}
            {ingestionStatus?.running && (
                <div className="bg-accent-primary/10 border border-accent-primary/30 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-accent-primary">
                            Ingestão em Andamento
                        </span>
                        <span className="text-sm text-accent-primary">
                            {ingestionStatus.progress} / {ingestionStatus.total}
                        </span>
                    </div>
                    <div className="w-full bg-surface rounded-full h-2 mb-2">
                        <div
                            className="bg-accent-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${ingestionStatus.total > 0 ? (ingestionStatus.progress / ingestionStatus.total) * 100 : 0}%` }}
                        />
                    </div>
                    <p className="text-xs text-text-secondary truncate">
                        {ingestionStatus.message}
                    </p>
                </div>
            )}

            {/* Ingestion Results */}
            {!ingestionStatus?.running && ingestionStatus?.results && ingestionStatus.results.length > 0 && (
                <div className="bg-card border border-border rounded-xl p-4">
                    <h3 className="text-sm font-medium text-text-primary mb-3">Última Ingestão</h3>
                    <p className="text-xs text-text-secondary mb-3">{ingestionStatus.message}</p>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                        {ingestionStatus.results.map((result, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-xs">
                                {getStatusIcon(result.status)}
                                <span className="text-text-primary truncate flex-1">{result.file}</span>
                                {result.chunks !== undefined && (
                                    <span className="text-text-secondary">
                                        {result.chunks}
                                        {result.total_chunks && result.total_chunks !== result.chunks ? `/${result.total_chunks}` : ''} chunks
                                    </span>
                                )}
                                {result.message && result.status !== 'success' && (
                                    <span className="text-text-secondary">{result.message}</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw size={24} className="animate-spin text-text-secondary" />
                </div>
            ) : (
                <>
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="bg-card backdrop-blur-xl border border-border rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-text-secondary text-sm">Arquivos no Dir</span>
                                <FileText size={16} className="text-accent-primary" />
                            </div>
                            <p className="text-2xl font-bold text-text-primary">
                                {docStats?.total_files || 0}
                            </p>
                        </div>

                        <div className="bg-card backdrop-blur-xl border border-border rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-text-secondary text-sm">Docs Ingeridos</span>
                                <CheckCircle size={16} className="text-emerald-400" />
                            </div>
                            <p className="text-2xl font-bold text-text-primary">
                                {ingestedDocs.filter(d => d.status === 'ok' || d.status === 'outdated').length}
                            </p>
                        </div>

                        <div className="bg-card backdrop-blur-xl border border-border rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-text-secondary text-sm">Chunks Indexados</span>
                                <Database size={16} className="text-purple-400" />
                            </div>
                            <p className="text-2xl font-bold text-text-primary">
                                {docStats?.indexed_chunks?.toLocaleString() || 0}
                            </p>
                        </div>

                        <div className="bg-card backdrop-blur-xl border border-border rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-text-secondary text-sm">Collections</span>
                                <FolderOpen size={16} className="text-yellow-400" />
                            </div>
                            <p className="text-2xl font-bold text-text-primary">
                                {collections.length}
                            </p>
                        </div>
                    </div>

                    {/* Ingested Documents Table */}
                    <div className="bg-card backdrop-blur-xl border border-border rounded-xl overflow-hidden">
                        <div className="p-4 border-b border-border flex items-center justify-between">
                            <h3 className="text-sm font-medium text-text-primary">Documentos</h3>
                            {selectedDocs.length > 0 && (
                                <button
                                    onClick={() => startIngestion(true, selectedDocs)}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-accent-primary hover:bg-accent-hover text-white text-xs font-medium rounded-lg transition-colors shadow-lg shadow-accent-primary/10"
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
                                        <tr className="text-left text-xs text-text-secondary border-b border-border">
                                            <th className="px-4 py-3 w-10">
                                                <input
                                                    type="checkbox"
                                                    className="rounded border-border bg-surface text-accent-primary focus:ring-accent-primary/50"
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
                                            <th
                                                className="px-4 py-3 font-medium relative group"
                                                style={{ width: `${fileColumnWidth}px`, minWidth: `${fileColumnWidth}px`, maxWidth: `${fileColumnWidth}px` }}
                                            >
                                                <span>Arquivo</span>
                                                <div
                                                    onMouseDown={handleMouseDown}
                                                    className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-accent-primary/50 transition-colors z-10"
                                                    title="Arraste para redimensionar"
                                                />
                                            </th>
                                            <th className="px-4 py-3 font-medium text-text-secondary">Coleção</th>
                                            <th className="px-4 py-3 font-medium text-text-secondary">Chunks</th>
                                            <th className="px-4 py-3 font-medium text-text-secondary">Tamanho</th>
                                            <th className="px-4 py-3 font-medium text-text-secondary">Data</th>
                                            <th className="px-4 py-3 font-medium text-text-secondary">Status</th>
                                            <th className="px-4 py-3 font-medium w-20 text-text-secondary">Ações</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {ingestedDocs.map((doc) => (
                                            <tr
                                                key={doc.file_path}
                                                className={`border-b border-border hover:bg-surface transition-colors ${selectedDocs.includes(doc.file_path) ? 'bg-accent-primary/5' : ''
                                                    }`}
                                            >
                                                <td className="px-4 py-3">
                                                    <input
                                                        type="checkbox"
                                                        className="rounded border-border bg-surface text-accent-primary focus:ring-accent-primary/50"
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
                                                <td className="px-4 py-3 overflow-hidden">
                                                    <div className="flex items-center gap-2 overflow-hidden">
                                                        <span className="shrink-0">{getFileIcon(doc.file_name.substring(doc.file_name.lastIndexOf('.')))}</span>
                                                        <span
                                                            className="text-sm text-text-primary truncate"
                                                            style={{ maxWidth: `${fileColumnWidth - 60}px` }}
                                                            title={doc.file_name}
                                                        >
                                                            {doc.file_name}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className="text-xs px-2 py-1 bg-accent-primary/10 text-accent-primary rounded">
                                                        {doc.collection_id}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-sm text-text-primary">
                                                    {doc.chunks_count}
                                                </td>
                                                <td className="px-4 py-3 text-sm text-text-secondary">
                                                    {formatBytes(doc.file_size)}
                                                </td>
                                                <td className="px-4 py-3 text-xs text-text-secondary">
                                                    {formatDate(doc.ingested_at)}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {getStatusIcon(doc.status)}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {(doc.status === 'ok' || doc.status === 'outdated' || doc.status === 'error') ? (
                                                        deleteConfirm === doc.file_path ? (
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
                                                                    className="text-xs px-2 py-1 bg-surface hover:bg-surface/80 text-text-primary rounded transition-colors border border-border"
                                                                >
                                                                    Não
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button
                                                                onClick={() => setDeleteConfirm(doc.file_path)}
                                                                className="p-1.5 hover:bg-red-500/10 text-text-secondary hover:text-red-400 rounded transition-colors"
                                                                title="Deletar documento"
                                                            >
                                                                <Trash2 size={14} />
                                                            </button>
                                                        )
                                                    ) : (
                                                        <div className="w-8" />
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="p-8 text-center text-text-secondary">
                                <Database size={32} className="mx-auto mb-2 opacity-30" />
                                <p className="text-sm">Nenhum documento ingerido ainda</p>
                                <p className="text-xs mt-1 text-text-secondary">Clique em "Atualizar" para processar documentos</p>
                            </div>
                        )}
                    </div>

                    {/* Files by Type */}
                    <div className="glass rounded-xl p-4">
                        <h3 className="text-sm font-medium text-text-primary mb-4">Arquivos por Tipo (no diretório)</h3>
                        {docStats?.files_by_type && Object.keys(docStats.files_by_type).length > 0 ? (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {Object.entries(docStats.files_by_type).map(([ext, count]) => (
                                    <div
                                        key={ext}
                                        className="flex items-center gap-2 bg-surface rounded-lg p-3 border border-border"
                                    >
                                        <span className="text-xl">{getFileIcon(ext)}</span>
                                        <div>
                                            <p className="text-text-primary font-medium">{count}</p>
                                            <p className="text-xs text-text-secondary uppercase">{ext}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-text-secondary text-sm">Nenhum documento encontrado</p>
                        )}
                    </div>

                    {/* Documents Path */}
                    {
                        docStats?.documents_dir && (
                            <div className="text-xs text-text-secondary flex items-center gap-2">
                                <FolderOpen size={12} />
                                <span className="font-mono">{docStats.documents_dir}</span>
                            </div>
                        )
                    }
                </>
            )
            }

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

            {/* No Files Modal */}
            {
                showNoFilesModal && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center">
                        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowNoFilesModal(false)} />
                        <div className="relative bg-card border border-border rounded-2xl shadow-2xl max-w-sm w-full mx-4 animate-fade-in overflow-hidden">
                            <div className="p-6 text-center">
                                <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <CheckCircle className="text-emerald-500" size={32} />
                                </div>
                                <h3 className="text-lg font-semibold text-text-primary mb-2">
                                    Tudo Atualizado!
                                </h3>
                                <p className="text-text-secondary text-sm mb-6">
                                    Nenhum arquivo novo ou modificado foi detectado no diretório de documentos.
                                </p>
                                <button
                                    onClick={() => setShowNoFilesModal(false)}
                                    className="w-full px-4 py-2.5 text-sm font-medium bg-surface hover:bg-surface/80 text-text-primary rounded-xl transition-colors border border-border"
                                >
                                    Entendido
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Chunking Selection Modal */}
            <ChunkingSelectionModal
                isOpen={showChunkingSelectionModal}
                onClose={() => setShowChunkingSelectionModal(false)}
                files={pendingFiles}
                onConfirm={handleChunkingSelectionConfirm}
            />
        </div >
    );
}
