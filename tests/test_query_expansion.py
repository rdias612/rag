"""
Testes para o módulo de Query Expansion.

Este script testa a funcionalidade de expansão de queries
para verificar se está funcionando corretamente.
"""
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.core.query_expansion import expand_query, merge_search_results
from src.core.logger import rag_logger
from src.config import ENABLE_QUERY_EXPANSION


def test_query_expansion():
    """Testa a expansão de uma query simples."""
    print("=" * 60)
    print("TESTE: Query Expansion")
    print("=" * 60)
    
    if not ENABLE_QUERY_EXPANSION:
        print("⚠️  Query Expansion está desabilitado na configuração")
        print("   Para habilitar, set ENABLE_QUERY_EXPANSION=True em config.py ou .env")
        return False
    
    # Test query
    test_query = "O que é GWPRP?"
    print(f"\n📝 Query Original: '{test_query}'")
    print(f"\n🔄 Iniciando expansão...")
    
    try:
        # Expandir query
        variations = expand_query(test_query, num_variations=3)
        
        print(f"\n✅ Expansão concluída!")
        print(f"   Total de variações: {len(variations)}")
        
        # Mostrar resultados
        print("\n📋 Variações geradas:")
        for i, var in enumerate(variations, 1):
            print(f"   {i}. {var}")
        
        # Verificar se temos mais de a query original
        if len(variations) > 1:
            print("\n✅ SUCESSO: Query foi expandida com variações adicionais")
            return True
        else:
            print("\n⚠️  AVISO: Apenas a query original foi retornada (sem variações)")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO: Falha ao expandir query")
        print(f"   Detalhes: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rrf_merge():
    """Testa a fusão de resultados usando RRF."""
    print("\n" + "=" * 60)
    print("TESTE: RRF Merge")
    print("=" * 60)
    
    # Simular resultados de múltiplas buscas
    results_set_1 = [
        {"id": 1, "content": "Documento A sobre GWPRP", "similarity": 0.85},
        {"id": 2, "content": "Documento B sobre protocolos", "similarity": 0.80},
        {"id": 3, "content": "Documento C sobre roteamento", "similarity": 0.75},
    ]
    
    results_set_2 = [
        {"id": 1, "content": "Documento A sobre GWPRP", "similarity": 0.88},
        {"id": 3, "content": "Documento C sobre roteamento", "similarity": 0.78},
        {"id": 4, "content": "Documento D sobre redes", "similarity": 0.70},
    ]
    
    print(f"\n📊 Conjunto 1: {len(results_set_1)} documentos")
    print(f"📊 Conjunto 2: {len(results_set_2)} documentos")
    
    try:
        # Mesclar resultados
        merged = merge_search_results(
            [results_set_1, results_set_2],
            top_k=5,
            k_constant=60
        )
        
        print(f"\n✅ Merge concluído!")
        print(f"   Resultados mesclados: {len(merged)} documentos")
        
        print("\n📋 Resultados ordenados por RRF score:")
        for i, doc in enumerate(merged, 1):
            rrf_score = doc.get("rrf_score", 0)
            content_preview = doc["content"][:50] + "..." if len(doc["content"]) > 50 else doc["content"]
            print(f"   {i}. RRF={rrf_score:.4f} - {content_preview}")
        
        # Verificar se documentos duplicados foram consolidados
        unique_ids = set(doc["id"] for doc in merged)
        if len(unique_ids) < len(results_set_1) + len(results_set_2):
            print("\n✅ SUCESSO: Documentos duplicados foram consolidados")
            return True
        else:
            print("\n⚠️  AVISO: Não houve consolidação de duplicatas")
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO: Falha ao mesclar resultados")
        print(f"   Detalhes: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("  SUITE DE TESTES: QUERY EXPANSION (Item 2 - SUGESTÕES)")
    print("=" * 70)
    
    results = {
        "Query Expansion": test_query_expansion(),
        "RRF Merge": test_rrf_merge()
    }
    
    # Resumo
    print("\n" + "=" * 70)
    print("  RESUMO DOS TESTES")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("   O Item 2 (Query Expansion) está funcionando corretamente.")
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        print("   Verifique os erros acima para resolver os problemas.")
    
    print("=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
