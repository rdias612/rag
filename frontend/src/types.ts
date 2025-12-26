export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: number;
    sources?: Source[];
    debugInfo?: DebugInfo;
    feedback?: 'good' | 'bad' | null;
}

export interface DebugInfo {
    embedding_time_ms?: number;
    search_time_ms?: number;
    rerank_time_ms?: number;
    compression_time_ms?: number;
    llm_time_ms?: number;
    total_time_ms?: number;
    initial_chunks_found?: number;
    chunks_after_rerank?: number;
    chunks_rejected?: number;
    hyde_applied?: boolean;
    hyde_document?: string;
    question_type?: string;
    config?: {
        enable_hyde?: boolean;
        enable_reranking?: boolean;
        enable_mmr?: boolean;
        enable_query_expansion?: boolean;
        use_hybrid_search?: boolean;
    };
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
