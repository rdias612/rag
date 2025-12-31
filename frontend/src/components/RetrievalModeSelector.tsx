import { Search, BookOpen, Target, Info } from "lucide-react";
import { useState } from "react";
import { cn } from "../utils";

type RetrievalMode = "auto" | "hierarchical" | "sentence";

interface RetrievalModeSelectorProps {
    mode: RetrievalMode | undefined;
    setMode: (mode: RetrievalMode | undefined) => void;
}

export function RetrievalModeSelector({ mode, setMode }: RetrievalModeSelectorProps) {
    const [showInfo, setShowInfo] = useState(false);

    const presets = [
        { 
            label: "Automático", 
            value: "auto" as RetrievalMode, 
            icon: Search, 
            description: "Sistema escolhe o melhor modo",
            explanation: "Analisa a pergunta e decide automaticamente se busca precisa ou explicação detalhada. Ideal para a maioria dos casos."
        },
        { 
            label: "Explicação", 
            value: "hierarchical" as RetrievalMode, 
            icon: BookOpen, 
            description: "Contexto mais detalhado",
            explanation: "Retorna explicações mais longas e contextuais. Ideal para perguntas do tipo 'como funciona', 'por que', 'explique'."
        },
        { 
            label: "Precisão", 
            value: "sentence" as RetrievalMode, 
            icon: Target, 
            description: "Resposta direta e específica",
            explanation: "Retorna respostas mais diretas e focadas. Ideal para perguntas curtas e específicas como 'qual é', 'quanto custa'."
        },
    ];

    const handlePresetClick = (val: RetrievalMode) => {
        setMode(val === mode ? undefined : val);
    };

    return (
        <div className="space-y-4 relative">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400">
                    <Search size={14} />
                    MODO DE BUSCA
                </div>
                <button
                    onClick={() => setShowInfo(!showInfo)}
                    className={cn(
                        "text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full transition-all",
                        showInfo
                            ? "bg-accent-primary/20 text-accent-primary border border-accent-primary/30"
                            : "text-text-secondary hover:text-text-primary"
                    )}
                >
                    <Info size={12} />
                </button>
            </div>

            {/* Popover Explicativo */}
            {showInfo && (
                <div className="absolute z-50 w-80 top-8 right-0 bg-surface border border-border rounded-xl shadow-lg p-4 animate-in fade-in zoom-in-95 duration-200">
                    <h4 className="text-sm font-bold text-text-primary mb-3">Como funciona?</h4>
                    <div className="space-y-3">
                        {presets.map((preset) => {
                            const Icon = preset.icon;
                            return (
                                <div key={preset.value} className="flex gap-3">
                                    <div className="flex-shrink-0 p-1.5 rounded-lg bg-card">
                                        <Icon size={14} className="text-text-secondary" />
                                    </div>
                                    <div>
                                        <div className="text-xs font-semibold text-text-primary">{preset.label}</div>
                                        <div className="text-[10px] text-text-secondary leading-relaxed">
                                            {preset.explanation}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Botões de Seleção */}
            <div className="grid grid-cols-1 gap-2">
                {presets.map((preset) => {
                    const Icon = preset.icon;
                    const isSelected = mode === preset.value;
                    return (
                        <button
                            key={preset.value}
                            onClick={() => handlePresetClick(preset.value)}
                            className={cn(
                                "flex items-center gap-3 p-2.5 rounded-xl border transition-all text-left group",
                                isSelected
                                    ? "bg-accent-primary/10 border-accent-primary/30 text-accent-primary shadow-sm shadow-accent-primary/5"
                                    : "bg-surface border-border text-text-secondary hover:border-text-primary hover:text-text-primary"
                            )}
                        >
                            <div className={cn(
                                "p-1.5 rounded-lg transition-colors",
                                isSelected ? "bg-accent-primary/20 text-accent-primary" : "bg-card text-text-secondary group-hover:text-text-primary"
                            )}>
                                <Icon size={16} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="text-xs font-bold leading-tight">{preset.label}</div>
                                <div className="text-[10px] text-text-secondary truncate">{preset.description}</div>
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
