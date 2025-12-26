import { motion, AnimatePresence } from "framer-motion";
import { X, FileText, BookOpen } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import type { Source } from "../types";

interface SourceModalProps {
    source: Source | null;
    isOpen: boolean;
    onClose: () => void;
}

export function SourceModal({ source, isOpen, onClose }: SourceModalProps) {
    if (!source) return null;

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                    >
                        {/* Modal Content */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-[#18181b] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl relative overflow-hidden"
                        >
                            {/* Header */}
                            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-[#09090b]/50">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                                        <FileText size={20} />
                                    </div>
                                    <div>
                                        <h3 className="font-medium text-zinc-100">{source.filename}</h3>
                                        {source.page && (
                                            <span className="text-xs text-zinc-400 flex items-center gap-1">
                                                <BookOpen size={12} />
                                                Página {source.page}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            {/* Body - Scrollable */}
                            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent">
                                <div className="prose prose-invert prose-zinc max-w-none">
                                    <h4 className="text-zinc-400 text-sm font-medium uppercase tracking-wider mb-4 border-b border-white/5 pb-2">
                                        Conteúdo do Trecho
                                    </h4>
                                    <div className="bg-zinc-900/50 p-4 rounded-xl border border-white/5 text-zinc-300 leading-relaxed font-mono text-sm whitespace-pre-wrap">
                                        {source.content}
                                    </div>
                                </div>
                            </div>

                            {/* Footer */}
                            <div className="p-4 border-t border-white/10 bg-[#09090b]/50 flex justify-end">
                                <button
                                    onClick={onClose}
                                    className="px-4 py-2 bg-white/5 hover:bg-white/10 text-zinc-200 rounded-lg text-sm font-medium transition-colors border border-white/5"
                                >
                                    Fechar Visualização
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
