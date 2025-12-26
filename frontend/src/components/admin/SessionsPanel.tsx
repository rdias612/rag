import { useState, useEffect } from 'react';
import {
    MessageSquare,
    Trash2,
    Clock,
    Hash,
    RefreshCw,
    AlertCircle
} from 'lucide-react';

interface Session {
    session_id: string;
    message_count: number;
    created_at: string;
    last_activity: string;
}

const API_URL = "http://localhost:5000/api";

export function SessionsPanel() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [loading, setLoading] = useState(true);
    const [deleting, setDeleting] = useState<string | null>(null);

    const fetchSessions = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/chat/sessions`);
            const data = await res.json();
            setSessions(data.sessions || []);
        } catch (error) {
            console.error('Failed to fetch sessions:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const handleDelete = async (sessionId: string) => {
        if (!confirm('Tem certeza que deseja excluir esta sessão?')) return;

        setDeleting(sessionId);
        try {
            await fetch(`${API_URL}/chat/sessions/${sessionId}`, { method: 'DELETE' });
            setSessions(prev => prev.filter(s => s.session_id !== sessionId));
        } catch (error) {
            console.error('Failed to delete session:', error);
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

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                    <MessageSquare size={24} className="text-indigo-400" />
                    Sessões de Chat
                </h2>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-zinc-400">{sessions.length} sessões</span>
                    <button
                        onClick={fetchSessions}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors disabled:opacity-50"
                    >
                        <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
            </div>

            {/* Sessions List */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <RefreshCw size={24} className="animate-spin text-zinc-500" />
                </div>
            ) : sessions.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
                    <AlertCircle size={32} className="mb-2" />
                    <p>Nenhuma sessão ativa</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {sessions.map((session) => (
                        <div
                            key={session.session_id}
                            className="bg-zinc-900/60 backdrop-blur-xl border border-white/5 rounded-xl p-4 flex items-center justify-between hover:border-white/10 transition-colors"
                        >
                            <div className="flex-1">
                                <div className="flex items-center gap-3">
                                    <span className="text-xs font-mono text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded">
                                        {session.session_id.slice(0, 8)}...
                                    </span>
                                    <span className="flex items-center gap-1 text-sm text-zinc-300">
                                        <Hash size={12} />
                                        {session.message_count} mensagens
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                                    <span className="flex items-center gap-1">
                                        <Clock size={12} />
                                        Criada: {formatDate(session.created_at)}
                                    </span>
                                    <span className="text-zinc-600">•</span>
                                    <span>
                                        Última atividade: {getTimeSince(session.last_activity)}
                                    </span>
                                </div>
                            </div>

                            <button
                                onClick={() => handleDelete(session.session_id)}
                                disabled={deleting === session.session_id}
                                className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors disabled:opacity-50"
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
        </div>
    );
}
