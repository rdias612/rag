import { Plus, MessageSquare, Trash2, History, Settings } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";
import type { Session, RetrievalMode } from "../types";
import { TemperatureSelector } from "./TemperatureSelector";
import { RetrievalModeSelector } from "./RetrievalModeSelector";
import { useState } from "react";

interface SidebarProps {
    sessions: Session[];
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    onDeleteSession: (e: React.MouseEvent, id: string) => void;
    isOpen: boolean;
    setIsOpen: (open: boolean) => void;
    temperature: number | undefined;
    setTemperature: (temp: number | undefined) => void;
    promptMode: string;
    setPromptMode: (mode: string) => void;
    responseStyle: string;
    setResponseStyle: (style: string) => void;
    searchMode: RetrievalMode | undefined;
    setSearchMode: (mode: RetrievalMode | undefined) => void;
}

export function Sidebar({
    sessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    onDeleteSession,
    temperature,
    setTemperature,
    promptMode,
    setPromptMode,
    responseStyle,
    setResponseStyle,
    searchMode,
    setSearchMode
}: SidebarProps) {
    const [showSettings, setShowSettings] = useState(false);

    return (
        <aside className="relative w-72 bg-sidebar border-r border-border flex flex-col h-full">
            <div className="p-6 space-y-3">
                <div className="flex items-center gap-3 mb-8">
                    <div className="h-8 w-8 rounded-lg bg-accent-primary flex items-center justify-center font-bold text-white shadow-lg shadow-accent-primary/25">
                        R
                    </div>
                    <span className="font-semibold text-lg tracking-tight">RAG Assistant</span>
                </div>

                <button
                    onClick={onNewChat}
                    className="w-full flex items-center gap-3 bg-surface hover:bg-surface/80 text-text-primary px-4 py-3 rounded-xl transition-all border border-border group"
                >
                    <div className="p-1 rounded-md bg-accent-primary/10 text-accent-primary group-hover:bg-accent-primary group-hover:text-white transition-colors">
                        <Plus size={18} />
                    </div>
                    <span className="font-medium text-sm">New Chat</span>
                </button>

                <button
                    onClick={() => setShowSettings(!showSettings)}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all border group",
                        showSettings
                            ? "bg-accent-primary/10 border-accent-primary/30 text-accent-primary"
                            : "bg-surface hover:bg-surface/80 text-text-primary border-border"
                    )}
                >
                    <div className={cn(
                        "p-1 rounded-md transition-colors",
                        showSettings
                            ? "bg-accent-primary/20 text-accent-primary"
                            : "bg-accent-primary/10 text-accent-primary group-hover:bg-accent-primary group-hover:text-white"
                    )}>
                        <Settings size={18} />
                    </div>
                    <span className="font-medium text-sm">Configurações</span>
                </button>

                <AnimatePresence>
                    {showSettings && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                        >
                            <div className="pt-2 space-y-3">
                                <TemperatureSelector
                                    temperature={temperature}
                                    setTemperature={setTemperature}
                                />

                                <RetrievalModeSelector
                                    mode={searchMode}
                                    setMode={setSearchMode}
                                />

                                {/* Prompt Mode Selector */}
                                <div className="bg-surface rounded-lg p-3 border border-border">
                                    <label className="block text-xs font-medium text-text-secondary mb-2">
                                        Modo de Seleção de Prompts
                                    </label>
                                    <select
                                        value={promptMode}
                                        onChange={(e) => setPromptMode(e.target.value)}
                                        className="w-full bg-chat border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary"
                                    >
                                        <option value="category">📂 Cat egoria (Rápido)</option>
                                        <option value="llm_router">🤖 Inteligente (LLM)</option>
                                    </select>
                                    <p className="text-xs text-text-secondary mt-2">
                                        {promptMode === 'category'
                                            ? 'Busca automática por prioridade'
                                            : 'LLM escolhe o melhor prompt (+200ms)'}
                                    </p>
                                </div>

                                {/* Response Style Selector */}
                                <div className="bg-surface rounded-lg p-3 border border-border">
                                    <label className="block text-xs font-medium text-text-secondary mb-2">
                                        Estilo da Resposta
                                    </label>
                                    <div className="flex gap-2 p-1 bg-chat rounded-lg border border-border">
                                        <button
                                            onClick={() => setResponseStyle('detailed')}
                                            className={cn(
                                                "flex-1 py-1.5 text-xs font-medium rounded-md transition-all",
                                                responseStyle === 'detailed'
                                                    ? "bg-accent-primary text-white shadow-sm"
                                                    : "text-text-secondary hover:text-text-primary"
                                            )}
                                        >
                                            Detalhado
                                        </button>
                                        <button
                                            onClick={() => setResponseStyle('concise')}
                                            className={cn(
                                                "flex-1 py-1.5 text-xs font-medium rounded-md transition-all",
                                                responseStyle === 'concise'
                                                    ? "bg-accent-primary text-white shadow-sm"
                                                    : "text-text-secondary hover:text-text-primary"
                                            )}
                                        >
                                            Conciso
                                        </button>
                                    </div>
                                    <p className="text-xs text-text-secondary mt-2">
                                        {responseStyle === 'detailed'
                                            ? 'Respostas ricas e explicativas'
                                            : 'Respostas diretas (máx 3 frases)'}
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <div className="flex-1 overflow-y-auto px-4 pb-4">
                <div className="text-xs font-medium text-text-secondary mb-3 px-2 flex items-center gap-2">
                    <History size={12} />
                    RECENT ACTIVITY
                </div>

                <div className="space-y-1">
                    {sessions.map((session) => (
                        <div
                            key={session.session_id}
                            onClick={() => onSelectSession(session.session_id)}
                            className={cn(
                                "group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all",
                                currentSessionId === session.session_id
                                    ? "bg-accent-primary/10 text-accent-primary border border-accent-primary/10"
                                    : "text-text-secondary hover:bg-surface hover:text-text-primary border border-transparent"
                            )}
                        >
                            <MessageSquare size={16} className={cn(
                                "shrink-0",
                                currentSessionId === session.session_id ? "text-accent-primary" : "text-text-secondary"
                            )} />
                            <div className="flex-1 truncate text-xs font-medium">
                                {session.last_activity
                                    ? new Date(session.last_activity).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                                    : `Session ${session.session_id.slice(0, 8)}`}
                            </div>
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteSession(e, session.session_id);
                                }}
                                className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/10 hover:text-red-400 rounded-md transition-all"
                            >
                                <Trash2 size={13} />
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            <div className="p-4 border-t border-border">
                <div className="p-3 rounded-xl bg-accent-primary/5 border border-border">
                    <p className="text-xs text-text-secondary font-medium text-center">
                        Powered by <span className="text-accent-primary">Deepmind RAG</span>
                    </p>
                </div>
            </div>
        </aside>
    );
}
