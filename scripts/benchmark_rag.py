#!/usr/bin/env python
"""
Script CLI para execução da Suíte de Benchmark do Sistema RAG (RAG Triad).

Uso:
    python scripts/benchmark_rag.py --dataset tests/data/golden_dataset.json
    python scripts/benchmark_rag.py --top-k 5 --hybrid --rerank
"""
import sys
import argparse
from pathlib import Path

# Adicionar raiz do projeto ao path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.benchmark import BenchmarkEngine
from src.core.logger import get_logger

logger = get_logger("scripts.benchmark_rag")


def main():
    parser = argparse.ArgumentParser(
        description="Executa avaliação empírica do pipeline RAG utilizando o padrão RAG Triad."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(project_root / "tests" / "data" / "golden_dataset.json"),
        help="Caminho para o arquivo JSON contendo o Golden Dataset anotado."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Número de documentos/chunks a recuperar por query."
    )
    parser.add_argument(
        "--hybrid",
        action="store_true",
        default=True,
        help="Ativar busca híbrida (Dense Vector + BM25/FTS)."
    )
    parser.add_argument(
        "--no-hybrid",
        dest="hybrid",
        action="store_false",
        help="Desativar busca híbrida (usar apenas busca vetorial pura)."
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        default=False,
        help="Ativar etapa de re-ranking (Cross-Encoder / LLM Reranker)."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(project_root / "docs" / "benchmarks"),
        help="Diretório para persistência dos relatórios (Markdown e JSON)."
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 INICIANDO SUÍTE DE BENCHMARK RAG TRIAD")
    print("="*70)
    print(f"📁 Dataset:    {args.dataset}")
    print(f"🔍 Top-K:      {args.top_k}")
    print(f"⚡ Híbrido:    {args.hybrid}")
    print(f"🎯 Rerank:     {args.rerank}")
    print(f"💾 Saída:      {args.output_dir}")
    print("="*70 + "\n")

    engine = BenchmarkEngine()
    
    pipeline_overrides = {
        "top_k": args.top_k,
        "use_hybrid": args.hybrid,
        "enable_reranking": args.rerank
    }

    try:
        report = engine.run_benchmark(
            dataset_path=args.dataset,
            pipeline_overrides=pipeline_overrides
        )
        
        saved_paths = engine.save_report(report, output_dir=args.output_dir)
        
        print("\n" + "="*70)
        print("🏆 RESULTADO FINAL DO BENCHMARK")
        print("="*70)
        print(f"Total de Testes:       {report.total_tests}")
        print(f"Sucessos:              {report.successful_tests}")
        print(f"Falhas:                {report.failed_tests}")
        print(f"Context Relevance:     {report.avg_context_relevance * 100:.1f}%")
        print(f"Faithfulness:          {report.avg_faithfulness * 100:.1f}%")
        print(f"Answer Relevancy:      {report.avg_answer_relevancy * 100:.1f}%")
        print(f"Keyword Recall:        {report.avg_keyword_recall * 100:.1f}%")
        print(f"⭐ OVERALL TRIAD SCORE: {report.avg_triad_score * 100:.1f}%")
        print(f"⏱️ Latência Média:      {report.avg_latency_seconds:.2f}s")
        print("="*70)
        print(f"📄 Relatório Markdown: {saved_paths['markdown']}")
        print(f"📊 Relatório JSON:     {saved_paths['json']}")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error("Falha na execução do benchmark: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
