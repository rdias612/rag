import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import type { Message } from "../types";

interface ChatAreaProps {
    messages: Message[];
    isLoading: boolean;
    onSend: (msg: string) => void;
    onOpenUpload: () => void;
}

export function ChatArea({ messages, isLoading, onSend, onOpenUpload }: ChatAreaProps) {
    return (
        <div className="flex-1 flex flex-col">
            <MessageList messages={messages} isLoading={isLoading} />
            <MessageInput onSend={onSend} isLoading={isLoading} onOpenUpload={onOpenUpload} />
        </div>
    );
}
