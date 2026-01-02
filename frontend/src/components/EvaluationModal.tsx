import React, { useState } from 'react';
import { X, Award, CheckCircle, XCircle } from 'lucide-react';
import { API_URL } from '../api';
import { useToast } from '../hooks/useToast';
import { createLogger } from '../logger';

const logger = createLogger('EvaluationModal');

interface EvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  question: string;
  answer: string;
  context: string;
  sources: any[];
}

interface EvaluationData {
  question: string;
  answer: string;
  context: string;
  chunks: any[];
}

export const EvaluationModal: React.FC<EvaluationModalProps> = ({
  isOpen,
  onClose,
  question,
  answer,
  context,
  sources
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const { showToast } = useToast();

  if (!isOpen) return null;

  const handleEvaluate = async () => {
    try {
      setLoading(true);
      setResult(null);

      const response = await fetch(`${API_URL}/metrics/quality/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          answer,
          context,
          chunks: sources
        })
      });

      if (!response.ok) throw new Error('Failed to evaluate');

      const data = await response.json();
      setResult(data);
      showToast('Avaliação realizada com sucesso!', 'success');
    } catch (error) {
      logger.error('Error evaluating:', error);
      showToast('Erro ao realizar avaliação', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score: number): string => {
    return `${(score * 100).toFixed(1)}%`;
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getScoreColorClass = (score: number): string => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-border">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Award className="w-5 h-5 text-accent-primary" />
            <h2 className="text-lg font-semibold">Avaliar Qualidade da Resposta</h2>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-surface transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Pergunta */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Pergunta
            </label>
            <div className="bg-surface rounded-lg p-3 text-sm">
              {question}
            </div>
          </div>

          {/* Resposta */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Resposta
            </label>
            <div className="bg-surface rounded-lg p-3 text-sm whitespace-pre-wrap">
              {answer}
            </div>
          </div>

          {/* Resultado da Avaliação */}
          {result && (
            <div className="border border-border rounded-lg p-4 bg-surface/50">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Award className="w-5 h-5 text-accent-primary" />
                Resultado da Avaliação
              </h3>

              {/* Score Geral */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Score Geral</span>
                  <span className={`text-2xl font-bold ${getScoreColorClass(result.overall_score)}`}>
                    {formatScore(result.overall_score)}
                  </span>
                </div>
                <div className="w-full bg-surface rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${getScoreColor(result.overall_score)}`}
                    style={{ width: `${result.overall_score * 100}%` }}
                  />
                </div>
              </div>

              {/* Métricas Individuais */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {/* Fidelidade */}
                <div className="bg-card rounded-lg p-3 border border-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-text-secondary">Fidelidade</span>
                    {result.faithfulness >= 0.8 ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : result.faithfulness >= 0.6 ? (
                      <XCircle className="w-4 h-4 text-yellow-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                  <div className={`text-xl font-bold ${getScoreColorClass(result.faithfulness)}`}>
                    {formatScore(result.faithfulness)}
                  </div>
                  <div className="w-full bg-surface rounded-full h-2 mt-2 overflow-hidden">
                    <div
                      className={`h-full ${getScoreColor(result.faithfulness)}`}
                      style={{ width: `${result.faithfulness * 100}%` }}
                    />
                  </div>
                </div>

                {/* Relevância */}
                <div className="bg-card rounded-lg p-3 border border-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-text-secondary">Relevância</span>
                    {result.answer_relevancy >= 0.8 ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : result.answer_relevancy >= 0.6 ? (
                      <XCircle className="w-4 h-4 text-yellow-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                  <div className={`text-xl font-bold ${getScoreColorClass(result.answer_relevancy)}`}>
                    {formatScore(result.answer_relevancy)}
                  </div>
                  <div className="w-full bg-surface rounded-full h-2 mt-2 overflow-hidden">
                    <div
                      className={`h-full ${getScoreColor(result.answer_relevancy)}`}
                      style={{ width: `${result.answer_relevancy * 100}%` }}
                    />
                  </div>
                </div>

                {/* Precisão do Contexto */}
                <div className="bg-card rounded-lg p-3 border border-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-text-secondary">Precisão do Contexto</span>
                    {result.context_precision >= 0.8 ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : result.context_precision >= 0.6 ? (
                      <XCircle className="w-4 h-4 text-yellow-500" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-500" />
                    )}
                  </div>
                  <div className={`text-xl font-bold ${getScoreColorClass(result.context_precision)}`}>
                    {formatScore(result.context_precision)}
                  </div>
                  <div className="w-full bg-surface rounded-full h-2 mt-2 overflow-hidden">
                    <div
                      className={`h-full ${getScoreColor(result.context_precision)}`}
                      style={{ width: `${result.context_precision * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Resumo da Avaliação */}
              {result.evaluation_summary && (
                <div className="bg-card rounded-lg p-3 border border-border">
                  <span className="text-sm font-medium text-text-secondary block mb-2">
                    Resumo da Avaliação
                  </span>
                  <p className="text-sm whitespace-pre-wrap">{result.evaluation_summary}</p>
                </div>
              )}

              {/* Sugestões */}
              {result.suggestions && result.suggestions.length > 0 && (
                <div className="mt-4 bg-card rounded-lg p-3 border border-border">
                  <span className="text-sm font-medium text-text-secondary block mb-2">
                    Sugestões de Melhoria
                  </span>
                  <ul className="text-sm space-y-1 list-disc list-inside">
                    {result.suggestions.map((suggestion: string, idx: number) => (
                      <li key={idx}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Botão de Ação */}
          {!result && (
            <button
              onClick={handleEvaluate}
              disabled={loading}
              className="w-full bg-accent-primary hover:bg-accent-primary/90 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Avaliando...</span>
                </>
              ) : (
                <>
                  <Award className="w-5 h-5" />
                  <span>Avaliar Resposta</span>
                </>
              )}
            </button>
          )}

          {result && (
            <button
              onClick={handleEvaluate}
              disabled={loading}
              className="w-full bg-surface hover:bg-surface/80 text-text-primary font-medium py-3 px-4 rounded-lg border border-border transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-text-primary/30 border-t-text-primary rounded-full animate-spin" />
                  <span>Reavaliando...</span>
                </>
              ) : (
                <>
                  <Award className="w-5 h-5" />
                  <span>Reavaliar</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default EvaluationModal;
