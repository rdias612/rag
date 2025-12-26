import { X, AlertTriangle, Info } from 'lucide-react';

interface ConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    variant?: 'danger' | 'warning' | 'info';
    loading?: boolean;
}

export function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirmar',
    cancelText = 'Cancelar',
    variant = 'warning',
    loading = false
}: ConfirmModalProps) {
    if (!isOpen) return null;

    const variantStyles = {
        danger: {
            icon: <AlertTriangle size={24} className="text-red-400" />,
            iconBg: 'bg-red-500/10',
            buttonBg: 'bg-red-600 hover:bg-red-500',
        },
        warning: {
            icon: <AlertTriangle size={24} className="text-amber-400" />,
            iconBg: 'bg-amber-500/10',
            buttonBg: 'bg-amber-600 hover:bg-amber-500',
        },
        info: {
            icon: <Info size={24} className="text-indigo-400" />,
            iconBg: 'bg-indigo-500/10',
            buttonBg: 'bg-indigo-600 hover:bg-indigo-500',
        },
    };

    const styles = variantStyles[variant];

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-zinc-900 border border-white/10 rounded-2xl shadow-2xl max-w-md w-full mx-4 animate-fade-in">
                {/* Close button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-1 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                >
                    <X size={18} />
                </button>

                {/* Content */}
                <div className="p-6">
                    {/* Icon */}
                    <div className={`w-12 h-12 rounded-xl ${styles.iconBg} flex items-center justify-center mb-4`}>
                        {styles.icon}
                    </div>

                    {/* Title */}
                    <h3 className="text-lg font-semibold text-white mb-2">
                        {title}
                    </h3>

                    {/* Message */}
                    <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                        {message}
                    </p>

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            disabled={loading}
                            className="flex-1 px-4 py-2.5 text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl transition-colors disabled:opacity-50"
                        >
                            {cancelText}
                        </button>
                        <button
                            onClick={onConfirm}
                            disabled={loading}
                            className={`flex-1 px-4 py-2.5 text-sm font-medium text-white rounded-xl transition-colors disabled:opacity-50 ${styles.buttonBg}`}
                        >
                            {loading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    Processando...
                                </span>
                            ) : (
                                confirmText
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
