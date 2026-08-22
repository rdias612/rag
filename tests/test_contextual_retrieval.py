"""
Testes unitários para o módulo de Contextual Retrieval (Task 2.1).
"""
import unittest
from unittest.mock import patch

from src.data.contextual_retrieval import (
    generate_chunk_context,
    contextualize_chunk,
    contextualize_document_chunks,
    check_contextual_retrieval_status
)


class TestContextualRetrieval(unittest.TestCase):
    
    def setUp(self):
        self.doc_text = (
            "Manual de Arquitetura RAG 2026. Este documento explica os conceitos de "
            "busca vetorial, busca híbrida e reranking para bases de conhecimento."
        )
        self.sample_chunk = {
            "content": "A busca híbrida combina pgvector com BM25 para maior recall.",
            "metadata": {
                "chunk_index": 0,
                "source": "manual.pdf",
                "chunk_type": "child"
            }
        }

    @patch("src.data.contextual_retrieval.generate_response")
    def test_generate_chunk_context_success(self, mock_llm):
        mock_llm.return_value = "Contexto: Seção sobre métodos de busca no manual de arquitetura."
        
        context = generate_chunk_context(self.doc_text, self.sample_chunk["content"])
        self.assertIn("Seção sobre métodos de busca", context)
        mock_llm.assert_called_once()

    @patch("src.data.contextual_retrieval.generate_response")
    def test_contextualize_chunk_metadata_and_prefix(self, mock_llm):
        mock_llm.return_value = "Documento sobre arquitetura RAG."
        
        enriched = contextualize_chunk(self.doc_text, self.sample_chunk)
        
        self.assertTrue(enriched["metadata"]["is_contextualized"])
        self.assertEqual(enriched["metadata"]["context_summary"], "Documento sobre arquitetura RAG.")
        self.assertEqual(enriched["metadata"]["original_content"], self.sample_chunk["content"])
        self.assertTrue(enriched["content"].startswith("[Contexto: Documento sobre arquitetura RAG.]"))

    @patch("src.data.contextual_retrieval.generate_response")
    def test_contextualize_document_chunks_skips_parent(self, mock_llm):
        mock_llm.return_value = "Contexto do chunk."
        
        parent_chunk = {
            "content": "Texto do chunk pai muito longo...",
            "metadata": {"chunk_type": "parent"}
        }
        child_chunk = {
            "content": "Texto do chunk filho.",
            "metadata": {"chunk_type": "child"}
        }
        
        results = contextualize_document_chunks(self.doc_text, [parent_chunk, child_chunk], enabled=True)
        
        self.assertEqual(len(results), 2)
        # O pai não deve ser contextualizado
        self.assertNotIn("is_contextualized", results[0]["metadata"])
        # O filho deve ser contextualizado
        self.assertTrue(results[1]["metadata"]["is_contextualized"])

    def test_status_check(self):
        status = check_contextual_retrieval_status()
        self.assertIn("enabled", status)
        self.assertIn("pattern", status)


if __name__ == "__main__":
    unittest.main()
