import { Send, Paperclip } from "lucide-react";
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
        <div className="p-4 bg-gray-900/50 backdrop-blur-lg border-t border-white/10">
            <div className="max-w-4xl mx-auto relative flex items-end gap-2 bg-gray-800/80 rounded-xl border border-white/10 p-2 shadow-xl focus-within:border-blue-500/50 transition-colors">
                <button
                    className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                    title="Upload Document"
                    onClick={onOpenUpload}
                    disabled={isLoading}
                >
                    <Paperclip size={20} />
                </button>

                <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything..."
                    className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500 resize-none max-h-32 py-2 min-h-[44px]"
                    rows={1}
                    disabled={isLoading}
                />

                <button
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading}
                    className={cn(
                        "p-2 rounded-lg transition-all duration-200",
                        input.trim() && !isLoading
                            ? "bg-blue-600 text-white shadow-lg hover:bg-blue-500 hover:scale-105"
                            : "bg-gray-700 text-gray-500 cursor-not-allowed"
                    )}
                >
                    <Send size={20} />
                </button>
            </div>
            <div className="text-center mt-2 text-xs text-gray-600">
                AI may display inaccurate info, please double check responses.
            </div>
        </div>
    );
}
