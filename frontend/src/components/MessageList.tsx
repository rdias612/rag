import ReactMarkdown from 'react-markdown';
import { Bot, User, ArrowDown } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "../utils";
import type { Message } from "../types";
import { useEffect, useRef, useState } from 'react';

interface MessageListProps {
    messages: Message[];
    isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [userScrolled, setUserScrolled] = useState(false);

    // Auto-scroll quando novas mensagens chegam (apenas se usuário não scrollou manualmente)
    useEffect(() => {
        if (!userScrolled && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages.length, userScrolled]);

    // Reset scroll state quando loading termina
    useEffect(() => {
        if (!isLoading && !userScrolled && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
            setUserScrolled(false);
        }
    }, [isLoading, userScrolled]);

    // Detectar se usuário scrollou para cima
    const handleScroll = () => {
        if (containerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
            const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
            setShowScrollButton(!isNearBottom);

            // Marcar que usuário scrollou se não estiver no fim
            if (!isNearBottom) {
                setUserScrolled(true);
            } else {
                setUserScrolled(false);
            }
        }
    };

    const scrollToBottom = () => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
        setUserScrolled(false);
    };

    return (
        <div
            ref={containerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-gray-700 relative"
        >
            {messages.length === 0 && !isLoading && (
                <div className="h-full flex flex-col items-center justify-center text-gray-500 opacity-50">
                    <Bot size={64} className="mb-4" />
                    <p className="text-lg">How can I help you today?</p>
                </div>
            )}

            {messages.map((msg, idx) => (
                <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                        "flex gap-4 max-w-4xl mx-auto",
                        msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                    )}
                >
                    <div className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-lg",
                        msg.role === 'user' ? "bg-blue-600" : "bg-emerald-600"
                    )}>
                        {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                    </div>

                    <div className={cn(
                        "rounded-2xl p-4 shadow-md max-w-[80%]",
                        msg.role === 'user'
                            ? "bg-blue-600/20 border border-blue-500/30 text-blue-50 rounded-tr-sm"
                            : "bg-gray-800/80 border border-white/5 text-gray-100 rounded-tl-sm backdrop-blur-md"
                    )}>
                        <div className="prose prose-invert prose-sm max-w-none leading-relaxed">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>

                        {msg.sources && msg.sources.length > 0 && (
                            <div className="mt-4 pt-3 border-t border-white/10">
                                <p className="text-xs font-semibold text-gray-400 mb-2">Sources:</p>
                                <div className="flex flex-wrap gap-2">
                                    {msg.sources.map((source, i) => (
                                        <span key={i} className="text-xs bg-black/30 px-2 py-1 rounded border border-white/5 text-gray-300">
                                            {source.filename}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </motion.div>
            ))}

            {isLoading && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex gap-4 max-w-4xl mx-auto"
                >
                    <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0 animate-pulse">
                        <Bot size={18} />
                    </div>
                    <div className="bg-gray-800/50 p-4 rounded-2xl rounded-tl-sm flex gap-1 items-center h-12">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    </div>
                </motion.div>
            )}

            {/* Elemento invisível para scroll */}
            <div ref={bottomRef} />

            {/* Botão para voltar ao fim */}
            {showScrollButton && (
                <motion.button
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    onClick={scrollToBottom}
                    className="fixed bottom-24 right-8 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors z-10"
                    title="Ir para o fim"
                >
                    <ArrowDown size={20} />
                </motion.button>
            )}
        </div>
    );
}
