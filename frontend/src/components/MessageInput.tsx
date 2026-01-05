import { Send, Paperclip, Loader2 } from "lucide-react";
import { useState, useRef, type KeyboardEvent, type ChangeEvent } from "react";
import { cn } from "../utils";

interface MessageInputProps {
    onSend: (message: string) => void;
    isLoading: boolean;
    onOpenUpload: () => void;
}

export function MessageInput({ onSend, isLoading, onOpenUpload }: MessageInputProps) {
    const [input, setInput] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSend = () => {
        if (!input.trim() || isLoading) return;
        onSend(input);
        setInput("");
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        e.target.style.height = "auto";
        e.target.style.height = `${e.target.scrollHeight}px`;
    };

    return (
        <div className="fixed bottom-0 left-0 right-0 z-20 p-4 pb-6 md:pl-72 bg-gradient-to-t from-chat via-chat/80 to-transparent pointer-events-none">
            <div className="max-w-3xl mx-auto pointer-events-auto">
                <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-accent-primary/20 to-accent-primary/10 rounded-2xl blur opacity-30 group-hover:opacity-50 transition duration-500" />
                    <div className="relative flex items-end gap-2 bg-card/90 backdrop-blur-xl border border-border rounded-2xl p-2 shadow-2xl">
                        <button
                            className="p-3 text-text-secondary hover:text-text-primary transition-colors rounded-xl hover:bg-surface active:scale-95 transition-all"
                            title="Upload Document"
                            onClick={onOpenUpload}
                            disabled={isLoading}
                            type="button"
                        >
                            <Paperclip size={20} />
                        </button>

                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={handleChange}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask me anything..."
                            className="flex-1 bg-transparent border-none outline-none text-text-primary placeholder:text-text-secondary resize-none max-h-32 py-3 text-sm leading-relaxed"
                            rows={1}
                            disabled={isLoading}
                        />

                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            type="button"
                            className={cn(
                                "flex items-center justify-center h-10 w-10 rounded-xl transition-all duration-200 mb-1 mr-1",
                                input.trim() && !isLoading
                                    ? "bg-accent-primary text-white shadow-lg shadow-accent-primary/20 hover:bg-accent-hover hover:scale-105 active:scale-95"
                                    : "bg-surface text-text-secondary/40 cursor-not-allowed"
                            )}
                        >
                            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                        </button>
                    </div>
                </div>
                <div className="text-center mt-3 text-[10px] text-text-secondary font-medium">
                    AI generated content may be inaccurate.
                </div>
            </div>
        </div>
    );
}
