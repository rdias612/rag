"""
Módulo de Benchmark e Avaliação Empírica Offline (RAG Triad).

Executa baterias de testes em datasets anotados (Golden Datasets) para
mensurar com precisão matemática a qualidade do pipeline RAG:
1. Context Relevance: Quão relevantes foram os chunks pescados?
2. Groundedness / Faithfulness: A resposta gerada é fiel ao contexto sem alucinações?
3. Answer Relevancy: A resposta atende com clareza o que foi perguntado?
4. Latency & Token Efficiency: Tempo de resposta e consumo de tokens.
"""
import json
import time
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from src.core.rag.pipeline import RAGPipeline
from src.core.evaluation import calculate_faithfulness, calculate_answer_relevancy, calculate_context_precision
from src.core.logger import get_logger

logger = get_logger("core.benchmark")


@dataclass
class BenchmarkItemResult:
    """Resultado individual de um caso de teste."""
    test_id: str
    category: str
    question: str
    ground_truth_answer: str
    generated_answer: str
    chunks_count: int
    context_relevance: float
    faithfulness: float
    answer_relevancy: float
    keyword_recall: float
    overall_triad_score: float
    latency_seconds: float
    status: str = "success"
    error_message: Optional[str] = None


@dataclass
class BenchmarkReport:
    """Relatório consolidado da execução de benchmark."""
    timestamp: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    avg_context_relevance: float
    avg_faithfulness: float
    avg_answer_relevancy: float
    avg_keyword_recall: float
    avg_triad_score: float
    avg_latency_seconds: float
    scores_by_category: Dict[str, Dict[str, float]]
    configuration: Dict[str, Any]
    items: List[BenchmarkItemResult] = field(default_factory=list)


def calculate_keyword_recall(text: str, expected_keywords: List[str]) -> float:
    """Calcula a taxa de presença dos termos-chave esperados no texto."""
    if not expected_keywords:
        return 1.0
    text_lower = text.lower()
    found = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
    return round(found / len(expected_keywords), 3)


class BenchmarkEngine:
    """Motor de execução e geração de relatórios de benchmark."""

    def __init__(self, pipeline: Optional[RAGPipeline] = None):
        self.pipeline = pipeline or RAGPipeline()

    def load_dataset(self, dataset_path: str | Path) -> List[Dict[str, Any]]:
        """Carrega e valida o Golden Dataset JSON."""
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Golden dataset não encontrado em: {path.resolve()}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            raise ValueError("O Golden Dataset deve ser uma lista de objetos JSON.")
            
        logger.info("Carregados %d casos de teste do dataset %s", len(data), path.name)
        return data

    def run_benchmark(
        self,
        dataset_path: str | Path,
        pipeline_overrides: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> BenchmarkReport:
        """
        Executa a suíte completa de testes sobre o dataset.
        """
        dataset = self.load_dataset(dataset_path)
        pipeline_overrides = pipeline_overrides or {}
        
        logger.info("Iniciando Benchmark RAG Triad (%d testes)...", len(dataset))
        results: List[BenchmarkItemResult] = []
        
        for i, item in enumerate(dataset, 1):
            test_id = item.get("id", f"tc_{i:03d}")
            question = item.get("question", "")
            ground_truth = item.get("ground_truth_answer", "")
            expected_keywords = item.get("expected_keywords", [])
            category = item.get("category", "general")
            
            logger.info("[%d/%d] Executando Teste '%s' (%s): %s", i, len(dataset), test_id, category, question[:60])
            start_time = time.time()
            
            try:
                # Executar query no pipeline RAG
                query_kwargs = {
                    "question": question,
                    "request_id": f"benchmark_{test_id}",
                    "async_eval": False
                }
                query_kwargs.update(pipeline_overrides)
                
                response = self.pipeline.query(**query_kwargs)
                latency = round(time.time() - start_time, 3)
                
                answer = response.get("answer", "")
                sources = response.get("sources", [])
                
                # Montar contexto textual retornado para avaliação
                context_texts = [s.get("content", "") for s in sources]
                full_context = "\n\n".join(context_texts)
                
                # 1. Context Relevance
                context_precision = calculate_context_precision(question, sources)
                kw_recall_context = calculate_keyword_recall(full_context, expected_keywords)
                context_relevance = round((context_precision * 0.6 + kw_recall_context * 0.4), 3)
                
                # 2. Faithfulness
                faithfulness = calculate_faithfulness(answer, full_context) if full_context else 0.5
                
                # 3. Answer Relevancy
                answer_relevancy = calculate_answer_relevancy(question, answer)
                kw_recall_answer = calculate_keyword_recall(answer, expected_keywords)
                
                # Score consolidado da Tríade
                triad_score = round((context_relevance + faithfulness + answer_relevancy) / 3.0, 3)
                
                res = BenchmarkItemResult(
                    test_id=test_id,
                    category=category,
                    question=question,
                    ground_truth_answer=ground_truth,
                    generated_answer=answer,
                    chunks_count=len(sources),
                    context_relevance=context_relevance,
                    faithfulness=faithfulness,
                    answer_relevancy=answer_relevancy,
                    keyword_recall=kw_recall_answer,
                    overall_triad_score=triad_score,
                    latency_seconds=latency,
                    status="success"
                )
            except Exception as e:
                latency = round(time.time() - start_time, 3)
                logger.error("Erro no teste %s: %s", test_id, e)
                res = BenchmarkItemResult(
                    test_id=test_id,
                    category=category,
                    question=question,
                    ground_truth_answer=ground_truth,
                    generated_answer="",
                    chunks_count=0,
                    context_relevance=0.0,
                    faithfulness=0.0,
                    answer_relevancy=0.0,
                    keyword_recall=0.0,
                    overall_triad_score=0.0,
                    latency_seconds=latency,
                    status="failed",
                    error_message=str(e)
                )
                
            results.append(res)
            if progress_callback:
                progress_callback(i, len(dataset), res)

        return self._consolidate_report(results, pipeline_overrides)

    def _consolidate_report(
        self,
        results: List[BenchmarkItemResult],
        configuration: Dict[str, Any]
    ) -> BenchmarkReport:
        """Calcula agregações e métricas por categoria."""
        successful = [r for r in results if r.status == "success"]
        n_succ = len(successful) if successful else 1
        
        avg_ctx = round(sum(r.context_relevance for r in successful) / n_succ, 3)
        avg_faith = round(sum(r.faithfulness for r in successful) / n_succ, 3)
        avg_rel = round(sum(r.answer_relevancy for r in successful) / n_succ, 3)
        avg_kw = round(sum(r.keyword_recall for r in successful) / n_succ, 3)
        avg_triad = round(sum(r.overall_triad_score for r in successful) / n_succ, 3)
        avg_lat = round(sum(r.latency_seconds for r in results) / len(results), 3)
        
        # Agrupar por categoria
        cats: Dict[str, List[BenchmarkItemResult]] = {}
        for r in successful:
            cats.setdefault(r.category, []).append(r)
            
        scores_by_cat = {}
        for cat_name, cat_items in cats.items():
            count = len(cat_items)
            scores_by_cat[cat_name] = {
                "count": count,
                "avg_triad_score": round(sum(x.overall_triad_score for x in cat_items) / count, 3),
                "avg_faithfulness": round(sum(x.faithfulness for x in cat_items) / count, 3),
                "avg_answer_relevancy": round(sum(x.answer_relevancy for x in cat_items) / count, 3),
                "avg_latency": round(sum(x.latency_seconds for x in cat_items) / count, 3)
            }
            
        return BenchmarkReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=len(results),
            successful_tests=len(successful),
            failed_tests=len(results) - len(successful),
            avg_context_relevance=avg_ctx,
            avg_faithfulness=avg_faith,
            avg_answer_relevancy=avg_rel,
            avg_keyword_recall=avg_kw,
            avg_triad_score=avg_triad,
            avg_latency_seconds=avg_lat,
            scores_by_category=scores_by_cat,
            configuration=configuration,
            items=results
        )

    def generate_markdown_report(self, report: BenchmarkReport) -> str:
        """Gera um relatório formatado em Markdown com tabelas e gráficos ASCII."""
        md = []
        md.append("# 📊 Relatório de Benchmark: RAG Triad Evaluation\n")
        md.append(f"**Data da Execução:** {report.timestamp}  ")
        md.append(f"**Testes Executados:** {report.total_tests} (Sucessos: {report.successful_tests} | Falhas: {report.failed_tests})\n")
        
        md.append("## 🎯 Resumo das Métricas Globais (RAG Triad)\n")
        md.append("| Métrica | Pontuação Média | Status |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Context Relevance** | `{report.avg_context_relevance * 100:.1f}%` | {'🟢 Alto' if report.avg_context_relevance >= 0.7 else '🟡 Atenção'} |")
        md.append(f"| **Faithfulness (Fidelidade)** | `{report.avg_faithfulness * 100:.1f}%` | {'🟢 Confiável' if report.avg_faithfulness >= 0.8 else '🔴 Risco de Alucinação'} |")
        md.append(f"| **Answer Relevancy** | `{report.avg_answer_relevancy * 100:.1f}%` | {'🟢 Direto' if report.avg_answer_relevancy >= 0.75 else '🟡 Genérico'} |")
        md.append(f"| **Keyword Recall** | `{report.avg_keyword_recall * 100:.1f}%` | {'🟢 Abrangente' if report.avg_keyword_recall >= 0.6 else '🟡 Parcial'} |")
        md.append(f"| **Overall Triad Score** | **`{report.avg_triad_score * 100:.1f}%`** | {'🏆 Excelente' if report.avg_triad_score >= 0.8 else '📈 Bom'} |")
        md.append(f"| **Latência Média** | `{report.avg_latency_seconds:.2f}s` | {'⚡ Rápido' if report.avg_latency_seconds < 3.0 else '⏱️ Moderado'} |\n")
        
        md.append("## 📂 Desempenho por Categoria\n")
        md.append("| Categoria | Casos | Score Tríade | Fidelidade | Relevância | Latência Média |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for cat, scores in report.scores_by_category.items():
            md.append(f"| `{cat}` | {scores['count']} | `{scores['avg_triad_score']*100:.1f}%` | `{scores['avg_faithfulness']*100:.1f}%` | `{scores['avg_answer_relevancy']*100:.1f}%` | `{scores['avg_latency']:.2f}s` |")
        md.append("\n")
        
        md.append("## 📋 Detalhamento dos Casos de Teste\n")
        md.append("| ID | Categoria | Pergunta | Contexto | Fidelidade | Resposta | Score Final |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for item in report.items:
            q_short = item.question[:45] + "..." if len(item.question) > 45 else item.question
            md.append(f"| `{item.test_id}` | `{item.category}` | {q_short} | `{item.context_relevance*100:.0f}%` | `{item.faithfulness*100:.0f}%` | `{item.answer_relevancy*100:.0f}%` | **`{item.overall_triad_score*100:.0f}%`** |")
            
        return "\n".join(md)

    def save_report(self, report: BenchmarkReport, output_dir: str | Path = "docs/benchmarks") -> Dict[str, str]:
        """Salva relatórios em Markdown e JSON no diretório de saída."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        timestamp_clean = time.strftime("%Y%m%d_%H%M%S")
        md_file = out_path / f"benchmark_report_{timestamp_clean}.md"
        json_file = out_path / f"benchmark_report_{timestamp_clean}.json"
        
        # Salvar Markdown
        md_content = self.generate_markdown_report(report)
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        # Salvar JSON serializado
        report_dict = asdict(report)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        logger.info("Relatórios salvos com sucesso em:\n - %s\n - %s", md_file, json_file)
        return {
            "markdown": str(md_file),
            "json": str(json_file)
        }
