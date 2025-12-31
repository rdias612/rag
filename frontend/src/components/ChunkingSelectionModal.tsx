import { X, FileText, Check, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";

interface PendingFile {
    file: string;
    path: string;
    reason: 'new' | 'modified';
    size: number;
    chunkingType: 'hierarchical' | 'sentence';
}

interface ChunkingSelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    files: PendingFile[];
    onConfirm: (files: PendingFile[]) => void;
}

const CHUNKING_OPTIONS = [
    {
        value: 'hierarchical' as const,
        label: 'Explicação',
        icon: '📖',
        description: 'Melhor para explicações detalhadas e contexto amplo',
    },
    {
        value: 'sentence' as const,
        label: 'Precisão',
        icon: '🎯',
        description: 'Melhor para respostas diretas e dados específicos',
    },
];

export function ChunkingSelectionModal({
    isOpen,
    onClose,
    files,
    onConfirm,
}: ChunkingSelectionModalProps) {
    const [localFiles, setLocalFiles] = useState<PendingFile[]>([]);
    const [loading, setLoading] = useState(false);

    // Sincronizar com props quando modal abre
    useEffect(() => {
        if (isOpen) {
            setLocalFiles(files.map(f => ({ ...f })));
        }
    }, [isOpen, files]);

    const handleChunkingChange = (index: number, value: 'hierarchical' | 'sentence') => {
        setLocalFiles(prev => {
            const updated = [...prev];
            updated[index].chunkingType = value;
            return updated;
        });
    };

    const handleSetAllAs = (type: 'hierarchical' | 'sentence') => {
        setLocalFiles(prev => prev.map(f => ({ ...f, chunkingType: type })));
    };

    const handleConfirm = async () => {
        setLoading(true);
        onConfirm(localFiles);
    };

    const formatBytes = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    };

    const selectedHierarchical = localFiles.filter(f => f.chunkingType === 'hierarchical').length;
    const selectedSentence = localFiles.filter(f => f.chunkingType === 'sentence').length;

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.5 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black z-[100]"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="fixed inset-0 flex items-center justify-center z-[110] p-4 pointer-events-none"
                    >
                        <div className="bg-card border border-border rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col pointer-events-auto shadow-2xl">
                            {/* Header */}
                            <div className="p-6 border-b border-border">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-accent-primary/10 rounded-xl">
                                            <FileText className="text-accent-primary" size={24} />
                                        </div>
                                        <div>
                                            <h2 className="text-xl font-semibold text-text-primary">
                                                Documentos Pendentes ({files.length})
                                            </h2>
                                            <p className="text-sm text-text-secondary">
                                                Selecione o tipo de chunking para cada documento
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={onClose}
                                        className="p-1.5 hover:bg-surface rounded-lg transition-colors text-text-secondary hover:text-text-primary"
                                        disabled={loading}
                                    >
                                        <X size={20} />
                                    </button>
                                </div>

                                {/* Quick Select Buttons */}
                                <div className="flex items-center gap-3 text-sm">
                                    <span className="text-text-secondary">Selecionar tudo como:</span>
                                    {CHUNKING_OPTIONS.map(option => (
                                        <button
                                            key={option.value}
                                            onClick={() => handleSetAllAs(option.value)}
                                            className="flex items-center gap-2 px-4 py-2 bg-surface hover:bg-surface/80 text-text-primary rounded-lg transition-colors border border-border"
                                            disabled={loading}
                                        >
                                            <span>{option.icon}</span>
                                            <span>{option.label}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Stats */}
                            <div className="px-6 py-3 bg-surface border-b border-border flex items-center gap-6 text-sm">
                                <div className="flex items-center gap-2">
                                    <span className="text-text-secondary">📖 Explicação:</span>
                                    <span className="font-medium text-text-primary">{selectedHierarchical}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-text-secondary">🎯 Precisão:</span>
                                    <span className="font-medium text-text-primary">{selectedSentence}</span>
                                </div>
                            </div>

                            {/* Files List */}
                            <div className="flex-1 overflow-y-auto">
                                <div className="divide-y divide-border">
                                    {localFiles.map((file, index) => (
                                        <div
                                            key={file.path}
                                            className="p-4 hover:bg-surface/50 transition-colors"
                                        >
                                            <div className="flex items-center gap-4">
                                                {/* File Info */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <FileText size={16} className="text-text-secondary flex-shrink-0" />
                                                        <span className="text-sm font-medium text-text-primary truncate">
                                                            {file.file}
                                                        </span>
                                                        <span
                                                            className={cn(
                                                                "text-[10px] px-2 py-0.5 rounded font-bold uppercase flex-shrink-0",
                                                                file.reason === 'new'
                                                                    ? 'bg-emerald-500/10 text-emerald-500'
                                                                    : 'bg-amber-500/10 text-amber-500'
                                                            )}
                                                        >
                                                            {file.reason === 'new' ? 'Novo' : 'Modificado'}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-text-secondary">
                                                        <span>{formatBytes(file.size)}</span>
                                                    </div>
                                                </div>

                                                {/* Chunking Type Selector */}
                                                <div className="flex-shrink-0">
                                                    <select
                                                        value={file.chunkingType}
                                                        onChange={(e) => handleChunkingChange(index, e.target.value as 'hierarchical' | 'sentence')}
                                                        className={cn(
                                                            "appearance-none bg-surface border border-border rounded-lg px-4 py-2 pr-8 text-sm font-medium",
                                                            "focus:outline-none focus:ring-2 focus:ring-accent-primary/50",
                                                            file.chunkingType === 'hierarchical'
                                                                ? "text-blue-400"
                                                                : "text-purple-400",
                                                            loading && "opacity-50 cursor-not-allowed"
                                                        )}
                                                        disabled={loading}
                                                    >
                                                        {CHUNKING_OPTIONS.map(option => (
                                                            <option
                                                                key={option.value}
                                                                value={option.value}
                                                                className="text-text-primary bg-card"
                                                            >
                                                                {option.icon} {option.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="p-6 border-t border-border flex items-center justify-between">
                                <button
                                    onClick={onClose}
                                    disabled={loading}
                                    className="px-6 py-2.5 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={handleConfirm}
                                    disabled={loading || localFiles.length === 0}
                                    className={cn(
                                        "px-6 py-2.5 text-sm font-medium bg-accent-primary hover:bg-accent-hover text-white rounded-xl transition-colors flex items-center gap-2",
                                        loading && "opacity-50 cursor-not-allowed",
                                        localFiles.length === 0 && "opacity-50 cursor-not-allowed"
                                    )}
                                >
                                    {loading ? (
                                        <>
                                            <Loader2 size={16} className="animate-spin" />
                                            Processando...
                                        </>
                                    ) : (
                                        <>
                                            <Check size={16} />
                                            Iniciar Ingestão
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
