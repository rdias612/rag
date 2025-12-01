"""
Script de teste para comparar chunking semântico vs legado.
Fase 4 do plano de implementação.
"""
import sys
sys.path.insert(0, ".")

from src.data.ingestion import get_all_pdfs, extract_text_from_pdf, chunk_text, chunk_text_legacy
from src.data.chunking import analyze_chunk_quality
from src.config import USE_SEMANTIC_CHUNKING, CHUNK_SIZE, MIN_CHUNK_SIZE, CHUNK_OVERLAP_SENTENCES


def print_separator(title: str):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_chunking_comparison():
    """Compara a qualidade do chunking semântico vs legado."""
    
    print_separator("FASE 4: TESTES DO CHUNKING SEMÂNTICO")
    
    print(f"\n📋 Configurações:")
    print(f"   USE_SEMANTIC_CHUNKING = {USE_SEMANTIC_CHUNKING}")
    print(f"   CHUNK_SIZE = {CHUNK_SIZE}")
    print(f"   MIN_CHUNK_SIZE = {MIN_CHUNK_SIZE}")
    print(f"   CHUNK_OVERLAP_SENTENCES = {CHUNK_OVERLAP_SENTENCES}")
    
    # Obter PDFs
    pdfs = get_all_pdfs()
    print(f"\n📁 PDFs encontrados: {len(pdfs)}")
    for p in pdfs:
        print(f"   - {p.name}")
    
    if not pdfs:
        print("❌ Nenhum PDF encontrado!")
        return
    
    # Resultados agregados
    total_semantic = {"chunks": 0, "incomplete": 0, "chars": 0}
    total_legacy = {"chunks": 0, "incomplete": 0, "chars": 0}
    
    for pdf in pdfs:
        print_separator(f"Testando: {pdf.name}")
        
        pages = extract_text_from_pdf(pdf)
        print(f"📄 Páginas extraídas: {len(pages)}")
        
        # Processar todas as páginas
        all_text = "\n\n".join([p["text"] for p in pages])
        print(f"📝 Texto total: {len(all_text):,} caracteres")
        
        # Chunking Semântico
        print("\n🧠 CHUNKING SEMÂNTICO:")
        chunks_semantic = chunk_text(all_text)
        quality_semantic = analyze_chunk_quality(chunks_semantic)
        print(f"   Chunks gerados: {quality_semantic['total_chunks']}")
        print(f"   Sentenças incompletas: {quality_semantic['incomplete_sentences']} ({quality_semantic['incomplete_rate']*100:.1f}%)")
        print(f"   Tamanho médio: {quality_semantic['avg_size']:.0f} chars")
        
        # Chunking Legado
        print("\n📦 CHUNKING LEGADO:")
        chunks_legacy = chunk_text_legacy(all_text)
        quality_legacy = analyze_chunk_quality(chunks_legacy)
        print(f"   Chunks gerados: {quality_legacy['total_chunks']}")
        print(f"   Sentenças incompletas: {quality_legacy['incomplete_sentences']} ({quality_legacy['incomplete_rate']*100:.1f}%)")
        print(f"   Tamanho médio: {quality_legacy['avg_size']:.0f} chars")
        
        # Agregar
        total_semantic["chunks"] += quality_semantic["total_chunks"]
        total_semantic["incomplete"] += quality_semantic["incomplete_sentences"]
        total_semantic["chars"] += quality_semantic["avg_size"] * quality_semantic["total_chunks"]
        
        total_legacy["chunks"] += quality_legacy["total_chunks"]
        total_legacy["incomplete"] += quality_legacy["incomplete_sentences"]
        total_legacy["chars"] += quality_legacy["avg_size"] * quality_legacy["total_chunks"]
        
        # Mostrar exemplos de chunks
        print("\n📋 EXEMPLOS DE CHUNKS SEMÂNTICOS:")
        for i, chunk in enumerate(chunks_semantic[:2]):
            preview = chunk[:150].replace("\n", " ")
            ending = chunk[-50:].replace("\n", " ")
            print(f"\n   Chunk {i+1} ({len(chunk)} chars):")
            print(f"   Início: \"{preview}...\"")
            print(f"   Fim: \"...{ending}\"")
    
    # Resumo final
    print_separator("RESUMO COMPARATIVO")
    
    sem_rate = (total_semantic["incomplete"] / total_semantic["chunks"] * 100) if total_semantic["chunks"] > 0 else 0
    leg_rate = (total_legacy["incomplete"] / total_legacy["chunks"] * 100) if total_legacy["chunks"] > 0 else 0
    sem_avg = total_semantic["chars"] / total_semantic["chunks"] if total_semantic["chunks"] > 0 else 0
    leg_avg = total_legacy["chars"] / total_legacy["chunks"] if total_legacy["chunks"] > 0 else 0
    
    print(f"""
    ┌─────────────────────────────────────────────────────────────┐
    │                    SEMÂNTICO    vs    LEGADO                │
    ├─────────────────────────────────────────────────────────────┤
    │  Total de chunks:    {total_semantic['chunks']:>6}              {total_legacy['chunks']:>6}            │
    │  Taxa incompletos:   {sem_rate:>5.1f}%             {leg_rate:>5.1f}%            │
    │  Tamanho médio:      {sem_avg:>5.0f} chars       {leg_avg:>5.0f} chars       │
    └─────────────────────────────────────────────────────────────┘
    """)
    
    # Verificar metas
    print("📊 VERIFICAÇÃO DAS METAS:")
    
    meta_incomplete = 5.0  # < 5%
    if sem_rate < meta_incomplete:
        print(f"   ✅ Taxa de incompletos: {sem_rate:.1f}% < {meta_incomplete}% (META ATINGIDA)")
    else:
        print(f"   ⚠️ Taxa de incompletos: {sem_rate:.1f}% >= {meta_incomplete}% (META NÃO ATINGIDA)")
    
    if sem_rate < leg_rate:
        melhoria = ((leg_rate - sem_rate) / leg_rate * 100) if leg_rate > 0 else 0
        print(f"   ✅ Melhoria vs legado: {melhoria:.1f}% menos sentenças cortadas")
    else:
        print(f"   ⚠️ Sem melhoria em relação ao legado")
    
    print("\n✅ Fase 4 concluída!")


if __name__ == "__main__":
    test_chunking_comparison()
