import { Sliders, Zap, Scale, Target } from "lucide-react";
import { useState } from "react";
import { cn } from "../utils";

interface TemperatureSelectorProps {
    temperature: number | undefined;
    setTemperature: (temp: number | undefined) => void;
}

export function TemperatureSelector({ temperature, setTemperature }: TemperatureSelectorProps) {
    const [isAdvanced, setIsAdvanced] = useState(false);

    const presets = [
        { label: "Preciso", value: 0.25, icon: Target, description: "Focado e factual" },
        { label: "Equilibrado", value: 0.5, icon: Scale, description: "Neutro e coerente" },
        { label: "Criativo", value: 0.75, icon: Zap, description: "Variado e rico" },
    ];

    const handlePresetClick = (val: number) => {
        setTemperature(val === temperature ? undefined : val);
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-400">
                    <Sliders size={14} />
                    TEMPERATURA
                </div>
                <button
                    onClick={() => setIsAdvanced(!isAdvanced)}
                    className={cn(
                        "text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full transition-all",
                        isAdvanced
                            ? "bg-accent-primary/20 text-accent-primary border border-accent-primary/30"
                            : "text-text-secondary hover:text-text-primary"
                    )}
                >
                    {isAdvanced ? "Simples" : "Avançado"}
                </button>
            </div>

            {!isAdvanced ? (
                <div className="grid grid-cols-1 gap-2">
                    {presets.map((preset) => {
                        const Icon = preset.icon;
                        const isSelected = temperature === preset.value;
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
            ) : (
                <div className="space-y-3 p-3 rounded-xl bg-surface border border-border">
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-text-secondary">Valor Manual</span>
                        <span className="font-mono text-accent-primary font-bold">{temperature ?? "0.70 (Padrão)"}</span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.01"
                        value={temperature ?? 0.7}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        className="w-full h-1.5 bg-card rounded-lg appearance-none cursor-pointer accent-accent-primary"
                    />
                    <div className="flex justify-between text-[10px] text-text-secondary font-medium">
                        <span>Preciso (0.0)</span>
                        <span>Criativo (2.0)</span>
                    </div>
                    <div className="pt-1">
                        <input
                            type="number"
                            min="0"
                            max="2"
                            step="0.01"
                            placeholder="0.70"
                            value={temperature ?? ""}
                            onChange={(e) => {
                                const val = e.target.value === "" ? undefined : parseFloat(e.target.value);
                                setTemperature(val);
                            }}
                            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-xs text-text-primary focus:outline-none focus:border-accent-primary/50 transition-colors"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
