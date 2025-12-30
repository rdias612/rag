"""
Script de teste manual para Self-RAG.

Uso:
    python tests/manual_test_self_rag.py

Este script testa o Self-RAG com diferentes configurações e cenários.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import ENABLE_SELF_RAG, SELF_RAG_MIN_SCORE, SELF_RAG_MAX_ITERATIONS, ENABLE_QUERY_EXPANSION
from src.core.rag import query_rag


def print_section(title: str):
    """Imprime uma seção formatada."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_configuration():
    """Testa e exibe configurações atuais."""
    print_section("CONFIGURAÇÕES ATUAIS")
    
    print(f"Self-RAG habilitado: {ENABLE_SELF_RAG}")
    print(f"Score mínimo: {SELF_RAG_MIN_SCORE}")
    print(f"Máximo de iterações: {SELF_RAG_MAX_ITERATIONS}")
    print(f"Query Expansion habilitado: {ENABLE_QUERY_EXPANSION}")


def test_simple_query():
    """Testa uma query simples."""
    print_section("TESTE 1: Query Simples")
    
    question = "Qual é a capital do Brasil?"
    print(f"Pergunta: {question}")
    print("\nBuscando...")
    
    try:
        result = query_rag(question, include_sources=True)
        
        print(f"\n--- RESPOSTA ---")
        print(result["answer"])
        
        if "self_rag" in result:
            print(f"\n--- MÉTRICAS SELF-RAG ---")
            print(f"Iterações: {result['self_rag']['iterations']}")
            print(f"Score inicial: {result['self_rag']['initial_score']}")
            print(f"Score final: {result['self_rag']['final_score']}")
            print(f"Refinado: {result['self_rag']['was_refined']}")
            print(f"Tempo total: {result['self_rag']['total_time_ms']:.2f} ms")
        else:
            print("\n--- SELF-RAG NÃO EXECUTADO (desabilitado ou não aplicável) ---")
        
        print(f"\n--- MÉTRICAS GERAIS ---")
        print(f"Tempo total: {result.get('duration', 0):.2f} s")
        print(f"Fontes encontradas: {len(result.get('sources', []))}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")


def test_complex_query():
    """Testa uma query complexa que pode precisar de refinamento."""
    print_section("TESTE 2: Query Complexa (pode precisar de refinamento)")
    
    question = "Quais são os benefícios e desvantagens do uso de RAG em sistemas de IA?"
    print(f"Pergunta: {question}")
    print("\nBuscando...")
    
    try:
        result = query_rag(question, include_sources=True)
        
        print(f"\n--- RESPOSTA ---")
        print(result["answer"])
        
        if "self_rag" in result:
            print(f"\n--- MÉTRICAS SELF-RAG ---")
            print(f"Iterações: {result['self_rag']['iterations']}")
            print(f"Score inicial: {result['self_rag']['initial_score']}")
            print(f"Score final: {result['self_rag']['final_score']}")
            print(f"Refinado: {result['self_rag']['was_refined']}")
            print(f"Tempo total: {result['self_rag']['total_time_ms']:.2f} ms")
            
            if result['self_rag']['was_refined']:
                print("\n✅ Resposta foi refinada pelo Self-RAG!")
            else:
                print("\n✅ Resposta considerada completa (não precisou de refinamento)")
        else:
            print("\n--- SELF-RAG NÃO EXECUTADO (desabilitado ou não aplicável) ---")
        
        print(f"\n--- MÉTRICAS GERAIS ---")
        print(f"Tempo total: {result.get('duration', 0):.2f} s")
        print(f"Fontes encontradas: {len(result.get('sources', []))}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")


def test_no_results():
    """Testa uma query que não retorna resultados."""
    print_section("TESTE 3: Query Sem Resultados")
    
    question = "Como criar um motor de warp drive interestelar?"
    print(f"Pergunta: {question}")
    print("\nBuscando...")
    
    try:
        result = query_rag(question, include_sources=True)
        
        print(f"\n--- RESPOSTA ---")
        print(result["answer"])
        
        print(f"\n--- STATUS ---")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Fontes encontradas: {len(result.get('sources', []))}")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 60)
    print("  TESTE MANUAL DO SELF-RAG")
    print("=" * 60)
    
    # Testar configurações
    test_configuration()
    
    # Verificar se Self-RAG está habilitado
    if not ENABLE_SELF_RAG:
        print(f"\n⚠️  ATENÇÃO: Self-RAG está desabilitado!")
        print(f"   Para habilitar, defina ENABLE_SELF_RAG=True no arquivo .env")
        print(f"   Continuando testes anyway...\n")
    
    # Executar testes
    test_simple_query()
    test_complex_query()
    test_no_results()
    
    print_section("TESTES CONCLUÍDOS")
    print("Para mais informações sobre Self-RAG:")
    print("  - Ver README.md seção '8. Self-RAG (Reflexão)'")
    print("  - Ver docs/SUGESTOES_MELHORIAS.md item 1")
    print()


if __name__ == "__main__":
    main()
