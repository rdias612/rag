import { Plus, MessageSquare, Trash2, X, History } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";
import type { Session } from "../types";
import { TemperatureSelector } from "./TemperatureSelector";

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
}

export function Sidebar({
    sessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    onDeleteSession,
    isOpen,
    setIsOpen,
    temperature,
    setTemperature
}: SidebarProps) {
    return (
        <>
            {/* Mobile Toggle & Overlay */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsOpen(false)}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
                    />
                )}
            </AnimatePresence>

            {/* Sidebar Container */}
            <motion.aside
                initial={false}
                animate={{ x: isOpen ? 0 : "-100%" }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className={cn(
                    "fixed inset-y-0 left-0 z-50 w-72 bg-sidebar border-r border-border flex flex-col md:translate-x-0 transition-transform duration-300 ease-in-out",
                    // On desktop, we always want it visible if the layout allows, but for now we follow the isOpen prop for mobile
                    // Actually, let's force it visible on desktop via CSS override if needed, or better, trust the parent layout.
                    "md:relative md:translate-x-0"
                )}
                style={{ position: 'fixed', transform: undefined }} // Let CSS classes handle desktop reset
            >
                {/* Mobile Close Button */}
                <div className="md:hidden absolute -right-10 top-4">
                    {isOpen && (
                        <button
                            onClick={() => setIsOpen(false)}
                            className="p-2 text-white/70 hover:text-white"
                        >
                            <X size={24} />
                        </button>
                    )}
                </div>

                <div className="p-6">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="h-8 w-8 rounded-lg bg-accent-primary flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/25">
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

                <div className="p-4 border-t border-border space-y-6">
                    <TemperatureSelector
                        temperature={temperature}
                        setTemperature={setTemperature}
                    />

                    <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-border">
                        <p className="text-xs text-text-secondary font-medium text-center">
                            Powered by <span className="text-accent-primary">Deepmind RAG</span>
                        </p>
                    </div>
                </div>
            </motion.aside>
        </>
    );
}
