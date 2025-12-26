import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import type { Message } from "../types";

interface ChatAreaProps {
    messages: Message[];
    isLoading: boolean;
    onSend: (msg: string) => void;
    onOpenUpload: () => void;
    onFeedback: (index: number, rating: number) => void;
}

export function ChatArea({ messages, isLoading, onSend, onOpenUpload, onFeedback }: ChatAreaProps) {
    return (
        <div className="flex-1 flex flex-col">
            <MessageList messages={messages} isLoading={isLoading} onFeedback={onFeedback} />
            <MessageInput onSend={onSend} isLoading={isLoading} onOpenUpload={onOpenUpload} />
        </div>
    );
}
