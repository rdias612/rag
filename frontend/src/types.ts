export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: number;
    sources?: Source[];
}

export interface Source {
    filename: string;
    page?: number;
    content: string;
}

export interface Session {
    session_id: string;
    created_at: string;
    message_count: number;
    last_activity?: string;
}

export interface ChatState {
    messages: Message[];
    isLoading: boolean;
    currentSessionId: string | null;
}
