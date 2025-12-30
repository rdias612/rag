import { motion, AnimatePresence } from "framer-motion";
import { X, Search, Copy, Check, Clock, FileText, ChevronDown } from "lucide-react";
import { useState, useEffect } from 'react';
import type { RAGExplanation, RAGTimelineStep } from "../types";

interface ExplanationModalProps {
  explanation: RAGExplanation | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ExplanationModal({ explanation, isOpen, onClose }: ExplanationModalProps) {
  const [copied, setCopied] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // Fechar modal com ESC
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Copiar JSON
  const handleCopyJSON = async () => {
    if (!explanation) return;
    
    const jsonString = JSON.stringify(explanation, null, 2);
    await navigator.clipboard.writeText(jsonString);
    
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Toggle step expansion
  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  // Auto-expand steps with metadata
  useEffect(() => {
    if (explanation) {
      const newExpanded = new Set<string>();
      explanation.steps.forEach(step => {
        if (step.metadata && Object.keys(step.metadata).length > 0) {
          newExpanded.add(step.id);
        }
      });
      setExpandedSteps(newExpanded);
    }
  }, [explanation]);

  const getStepIcon = (icon: string) => {
    const icons: Record<string, any> = {
      'message-circle': FileText,
      'sparkles': Clock,
      'cpu': Clock,
      'search': Clock,
      'filter': Clock,
      'compress': Clock,
      'bot': Clock,
      'branch': Clock,
      'layers': Clock,
      'check-circle': Clock,
    };
    return icons[icon] || Clock;
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    return `${ms.toFixed(0)}ms`;
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  if (!explanation) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            {/* Modal Content */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-card border border-border rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl relative overflow-hidden"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-border bg-surface/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-accent-primary/10 text-accent-primary">
                    <Search size={20} />
                  </div>
                  <div>
                    <h3 className="font-medium text-text-primary">Como chegamos a esta resposta</h3>
                    <p className="text-xs text-text-secondary">
                      {explanation.final_result.chunks_used} chunks usados de {explanation.final_result.total_chunks_found} encontrados
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopyJSON}
                    className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface rounded-lg transition-colors border border-border"
                    title="Copiar JSON"
                  >
                    {copied ? <Check size={18} className="text-emerald-500" /> : <Copy size={18} />}
                  </button>
                  <button
                    onClick={onClose}
                    className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface rounded-lg transition-colors"
                    title="Fechar"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              {/* Body - Scrollable */}
              <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
                <div className="space-y-4">
                  {explanation.steps.map((step, idx) => (
                    <motion.div
                      key={step.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.1 }}
                      className="flex gap-3"
                    >
                      {/* Step indicator */}
                      <div className="flex flex-col items-center">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          step.status === 'completed' 
                            ? 'bg-emerald-500/20 text-emerald-500' 
                            : 'bg-surface text-text-secondary'
                        }`}>
                          {(() => {
                            const IconComponent = getStepIcon(step.icon);
                            return <IconComponent size={18} />;
                          })()}
                        </div>
                        {idx < explanation.steps.length - 1 && (
                          <div className="w-0.5 flex-1 bg-border min-h-[40px]" />
                        )}
                      </div>

                      {/* Step content */}
                      <div className="flex-1 pb-6 min-w-0">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-semibold text-text-primary text-sm">
                            {step.title}
                          </h4>
                          {step.duration_ms && (
                            <span className="text-xs text-text-secondary font-mono bg-surface px-2 py-1 rounded border border-border">
                              {formatDuration(step.duration_ms)}
                            </span>
                          )}
                        </div>
                        
                        <p className="text-sm text-text-secondary leading-relaxed mb-2">
                          {step.description}
                        </p>

                        {/* Metadata detalhada */}
                        {step.metadata && Object.keys(step.metadata).length > 0 && (
                          <div className="mt-2">
                            <button
                              onClick={() => toggleStep(step.id)}
                              className="flex items-center gap-2 text-xs text-accent-primary hover:text-accent-primary/80 transition-colors"
                            >
                              <ChevronDown 
                                size={14} 
                                className={`transition-transform ${expandedSteps.has(step.id) ? 'rotate-180' : ''}`} 
                              />
                              {expandedSteps.has(step.id) ? 'Ocultar detalhes' : 'Ver detalhes'}
                            </button>
                            
                            <AnimatePresence>
                              {expandedSteps.has(step.id) && (
                                <motion.div
                                  initial={{ opacity: 0, height: 0 }}
                                  animate={{ opacity: 1, height: 'auto' }}
                                  exit={{ opacity: 0, height: 0 }}
                                  className="mt-2"
                                >
                                  <div className="bg-surface rounded-lg border border-border p-3 space-y-2">
                                    {Object.entries(step.metadata).map(([key, value]) => {
                                      if (value === null || value === undefined) return null;
                                      
                                      // Format value based on type
                                      let displayValue: string;
                                      if (typeof value === 'number') {
                                        if (key.includes('score') || key.includes('similarity')) {
                                          displayValue = formatPercentage(value);
                                        } else {
                                          displayValue = value.toString();
                                        }
                                      } else if (typeof value === 'object' && value !== null) {
                                        displayValue = JSON.stringify(value);
                                      } else {
                                        displayValue = String(value);
                                      }
                                      
                                      // Truncate long values
                                      if (displayValue.length > 150) {
                                        displayValue = displayValue.substring(0, 150) + '...';
                                      }
                                      
                                      return (
                                        <div key={key} className="flex items-start gap-2 text-xs">
                                          <span className="text-text-secondary min-w-[120px] capitalize shrink-0">
                                            {key.replace(/_/g, ' ')}:
                                          </span>
                                          <span className="text-text-primary font-mono break-all">
                                            {displayValue}
                                          </span>
                                        </div>
                                      );
                                    })}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>

                {/* Summary */}
                <div className="mt-8 p-4 bg-accent-primary/10 rounded-xl border border-accent-primary/20">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-text-primary text-sm mb-1">
                        Tempo total
                      </h4>
                      <p className="text-xs text-text-secondary">
                        {formatDuration(explanation.final_result.total_time_ms)}
                      </p>
                    </div>
                    <div className="text-right">
                      <h4 className="font-semibold text-text-primary text-sm mb-1">
                        Eficiência
                      </h4>
                      <p className="text-xs text-text-secondary">
                        {((explanation.final_result.chunks_used / explanation.final_result.total_chunks_found) * 100).toFixed(0)}% dos chunks utilizados ({explanation.final_result.chunks_used} de {explanation.final_result.total_chunks_found})
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-border bg-surface/50 flex justify-between items-center">
                <span className="text-xs text-text-secondary">
                  Gerado em: {new Date(explanation.generated_at).toLocaleString('pt-BR')}
                </span>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-surface hover:bg-surface/80 text-text-primary rounded-lg text-sm font-medium transition-colors border border-border"
                >
                  Fechar
                </button>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
