# 📋 Plano de Implementação: Chunking Semântico

## 📌 Objetivo

Substituir o chunking baseado em caracteres por um chunking semântico que:
- Respeita limites naturais do texto (sentenças, parágrafos)
- Mantém a coesão semântica de cada chunk
- Evita cortar frases no meio
- Preserva o contexto necessário para compreensão

---

## 🔍 Análise do Estado Atual

### Código Atual (`src/data/ingestion.py`)

```python
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Divide um texto em chunks com overlap."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Tenta quebrar em um espaço (apenas espaço, não ponto)
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
```

### Problemas Identificados

| Problema | Exemplo |
|----------|---------|
| Corta no espaço, não na sentença | `"...protocolo de roteamento. O"` → `"GWPRP é um"` |
| Ignora parágrafos | Junta parágrafos diferentes no mesmo chunk |
| Overlap cego | Pode repetir contexto desnecessário |
| Sem tratamento de listas/tabelas | Quebra estruturas formatadas |

---

## 🎯 Estratégia de Implementação

### Abordagem Escolhida: **Sentence-Based Chunking**

Dividir o texto primeiro em sentenças, depois agrupar sentenças até atingir o tamanho desejado.

### Bibliotecas

| Opção | Prós | Contras |
|-------|------|---------||
| **NLTK** | Leve, maduro, bom para PT-BR | Precisa download de dados |
| **spaCy** | Muito preciso, rápido, pipeline completo | Pesado (~15MB modelo pt_core_news_sm) |
| **re (regex)** | Zero dependências | Menos preciso |

**Escolha:** `spaCy` (maior precisão na segmentação de sentenças e suporte nativo a português)

---

## 📝 Especificação Técnica

### Nova Função: `chunk_text_semantic`

```python
def chunk_text_semantic(
    text: str,
    max_chunk_size: int = 800,
    min_chunk_size: int = 200,
    overlap_sentences: int = 1
) -> list[str]:
    """
    Divide texto em chunks respeitando limites de sentenças.
    
    Args:
        text: Texto a ser dividido
        max_chunk_size: Tamanho máximo do chunk em caracteres
        min_chunk_size: Tamanho mínimo (evita chunks muito pequenos)
        overlap_sentences: Número de sentenças de overlap
        
    Returns:
        Lista de chunks semanticamente coesos
    """
```

### Algoritmo

```
1. Dividir texto em parágrafos (por \n\n)
2. Para cada parágrafo:
   a. Dividir em sentenças (usando spaCy)
   b. Agrupar sentenças até atingir max_chunk_size
   c. Ao atingir limite, iniciar novo chunk com overlap
3. Mesclar chunks muito pequenos com adjacentes
4. Retornar lista de chunks
```

### Regras de Quebra

| Prioridade | Delimitador | Descrição |
|------------|-------------|-----------|
| 1 | `\n\n` | Parágrafo (sempre respeitar) |
| 2 | `. ` + maiúscula | Fim de sentença |
| 3 | `? `, `! ` | Fim de sentença interrogativa/exclamativa |
| 4 | `; ` | Ponto e vírgula |
| 5 | `: ` | Dois pontos (se seguido de lista) |

---

## 📂 Estrutura de Arquivos

```
src/data/
├── ingestion.py          # Mantém funções existentes
├── chunking.py           # NOVO: Módulo de chunking semântico
└── __init__.py
```

### Novo Arquivo: `src/data/chunking.py`

```python
"""
Módulo de chunking semântico para textos.
"""
import re
from typing import List, Optional
import spacy

# Carregar modelo português (instalar uma vez: python -m spacy download pt_core_news_sm)
nlp = spacy.load("pt_core_news_sm")

class SemanticChunker:
    """Classe para chunking semântico de textos."""
    
    def __init__(
        self,
        max_chunk_size: int = 800,
        min_chunk_size: int = 200,
        overlap_sentences: int = 1,
        language: str = "portuguese"
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap_sentences = overlap_sentences
        self.language = language
    
    def chunk(self, text: str) -> List[str]:
        """Divide texto em chunks semânticos."""
        ...
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Divide texto em sentenças."""
        ...
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Divide texto em parágrafos."""
        ...
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """Mescla chunks muito pequenos."""
        ...
```

---

## ✅ Tarefas de Implementação

### Fase 1: Setup (45 min) ✅ CONCLUÍDA
- [x] Adicionar `spacy>=3.7.0` ao `requirements.txt`
- [x] Instalar spaCy: `pip install spacy`
- [x] Baixar modelo português: `python -m spacy download pt_core_news_sm`
- [x] Criar arquivo `src/data/chunking.py`
- [x] Implementar carregamento do modelo spaCy com fallback

### Fase 2: Core (2 horas) ✅ CONCLUÍDA
- [x] Implementar `_split_into_paragraphs()`
- [x] Implementar `_split_into_sentences()`
- [x] Implementar lógica de agrupamento de sentenças
- [x] Implementar overlap por sentenças
- [x] Implementar `_merge_small_chunks()`

### Fase 3: Integração (1 hora) ✅ CONCLUÍDA
- [x] Atualizar `ingestion.py` para usar `SemanticChunker`
- [x] Manter função antiga como fallback (`chunk_text_legacy`)
- [x] Adicionar flag de configuração em `config.py`
- [x] Adicionar logging para informar modo de chunking

### Fase 4: Testes (1 hora) ✅ CONCLUÍDA
- [x] Testar com textos em português
- [x] Testar com PDFs reais do projeto
- [x] Comparar qualidade dos chunks (antes vs depois)
- [x] Verificar se não quebrou nada

**Resultados dos Testes:**
| Métrica | Semântico | Legado | Melhoria |
|---------|-----------|--------|----------|
| Total de chunks | 275 | 242 | +13.6% |
| Taxa incompletos | 5.1% | 92.6% | **94.5% menos** |
| Tamanho médio | 711 chars | 792 chars | Dentro da meta |

### Fase 5: Re-ingestão (30 min) ✅ CONCLUÍDA
- [x] Limpar banco de dados
- [x] Re-processar todos os documentos
- [x] Validar quantidade e qualidade dos chunks

**Resultado da Re-ingestão:**
- Chunks antes: 262 (legado)
- Chunks depois: 295 (semântico)
- Modo: SEMÂNTICO (spaCy)
- Tempo total: ~15 segundos

---

## 🎉 IMPLEMENTAÇÃO CONCLUÍDA

Todas as 5 fases foram concluídas com sucesso!

## 📊 Métricas de Sucesso

| Métrica | Antes | Meta |
|---------|-------|------|
| Sentenças cortadas | ~30% | < 5% |
| Chunks com contexto incompleto | ~40% | < 10% |
| Tamanho médio do chunk | 750 chars | 600-800 chars |
| Variação de tamanho | Alta | Baixa |

### Como Medir

```python
def analyze_chunk_quality(chunks: list[str]) -> dict:
    """Analisa qualidade dos chunks gerados."""
    incomplete = 0
    for chunk in chunks:
        # Chunk que não termina com pontuação
        if not chunk.rstrip()[-1] in '.!?':
            incomplete += 1
    
    return {
        "total_chunks": len(chunks),
        "incomplete_sentences": incomplete,
        "incomplete_rate": incomplete / len(chunks),
        "avg_size": sum(len(c) for c in chunks) / len(chunks)
    }
```

---

## 🔄 Migração

### Estratégia de Rollback

1. Manter função `chunk_text()` original
2. Adicionar config `USE_SEMANTIC_CHUNKING = True`
3. Se problemas, basta alterar para `False`

### Configuração (`config.py`)

```python
# Chunking
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
USE_SEMANTIC_CHUNKING = True  # NOVO
CHUNK_OVERLAP_SENTENCES = 1   # NOVO
MIN_CHUNK_SIZE = 200          # NOVO
```

---

## 📅 Cronograma

| Dia | Atividade | Tempo |
|-----|-----------|-------|
| 1 | Setup + Fase 1-2 | 3h |
| 2 | Fase 3-4 (Integração + Testes) | 2h |
| 3 | Fase 5 (Re-ingestão) + Validação | 1h |

**Total estimado:** 6 horas

---

## 🚀 Próximos Passos

1. Aprovar este plano
2. Iniciar implementação da Fase 1
3. Testar com subset de documentos
4. Re-ingerir base completa
5. Marcar como ✅ concluído no `MELHORIAS.md`

---

## 📚 Referências

- [spaCy Linguistic Features](https://spacy.io/usage/linguistic-features#sbd)
- [spaCy Models - Portuguese](https://spacy.io/models/pt)
- [Chunking Strategies for RAG](https://www.pinecone.io/learn/chunking-strategies/)
- [Semantic Chunking Best Practices](https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_chunking.html)

---

*Criado em: Novembro 2025*
