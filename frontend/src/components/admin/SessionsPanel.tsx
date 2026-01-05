import { useState, useEffect } from 'react';
import {
    MessageSquare,
    Trash2,
    Clock,
    Hash,
    RefreshCw,
    AlertCircle,
    ArrowLeft,
    User,
    Bot
} from 'lucide-react';
import { createLogger } from '../../logger';

const logger = createLogger('SessionsPanel');

interface Session {
    session_id: string;
    message_count: number;
    created_at: string;
    last_activity: string;
}

interface Message {
    role: string;
    content: string;
    timestamp: number;
}

interface SessionHistory {
    session_id: string;
    messages: Message[];
    created_at: string;
    message_count: number;
}

const API_URL = "http://localhost:5000/api";

export function SessionsPanel() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState<string | null>(null);
    const [selectedSession, setSelectedSession] = useState<string | null>(null);
    const [sessionHistory, setSessionHistory] = useState<SessionHistory | null>(null);
    const [loadingHistory, setLoadingHistory] = useState(false);

    const fetchSessions = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/chat/sessions`);
            const data = await res.json();
            setSessions(data.sessions || []);
        } catch (error) {
            logger.error('Failed to fetch sessions:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchSessionHistory = async (sessionId: string) => {
        setLoadingHistory(true);
        try {
            const res = await fetch(`${API_URL}/chat/sessions/${sessionId}`);
            if (res.ok) {
                const data = await res.json();
                setSessionHistory(data);
                setSelectedSession(sessionId);
            } else {
                alert('Erro ao carregar histórico da sessão');
            }
        } catch (error) {
            logger.error('Failed to fetch session history:', error);
            alert('Erro ao carregar histórico da sessão');
        } finally {
            setLoadingHistory(false);
        }
    };

    const handleBackToList = () => {
        setSelectedSession(null);
        setSessionHistory(null);
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const handleDelete = async (sessionId: string, event: React.MouseEvent) => {
        event.stopPropagation();
        if (!confirm('Tem certeza que deseja excluir esta sessão?')) return;

        setDeleting(sessionId);
        try {
            await fetch(`${API_URL}/chat/sessions/${sessionId}`, { method: 'DELETE' });
            setSessions(prev => prev.filter(s => s.session_id !== sessionId));
        } catch (error) {
            logger.error('Failed to delete session:', error);
            alert('Erro ao excluir sessão');
        } finally {
            setDeleting(null);
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const formatTimestamp = (timestamp: number) => {
        const date = new Date(timestamp * 1000);
        return date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    const getTimeSince = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 60) return `${diffMins}min atrás`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h atrás`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d atrás`;
    };

    // If viewing session history, render history view
    if (selectedSession && sessionHistory) {
        return (
            <div className="space-y-6">
                {/* History Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleBackToList}
                            className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface rounded-lg transition-colors"
                        >
                            <ArrowLeft size={20} />
                        </button>
                        <div>
                            <h2 className="text-xl font-semibold text-text-primary flex items-center gap-2">
                                <MessageSquare size={24} className="text-accent-primary" />
                                Histórico da Sessão
                            </h2>
                            <p className="text-sm text-text-secondary mt-1">
                                {sessionHistory.session_id.slice(0, 8)}... • {sessionHistory.message_count} mensagens
                            </p>
                        </div>
                    </div>
                    <span className="text-xs text-text-secondary">
                        Criada: {formatDate(sessionHistory.created_at)}
                    </span>
                </div>

                {/* Messages */}
                <div className="space-y-3">
                    {sessionHistory.messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-text-secondary">
                            <AlertCircle size={32} className="mb-2" />
                            <p>Nenhuma mensagem nesta sessão</p>
                        </div>
                    ) : (
                        sessionHistory.messages.map((message, index) => (
                            <div
                                key={index}
                                className={`glass rounded-xl p-4 ${message.role === 'user'
                                        ? 'border-l-4 border-accent-primary'
                                        : 'border-l-4 border-green-500'
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    <div className={`p-2 rounded-lg ${message.role === 'user'
                                            ? 'bg-accent-primary/10 text-accent-primary'
                                            : 'bg-green-500/10 text-green-500'
                                        }`}>
                                        {message.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-sm font-medium text-text-primary">
                                                {message.role === 'user' ? 'Usuário' : 'Assistente'}
                                            </span>
                                            <span className="text-xs text-text-secondary">
                                                {formatTimestamp(message.timestamp)}
                                            </span>
                                        </div>
                                        <div className="text-sm text-text-primary whitespace-pre-wrap break-words">
                                            {message.content}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        );
    }

    // Default: render sessions list
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-text-primary flex items-center gap-2">
                    <MessageSquare size={24} className="text-accent-primary" />
                    Sessões de Chat
                </h2>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-text-secondary">{sessions.length} sessões</span>
                    <button
                        onClick={fetchSessions}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface hover:bg-surface/80 text-text-primary rounded-lg transition-colors disabled:opacity-50 border border-border"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Sessions List */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw size={24} className="animate-spin text-text-secondary" />
                </div>
            ) : sessions.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-text-secondary">
                    <AlertCircle size={32} className="mb-2" />
                    <p>Nenhuma sessão ativa</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {sessions.map((session) => (
                        <div
                            key={session.session_id}
                            onClick={() => fetchSessionHistory(session.session_id)}
                            className="glass rounded-xl p-4 flex items-center justify-between glass-hover cursor-pointer"
                        >
                            <div className="flex-1">
                                <div className="flex items-center gap-3">
                                    <span className="text-xs font-mono text-text-secondary bg-surface px-2 py-0.5 rounded">
                                        {session.session_id.slice(0, 8)}...
                                    </span>
                                    <span className="flex items-center gap-1 text-sm text-text-primary">
                                        <Hash size={12} />
                                        {session.message_count} mensagens
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 mt-2 text-xs text-text-secondary">
                                    <span className="flex items-center gap-1">
                                        <Clock size={12} />
                                        Criada: {formatDate(session.created_at)}
                                    </span>
                                    <span className="text-text-secondary/60">•</span>
                                    <span>
                                        Última atividade: {getTimeSince(session.last_activity)}
                                    </span>
                                </div>
                            </div>

                            <button
                                onClick={(e) => handleDelete(session.session_id, e)}
                                disabled={deleting === session.session_id}
                                className="p-2 text-text-secondary hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
                            >
                                {deleting === session.session_id ? (
                                    <RefreshCw size={16} className="animate-spin" />
                                ) : (
                                    <Trash2 size={16} />
                                )}
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Loading overlay when fetching history */}
            {loadingHistory && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="glass rounded-xl p-6 flex flex-col items-center gap-3">
                        <RefreshCw size={32} className="animate-spin text-accent-primary" />
                        <p className="text-text-primary">Carregando histórico...</p>
                    </div>
                </div>
            )}
        </div>
    );
}
