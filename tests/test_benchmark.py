"""
Testes unitários para o módulo de Benchmark (Task 2.2).
"""
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.benchmark import BenchmarkEngine, calculate_keyword_recall, BenchmarkReport


class TestBenchmark(unittest.TestCase):

    def setUp(self):
        self.engine = BenchmarkEngine(pipeline=MagicMock())
        self.golden_dataset_path = Path(__file__).resolve().parent / "data" / "golden_dataset.json"

    def test_golden_dataset_exists_and_valid(self):
        self.assertTrue(self.golden_dataset_path.exists())
        items = self.engine.load_dataset(self.golden_dataset_path)
        self.assertGreater(len(items), 0)
        first = items[0]
        self.assertIn("question", first)
        self.assertIn("ground_truth_answer", first)
        self.assertIn("expected_keywords", first)

    def test_calculate_keyword_recall(self):
        text = "A arquitetura RAG utiliza modelos LLM com busca vetorial."
        keywords = ["rag", "llm", "vetorial", "inexistente"]
        recall = calculate_keyword_recall(text, keywords)
        self.assertEqual(recall, 0.75)

    @patch("src.core.benchmark.calculate_faithfulness")
    @patch("src.core.benchmark.calculate_answer_relevancy")
    @patch("src.core.benchmark.calculate_context_precision")
    def test_run_benchmark_mocked(self, mock_prec, mock_rel, mock_faith):
        mock_prec.return_value = 0.9
        mock_faith.return_value = 0.85
        mock_rel.return_value = 0.95

        # Simular resposta do pipeline RAG
        self.engine.pipeline.query.return_value = {
            "answer": "RAG é uma arquitetura que combina busca com LLM.",
            "sources": [{"content": "RAG é uma arquitetura de recuperação com embeddings."}]
        }

        report = self.engine.run_benchmark(self.golden_dataset_path)
        self.assertIsInstance(report, BenchmarkReport)
        self.assertEqual(report.total_tests, len(self.engine.load_dataset(self.golden_dataset_path)))
        self.assertGreater(report.avg_triad_score, 0.0)

        # Testar geração de Markdown
        md = self.engine.generate_markdown_report(report)
        self.assertIn("# 📊 Relatório de Benchmark: RAG Triad Evaluation", md)
        self.assertIn("Context Relevance", md)


if __name__ == "__main__":
    unittest.main()
