import { X, Upload, FileText, CheckCircle, AlertCircle } from "lucide-react";
import { useState, useRef, type ChangeEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../utils";

const UPLOAD_URL = "http://localhost:5000/api/ingest";

interface UploadModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function UploadModal({ isOpen, onClose }: UploadModalProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState("");
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            const validation = validateFile(droppedFile);

            if (!validation.valid) {
                setStatus('error');
                setMessage(validation.error || 'Arquivo inválido');
                setFile(null);
                return;
            }

            setFile(droppedFile);
            setStatus('idle');
            setMessage("");
        }
    };

    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    const VALID_EXTENSIONS = ['.pdf', '.txt', '.md', '.docx'];

    const validateFile = (file: File): { valid: boolean; error?: string } => {
        // Validar tamanho
        if (file.size > MAX_FILE_SIZE) {
            return {
                valid: false,
                error: `Arquivo muito grande! Tamanho máximo: ${(MAX_FILE_SIZE / 1024 / 1024).toFixed(0)}MB`
            };
        }

        // Validar extensão
        const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        if (!VALID_EXTENSIONS.includes(fileExt)) {
            return {
                valid: false,
                error: `Formato não suportado. Use: ${VALID_EXTENSIONS.join(', ')}`
            };
        }

        return { valid: true };
    };

    const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            const validation = validateFile(selectedFile);

            if (!validation.valid) {
                setStatus('error');
                setMessage(validation.error || 'Arquivo inválido');
                setFile(null);
                return;
            }

            setFile(selectedFile);
            setStatus('idle');
            setMessage("");
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setStatus('uploading');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(UPLOAD_URL, {
                method: 'POST',
                body: formData,
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            setStatus('success');
            setMessage('Document queued for processing!');
            setTimeout(() => {
                onClose();
                setFile(null);
                setStatus('idle');
            }, 2000);

        } catch (error) {
            console.error(error);
            setStatus('error');
            setMessage(error instanceof Error ? error.message : 'Upload failed');
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.5 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black z-[60]"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="fixed inset-0 flex items-center justify-center z-[70] p-4 pointer-events-none"
                    >
                        <div className="bg-gray-900 border border-white/10 rounded-2xl w-full max-w-md p-6 shadow-2xl pointer-events-auto">
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-xl font-semibold text-white">Upload Document</h2>
                                <button
                                    onClick={onClose}
                                    className="p-1 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            <div
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                                onClick={() => fileInputRef.current?.click()}
                                className={cn(
                                    "border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all gap-4 text-center",
                                    isDragging
                                        ? "border-blue-500 bg-blue-500/10"
                                        : "border-gray-700 hover:border-gray-500 hover:bg-white/5",
                                    status === 'error' && "border-red-500/50 bg-red-900/10",
                                    status === 'success' && "border-emerald-500/50 bg-emerald-900/10"
                                )}
                            >
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    onChange={handleFileSelect}
                                    accept=".pdf,.txt,.md,.docx"
                                />

                                {status === 'success' ? (
                                    <CheckCircle size={48} className="text-emerald-500" />
                                ) : status === 'error' ? (
                                    <AlertCircle size={48} className="text-red-500" />
                                ) : file ? (
                                    <FileText size={48} className="text-blue-400" />
                                ) : (
                                    <Upload size={48} className="text-gray-500" />
                                )}

                                <div>
                                    <p className="font-medium text-white mb-1">
                                        {file ? file.name : "Click to upload or drag and drop"}
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        {status === 'success' ? message : status === 'error' ? message : "PDF, TXT, MD, DOCX (Max 10MB)"}
                                    </p>
                                </div>
                            </div>

                            <div className="mt-6 flex justify-end gap-3">
                                <button
                                    onClick={onClose}
                                    className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleUpload}
                                    disabled={!file || status === 'uploading' || status === 'success'}
                                    className={cn(
                                        "px-4 py-2 bg-blue-600 text-white rounded-lg font-medium transition-all",
                                        (!file || status === 'uploading') && "opacity-50 cursor-not-allowed",
                                        status === 'success' && "bg-emerald-600"
                                    )}
                                >
                                    {status === 'uploading' ? 'Uploading...' : status === 'success' ? 'Done' : 'Upload'}
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
