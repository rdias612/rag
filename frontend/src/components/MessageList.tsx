import ReactMarkdown from 'react-markdown';
import { Bot, ArrowDown, FileText, Sparkles, Zap, BookOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";
import type { Message } from "../types";
import { useEffect, useRef, useState } from 'react';
import { DebugPanel } from './DebugPanel';

interface MessageListProps {
    messages: Message[];
    isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [userScrolled, setUserScrolled] = useState(false);

    // Auto-scroll when new messages arrive (only if user hasn't scrolled manually)
    useEffect(() => {
        if (!userScrolled && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages.length, userScrolled]);

    // Reset scroll state when loading ends
    useEffect(() => {
        if (!isLoading && !userScrolled && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
            setUserScrolled(false);
        }
    }, [isLoading, userScrolled]);

    const handleScroll = () => {
        if (containerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
            const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
            setShowScrollButton(!isNearBottom);

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
            className="flex-1 overflow-y-auto w-full pt-8 pb-32 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent"
        >
            <div className="max-w-3xl mx-auto px-4 space-y-8">
                {messages.length === 0 && (
                    <div className="h-[70vh] flex flex-col items-center justify-center text-center px-4 animate-fade-in">
                        <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-indigo-500 to-purple-500 p-[1px] mb-8 shadow-2xl shadow-indigo-500/20">
                            <div className="w-full h-full rounded-[23px] bg-zinc-900 flex items-center justify-center">
                                <Sparkles className="w-8 h-8 text-indigo-400" />
                            </div>
                        </div>

                        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400 mb-3">
                            Hello, Rian.
                        </h1>
                        <p className="text-zinc-500 text-lg max-w-md mb-12">
                            I'm your intelligent RAG assistant. How can I help you explore your documents today?
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
                            {[
                                { icon: Zap, label: "Deep Dive", text: "Analyze complex documents" },
                                { icon: BookOpen, label: "Summarize", text: "Get quick overviews" },
                            ].map((item, i) => (
                                <button key={i} className="flex flex-col items-start p-4 rounded-xl bg-[#18181b] border border-white/5 hover:border-indigo-500/30 hover:bg-white/5 transition-all text-left group">
                                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 mb-3 group-hover:scale-110 transition-transform">
                                        <item.icon size={20} />
                                    </div>
                                    <span className="text-sm font-semibold text-zinc-200 mb-1">{item.label}</span>
                                    <span className="text-xs text-zinc-500">{item.text}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <motion.div
                        key={idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={cn(
                            "flex gap-4 w-full",
                            msg.role === 'user' ? "justify-end" : "justify-start"
                        )}
                    >
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0 mt-1">
                                <Bot size={18} />
                            </div>
                        )}

                        <div className={cn("flex flex-col gap-2 max-w-[85%]", msg.role === 'user' && "items-end")}>
                            {msg.role === 'user' ? (
                                <div className="bg-accent-primary text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-lg shadow-indigo-500/10">
                                    <p className="leading-relaxed text-[15px]">{msg.content}</p>
                                </div>
                            ) : (
                                <div className="prose prose-invert prose-zinc max-w-none prose-p:leading-relaxed prose-pre:bg-[#18181b] prose-pre:border prose-pre:border-white/5 prose-pre:rounded-xl">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </div>
                            )}

                            {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                                <div className="flex gap-2 flex-wrap mt-2">
                                    {msg.sources.map((source, i) => (
                                        <div
                                            key={i}
                                            className="bg-[#18181b] border border-white/5 hover:border-indigo-500/30 hover:bg-indigo-500/5 transition-all rounded-lg p-2.5 text-xs flex items-center gap-2 cursor-help"
                                            title={source.filename}
                                        >
                                            <FileText size={14} className="text-indigo-400" />
                                            <span className="text-zinc-300 max-w-[150px] truncate">
                                                {source.filename}
                                                {source.page ? <span className="opacity-50 ml-1">· P{source.page}</span> : null}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Debug Panel */}
                            {msg.role === 'assistant' && msg.debugInfo && (
                                <DebugPanel debugInfo={msg.debugInfo} />
                            )}
                        </div>
                    </motion.div>
                ))}

                <AnimatePresence>
                    {isLoading && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            className="flex gap-4 items-start"
                        >
                            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0 mt-1">
                                <Bot size={18} />
                            </div>
                            <div className="flex flex-col gap-2">
                                <div className="flex gap-1 h-6 items-center px-2">
                                    <span className="w-1.5 h-1.5 bg-zinc-600 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                    <span className="w-1.5 h-1.5 bg-zinc-600 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-1.5 h-1.5 bg-zinc-600 rounded-full animate-bounce"></span>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <div ref={bottomRef} />
            </div>

            {showScrollButton && (
                <motion.button
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    onClick={scrollToBottom}
                    className="fixed bottom-32 right-8 bg-zinc-800 text-zinc-200 p-2.5 rounded-full shadow-xl border border-white/10 hover:bg-white/10 transition-colors z-30"
                >
                    <ArrowDown size={20} />
                </motion.button>
            )}
        </div>
    );
}
