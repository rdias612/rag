import { Plus, MessageSquare, Trash2, Menu } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";
import type { Session } from "../types";

interface SidebarProps {
    sessions: Session[];
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    onDeleteSession: (e: React.MouseEvent, id: string) => void;
    isOpen: boolean;
    setIsOpen: (open: boolean) => void;
}

export function Sidebar({
    sessions,
    currentSessionId,
    onSelectSession,
    onNewChat,
    onDeleteSession,
    isOpen,
    setIsOpen
}: SidebarProps) {
    return (
        <>
            <button
                className="fixed top-4 left-4 z-50 md:hidden p-2 bg-gray-800 rounded-md text-white"
                onClick={() => setIsOpen(!isOpen)}
            >
                <Menu size={24} />
            </button>

            {/* Backdrop for mobile */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.5 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setIsOpen(false)}
                        className="fixed inset-0 bg-black z-40 md:hidden"
                    />
                )}
            </AnimatePresence>

            <motion.div
                className={cn(
                    "fixed inset-y-0 left-0 z-50 w-72 bg-gradient-to-b from-gray-900/90 to-gray-800/90 backdrop-blur-xl border-r border-white/10 flex flex-col transition-transform duration-300 md:relative md:translate-x-0",
                    isOpen ? "translate-x-0" : "-translate-x-full"
                )}
            >
                <div className="p-4 border-b border-white/10">
                    <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-6">
                        RAG Assistant
                    </h1>
                    <button
                        onClick={onNewChat}
                        className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg transition-all shadow-lg shadow-blue-900/20 font-medium"
                    >
                        <Plus size={20} />
                        New Chat
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-gray-700">
                    <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2 mt-2">
                        History
                    </h2>
                    <div className="space-y-1">
                        {sessions.map((session) => (
                            <div
                                key={session.session_id}
                                onClick={() => onSelectSession(session.session_id)}
                                className={cn(
                                    "group flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all hover:bg-white/5",
                                    currentSessionId === session.session_id ? "bg-white/10 text-white" : "text-gray-400"
                                )}
                            >
                                <MessageSquare size={18} />
                                <div className="flex-1 truncate text-sm">
                                    {session.last_activity ? new Date(session.last_activity).toLocaleString() : `Session ${session.session_id.slice(0, 8)}`}
                                </div>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDeleteSession(e, session.session_id);
                                    }}
                                    className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="p-4 border-t border-white/10 text-xs text-gray-500 text-center">
                    Powered by Deepmind RAG
                </div>
            </motion.div>
        </>
    );
}
