import ReactMarkdown from 'react-markdown';
import { Bot, ArrowDown, FileText, Sparkles, Zap, BookOpen, ThumbsUp, ThumbsDown, Copy, Check, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";
import type { Message } from "../types";
import { useEffect, useRef, useState } from 'react';
import { DebugPanel } from './DebugPanel';
import { SourceModal } from './SourceModal';
import { ExplanationModal } from './ExplanationModal';
import type { Source } from '../types';

interface MessageListProps {
    messages: Message[];
    isLoading: boolean;
    onFeedback: (index: number, rating: number) => void;
}

export function MessageList({ messages, isLoading, onFeedback }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [showScrollButton, setShowScrollButton] = useState(false);
    const [userScrolled, setUserScrolled] = useState(false);
    const [selectedSource, setSelectedSource] = useState<Source | null>(null);
    const [selectedExplanation, setSelectedExplanation] = useState<Message['explanation'] | null>(null);
    const [showExplanation, setShowExplanation] = useState(false);
    const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

    const handleCopy = (content: string, index: number) => {
        navigator.clipboard.writeText(content);
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
    };

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
                        <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-blue-500 to-blue-300 p-[1px] mb-8 shadow-2xl shadow-blue-500/20">
                            <div className="w-full h-full rounded-[23px] bg-card flex items-center justify-center">
                                <Sparkles className="w-8 h-8 text-blue-500" />
                            </div>
                        </div>

                        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-blue-400 mb-3">
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
                                <button key={i} className="flex flex-col items-start p-4 rounded-xl bg-card border border-border hover:border-accent-primary/30 hover:bg-accent-primary/5 transition-all text-left group">
                                    <div className="p-2 rounded-lg bg-accent-primary/10 text-accent-primary mb-3 group-hover:scale-110 transition-transform">
                                        <item.icon size={20} />
                                    </div>
                                    <span className="text-sm font-semibold text-text-primary mb-1">{item.label}</span>
                                    <span className="text-xs text-text-secondary">{item.text}</span>
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
                            "flex gap-4 w-full group",
                            msg.role === 'user' ? "justify-end" : "justify-start"
                        )}
                    >
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-lg bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-accent-primary shrink-0 mt-1">
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
                                            onClick={() => setSelectedSource(source)}
                                            className="bg-card border border-border hover:border-accent-primary/30 hover:bg-accent-primary/5 transition-all rounded-lg p-2.5 text-xs flex items-center gap-2 cursor-pointer group/source"
                                            title="Clique para ver o conteúdo"
                                        >
                                            <FileText size={14} className="text-accent-primary" />
                                            <span className="text-text-secondary max-w-[150px] truncate">
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

                            {/* Feedback Buttons */}
                            {msg.role === 'assistant' && !isLoading && (
                                <div className="flex items-center gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => onFeedback(idx, 1)}
                                        className={cn(
                                            "p-1.5 rounded-lg transition-colors",
                                            msg.feedback === 'good'
                                                ? "text-emerald-400 bg-emerald-500/10"
                                                : "text-zinc-500 hover:text-emerald-400 hover:bg-emerald-500/10"
                                        )}
                                        title="Útil"
                                    >
                                        <ThumbsUp size={14} fill={msg.feedback === 'good' ? "currentColor" : "none"} />
                                    </button>
                                    <button
                                        onClick={() => onFeedback(idx, 0)}
                                        className={cn(
                                            "p-1.5 rounded-lg transition-colors",
                                            msg.feedback === 'bad'
                                                ? "text-rose-400 bg-rose-500/10"
                                                : "text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10"
                                        )}
                                        title="Não foi útil"
                                    >
                                        <ThumbsDown size={14} fill={msg.feedback === 'bad' ? "currentColor" : "none"} />
                                    </button>
                                    <div className="w-px h-3 bg-white/10 mx-1" />
                                    <button
                                        onClick={() => handleCopy(msg.content, idx)}
                                        className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition-colors"
                                        title="Copiar resposta"
                                    >
                                        {copiedIndex === idx ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                                    </button>
                                    {msg.explanation && (
                                        <button
                                            onClick={() => {
                                                setSelectedExplanation(msg.explanation);
                                                setShowExplanation(true);
                                            }}
                                            className="p-1.5 rounded-lg text-zinc-500 hover:text-accent-primary hover:bg-accent-primary/10 transition-colors"
                                            title="Ver explicação detalhada"
                                        >
                                            <Search size={14} />
                                        </button>
                                    )}
                                </div>
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
                            <div className="w-8 h-8 rounded-lg bg-accent-primary/10 border border-accent-primary/20 flex items-center justify-center text-accent-primary shrink-0 mt-1">
                                <Bot size={18} />
                            </div>
                            <div className="flex flex-col gap-2">
                                <div className="flex gap-1 h-6 items-center px-2">
                                    <span className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                    <span className="w-1.5 h-1.5 bg-accent-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-1.5 h-1.5 bg-accent-primary rounded-full animate-bounce"></span>
                                </div>
                                <span className="text-xs text-text-secondary font-medium px-1">Pensando...</span>
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

            <SourceModal
                source={selectedSource}
                isOpen={!!selectedSource}
                onClose={() => setSelectedSource(null)}
            />

            <ExplanationModal
                explanation={selectedExplanation}
                isOpen={showExplanation}
                onClose={() => {
                    setShowExplanation(false);
                    setSelectedExplanation(null);
                }}
            />
        </div>
    );
}
