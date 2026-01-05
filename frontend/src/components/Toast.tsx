import { X, AlertCircle, CheckCircle, Info } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect } from "react";

export type ToastType = 'error' | 'success' | 'info';

interface ToastProps {
    message: string;
    type: ToastType;
    isVisible: boolean;
    onClose: () => void;
    duration?: number; // Auto-dismiss duration in ms
}

export function Toast({ message, type, isVisible, onClose, duration = 5000 }: ToastProps) {
    const icons = {
        error: AlertCircle,
        success: CheckCircle,
        info: Info
    };

    const colors = {
        error: 'bg-red-500/90 border-red-400/50',
        success: 'bg-emerald-500/90 border-emerald-400/50',
        info: 'bg-blue-500/90 border-blue-400/50'
    };

    const Icon = icons[type];

    // Auto-dismiss
    useEffect(() => {
        if (isVisible && duration > 0) {
            const timer = setTimeout(() => {
                onClose();
            }, duration);

            return () => clearTimeout(timer);
        }
    }, [isVisible, duration, onClose]);

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0, y: -50, x: 50 }}
                    animate={{ opacity: 1, y: 0, x: 0 }}
                    exit={{ opacity: 0, y: -50, x: 50 }}
                    className={`fixed top-4 right-4 z-50 ${colors[type]} text-white px-4 py-3 rounded-lg shadow-xl border flex items-center gap-3 max-w-md backdrop-blur-sm`}
                >
                    <Icon size={20} className="shrink-0" />
                    <p className="flex-1 text-sm font-medium">{message}</p>
                    <button
                        onClick={onClose}
                        className="hover:bg-white/20 p-1 rounded transition-colors shrink-0"
                        aria-label="Close notification"
                    >
                        <X size={16} />
                    </button>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
