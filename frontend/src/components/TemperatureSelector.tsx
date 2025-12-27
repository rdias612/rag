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
                            ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                            : "text-zinc-500 hover:text-zinc-300"
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
                                        ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400 shadow-sm shadow-indigo-500/5"
                                        : "bg-surface border-border text-zinc-400 hover:border-zinc-700 hover:text-zinc-300"
                                )}
                            >
                                <div className={cn(
                                    "p-1.5 rounded-lg transition-colors",
                                    isSelected ? "bg-indigo-500/20 text-indigo-400" : "bg-zinc-800 text-zinc-500 group-hover:text-zinc-400"
                                )}>
                                    <Icon size={16} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="text-xs font-bold leading-tight">{preset.label}</div>
                                    <div className="text-[10px] text-zinc-500 truncate">{preset.description}</div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            ) : (
                <div className="space-y-3 p-3 rounded-xl bg-surface border border-border">
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-zinc-400">Valor Manual</span>
                        <span className="font-mono text-indigo-400 font-bold">{temperature ?? "0.70 (Padrão)"}</span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.01"
                        value={temperature ?? 0.7}
                        onChange={(e) => setTemperature(parseFloat(e.target.value))}
                        className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                    <div className="flex justify-between text-[10px] text-zinc-500 font-medium">
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
                            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500/50 transition-colors"
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
