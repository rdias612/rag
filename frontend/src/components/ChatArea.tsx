import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import type { Message } from "../types";
import { cn } from "../utils";

interface ChatAreaProps {
    messages: Message[];
    isLoading: boolean;
    onSend: (msg: string) => void;
    onOpenUpload: () => void;
    collections: string[];
    selectedCollection: string | null;
    onSelectCollection: (value: string | null) => void;
}

export function ChatArea({ messages, isLoading, onSend, onOpenUpload, collections, selectedCollection, onSelectCollection }: ChatAreaProps) {
    return (
        <div className={cn(
            "flex-1 flex flex-col h-screen transition-all duration-300 relative",
            // standard layout handles sidebar width (flex), this just needs to fill remaining space
        )}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-gray-900/40 backdrop-blur-md">
                <div className="text-sm text-gray-400">Selecione o contexto</div>
                <select
                    className="bg-gray-800 text-white text-sm px-3 py-2 rounded-lg border border-white/10 focus:border-blue-500 focus:outline-none"
                    value={selectedCollection || ""}
                    onChange={(e) => onSelectCollection(e.target.value || null)}
                >
                    <option value="">Todas as coleções</option>
                    {collections.map((c) => (
                        <option key={c} value={c}>{c}</option>
                    ))}
                </select>
            </div>

            <MessageList messages={messages} isLoading={isLoading} />

            <MessageInput onSend={onSend} isLoading={isLoading} onOpenUpload={onOpenUpload} />
        </div>
    );
}
