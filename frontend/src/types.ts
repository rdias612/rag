export interface RAGTimelineStep {
    id: string;
    title: string;
    description: string;
    timestamp?: number;
    icon: string;
    status: 'pending' | 'processing' | 'completed' | 'skipped';
    duration_ms?: number;
    metadata?: {
        [key: string]: any;
    };
}

export interface RAGExplanation {
    question: string;
    steps: RAGTimelineStep[];
    final_result: {
        chunks_used: number;
        total_chunks_found: number;
        total_time_ms: number;
    };
    generated_at: string;
}

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: number;
    sources?: Source[];
    debugInfo?: DebugInfo;
    explanation?: RAGExplanation;
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
