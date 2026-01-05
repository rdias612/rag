"""
Testes unitários para Adaptive Retrieval.

Cobrem:
- Cálculo de complexidade
- Validação de limites
- Ajuste de top_k e min_similarity
- Logging configurável
"""
import pytest
from src.core.adaptive_retrieval import (
    get_adaptive_params,
    _calculate_complexity,
    _adjust_retrieval_params
)
from src.config import (
    TOP_K_RESULTS,
    MIN_SIMILARITY_THRESHOLD,
    MAX_TOP_K_ADAPTIVE,
    MIN_TOP_K_ADAPTIVE,
    MAX_MIN_SIMILARITY_ADAPTIVE,
    MIN_MIN_SIMILARITY_ADAPTIVE
)


class TestCalculateComplexity:
    """Testes para cálculo de complexidade de queries."""
    
    def test_simple_query_short(self):
        """Query simples e curta deve ter baixa complexidade."""
        query = "O que é RAG?"
        result = _calculate_complexity(query)
        assert 0 <= result <= 3
    
    def test_simple_query_direct(self):
        """Query direta e simples."""
        query = "Como instalar o sistema?"
        result = _calculate_complexity(query)
        assert 0 <= result <= 3
    
    def test_medium_query_multiple_words(self):
        """Query com múltiplas palavras e contexto."""
        query = "Como funciona o sistema de busca vetorial e qual a importância do threshold?"
        result = _calculate_complexity(query)
        assert 4 <= result <= 6
    
    def test_medium_question_terms(self):
        """Query com termos de pergunta."""
        query = "Por que preciso configurar o MIN_SIMILARITY_THRESHOLD e quais os valores recomendados?"
        result = _calculate_complexity(query)
        assert 4 <= result <= 6
    
    def test_complex_query_multiple_sentences(self):
        """Query complexa com múltiplas frases."""
        query = "Quero entender como configurar o sistema para lidar com documentos PDF e DOCX, e quais são os melhores parâmetros para embeddings e re-ranking em um ambiente de produção com alto volume de queries."
        result = _calculate_complexity(query)
        assert 7 <= result <= 10
    
    def test_complex_query_technical(self):
        """Query técnica e longa."""
        query = "Explique como funciona o pipeline RAG completo incluindo Query Expansion, HyDE, Re-ranking com Cross-Encoder, e como otimizar cada componente para performance em produção com milhares de documentos."
        result = _calculate_complexity(query)
        assert 7 <= result <= 10
    
    def test_complexity_max_score(self):
        """Query muito longa deve ter score máximo."""
        query = "P" * 200  # Muito longa
        result = _calculate_complexity(query)
        assert result <= 10
    
    def test_complexity_with_question_words(self):
        """Question words devem aumentar complexidade."""
        simple = "Configuração sistema"
        with_questions = "Como e por que devo fazer a configuração do sistema e quais são as consequências?"
        
        result_simple = _calculate_complexity(simple)
        result_questions = _calculate_complexity(with_questions)
        
        assert result_questions > result_simple
    
    def test_empty_query(self):
        """Query vazia deve ter complexidade 0."""
        result = _calculate_complexity("")
        assert result == 0
    
    def test_whitespace_query(self):
        """Query apenas com espaços deve ter complexidade 0."""
        result = _calculate_complexity("   ")
        assert result == 0


class TestAdjustRetrievalParams:
    """Testes para ajuste de parâmetros de recuperação."""
    
    def test_simple_query_increases_top_k(self):
        """Query simples deve aumentar top_k."""
        result = _adjust_retrieval_params(
            complexity_score=2,
            base_top_k=5,
            base_min_similarity=0.7
        )
        assert result["top_k"] > 5
        assert result["adjustment_reason"] == "Simple query - expanding search scope"
    
    def test_simple_query_decreases_min_similarity(self):
        """Query simples deve diminuir min_similarity."""
        result = _adjust_retrieval_params(
            complexity_score=2,
            base_top_k=5,
            base_min_similarity=0.7
        )
        assert result["min_similarity"] < 0.7
    
    def test_medium_query_uses_defaults(self):
        """Query média deve usar valores padrão."""
        result = _adjust_retrieval_params(
            complexity_score=5,
            base_top_k=5,
            base_min_similarity=0.7
        )
        assert result["top_k"] == 5
        assert result["min_similarity"] == 0.7
        assert result["adjustment_reason"] == "Medium complexity - using defaults"
    
    def test_complex_query_decreases_top_k(self):
        """Query complexa deve diminuir top_k."""
        result = _adjust_retrieval_params(
            complexity_score=8,
            base_top_k=10,
            base_min_similarity=0.5
        )
        assert result["top_k"] < 10
        assert result["adjustment_reason"] == "Complex query - focusing on most relevant"
    
    def test_complex_query_increases_min_similarity(self):
        """Query complexa deve aumentar min_similarity."""
        result = _adjust_retrieval_params(
            complexity_score=8,
            base_top_k=10,
            base_min_similarity=0.5
        )
        assert result["min_similarity"] > 0.5
    
    def test_very_simple_extreme_adjustment(self):
        """Query muito simples (0-1) deve ter ajuste extremo."""
        result = _adjust_retrieval_params(
            complexity_score=1,
            base_top_k=5,
            base_min_similarity=0.7
        )
        # top_k deve aumentar significativamente
        assert result["top_k"] >= 8
    
    def test_very_complex_extreme_adjustment(self):
        """Query muito complexa (9-10) deve ter ajuste extremo."""
        result = _adjust_retrieval_params(
            complexity_score=9,
            base_top_k=10,
            base_min_similarity=0.5
        )
        # top_k deve diminuir significativamente
        assert result["top_k"] <= 7
        # min_similarity deve aumentar significativamente
        assert result["min_similarity"] >= 0.7
    
    def test_adjustment_respects_max_top_k(self):
        """Ajuste deve respeitar MAX_TOP_K_ADAPTIVE."""
        result = _adjust_retrieval_params(
            complexity_score=0,
            base_top_k=5,
            base_min_similarity=0.7
        )
        assert result["top_k"] <= MAX_TOP_K_ADAPTIVE
    
    def test_adjustment_respects_min_top_k(self):
        """Ajuste deve respeitar MIN_TOP_K_ADAPTIVE."""
        result = _adjust_retrieval_params(
            complexity_score=10,
            base_top_k=10,
            base_min_similarity=0.3
        )
        assert result["top_k"] >= MIN_TOP_K_ADAPTIVE
    
    def test_adjustment_respects_max_min_similarity(self):
        """Ajuste deve respeitar MAX_MIN_SIMILARITY_ADAPTIVE."""
        result = _adjust_retrieval_params(
            complexity_score=10,
            base_top_k=5,
            base_min_similarity=0.5
        )
        assert result["min_similarity"] <= MAX_MIN_SIMILARITY_ADAPTIVE
    
    def test_adjustment_respects_min_min_similarity(self):
        """Ajuste deve respeitar MIN_MIN_SIMILARITY_ADAPTIVE."""
        result = _adjust_retrieval_params(
            complexity_score=0,
            base_top_k=5,
            base_min_similarity=0.7
        )
        assert result["min_similarity"] >= MIN_MIN_SIMILARITY_ADAPTIVE


class TestGetAdaptiveParams:
    """Testes integração da função principal."""
    
    def test_simple_query_full_flow(self):
        """Teste completo com query simples."""
        query = "O que é RAG?"
        result = get_adaptive_params(
            query=query,
            base_top_k=5,
            base_min_similarity=0.7
        )
        
        assert "top_k" in result
        assert "min_similarity" in result
        assert "analysis" in result
        assert "adjustment_reason" in result
        assert "original_top_k" in result
        assert "original_min_similarity" in result
        
        assert result["original_top_k"] == 5
        assert result["original_min_similarity"] == 0.7
        assert result["analysis"]["complexity_score"] <= 3
    
    def test_complex_query_full_flow(self):
        """Teste completo com query complexa."""
        query = "Como configurar o sistema completo incluindo Query Expansion, HyDE, Re-ranking e Adaptive Retrieval para produção?"
        result = get_adaptive_params(
            query=query,
            base_top_k=10,
            base_min_similarity=0.5
        )
        
        assert result["original_top_k"] == 10
        assert result["original_min_similarity"] == 0.5
        assert result["analysis"]["complexity_score"] >= 7
        assert result["top_k"] < 10  # Deve diminuir
        assert result["min_similarity"] > 0.5  # Deve aumentar
    
    def test_default_values(self):
        """Deve usar valores padrão do config se não informados."""
        query = "Teste"
        result = get_adaptive_params(query=query)
        
        assert "top_k" in result
        assert "min_similarity" in result
        assert result["original_top_k"] == TOP_K_RESULTS
        assert result["original_min_similarity"] == MIN_SIMILARITY_THRESHOLD
    
    def test_analysis_contains_all_fields(self):
        """Análise deve conter todos os campos esperados."""
        query = "Como configurar o sistema?"
        result = get_adaptive_params(query=query)
        
        analysis = result["analysis"]
        assert "complexity_score" in analysis
        assert "word_count" in analysis
        assert "is_short" in analysis
        assert "has_question_words" in analysis
        assert "has_multiple_sentences" in analysis
        assert "is_technical" in analysis
    
    def test_word_count_accurate(self):
        """Contagem de palavras deve ser precisa."""
        query = "Como configurar o sistema de forma adequada?"
        result = get_adaptive_params(query=query)
        
        # 7 palavras: Como, configurar, o, sistema, de, forma, adequada
        assert result["analysis"]["word_count"] == 7


class TestEdgeCases:
    """Testes de casos de borda."""
    
    def test_very_long_query(self):
        """Query muito longa não deve causar erro."""
        query = "Teste " * 100  # 500 palavras
        result = get_adaptive_params(query=query)
        
        assert result is not None
        assert result["analysis"]["complexity_score"] <= 10
    
    def test_special_characters(self):
        """Query com caracteres especiais."""
        query = "Como usar @#$% no sistema?"
        result = get_adaptive_params(query=query)
        
        assert result is not None
        assert "complexity_score" in result["analysis"]
    
    def test_unicode_characters(self):
        """Query com caracteres unicode."""
        query = "Como configurar com emojis 🎉 e caracteres especiais é à á?"
        result = get_adaptive_params(query=query)
        
        assert result is not None
        assert "complexity_score" in result["analysis"]
    
    def test_single_word_query(self):
        """Query de uma única palavra."""
        query = "RAG"
        result = get_adaptive_params(query=query)
        
        assert result["analysis"]["word_count"] == 1
        assert result["analysis"]["complexity_score"] <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
