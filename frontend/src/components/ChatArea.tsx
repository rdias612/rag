import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import type { Message } from "../types";
import { cn } from "../utils";

interface ChatAreaProps {
    messages: Message[];
    isLoading: boolean;
    onSend: (msg: string) => void;
    onOpenUpload: () => void;
}

export function ChatArea({ messages, isLoading, onSend, onOpenUpload }: ChatAreaProps) {
    return (
        <div className={cn(
            "flex-1 flex flex-col h-screen transition-all duration-300 relative",
            // standard layout handles sidebar width (flex), this just needs to fill remaining space
        )}>
            {/* Header / Top bar could go here */}

            <MessageList messages={messages} isLoading={isLoading} />

            <MessageInput onSend={onSend} isLoading={isLoading} onOpenUpload={onOpenUpload} />
        </div>
    );
}
