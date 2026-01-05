"""
Módulo de Chunking Hierárquico (Parent-Child).

Implementa estratégia de chunks hierárquicos:
- Chunks pequenos para busca precisa
- Chunks pais (maiores) para contexto expandido ao LLM

Benefícios:
- Maior precisão na busca (chunks pequenos)
- Melhor contexto para resposta (chunks pais grandes)
"""

from typing import Optional

print(__name__)


# Configurações padrão
DEFAULT_PARENT_SIZE = 2000  # caracteres
DEFAULT_CHILD_SIZE = 400   # caracteres
DEFAULT_CHILD_OVERLAP = 50  # caracteres


def create_parent_child_chunks(
    text: str,
    metadata: dict,
    parent_size: int = DEFAULT_PARENT_SIZE,
    child_size: int = DEFAULT_CHILD_SIZE,
    child_overlap: int = DEFAULT_CHILD_OVERLAP
) -> tuple[list[dict], list[dict]]:
    """
    Cria chunks hierárquicos (pais e filhos).
    
    Args:
        text: Texto completo do documento
        metadata: Metadados do documento
        parent_size: Tamanho dos chunks pais
        child_size: Tamanho dos chunks filhos
        child_overlap: Overlap entre chunks filhos
        
    Returns:
        Tupla (lista_pais, lista_filhos)
        Cada filho tem referência ao índice do pai
    """
    if not text or not text.strip():
        return [], []
    
    # 1. Criar chunks pais (grandes)
    parent_chunks = []
    parent_start = 0
    parent_idx = 0
    
    while parent_start < len(text):
        parent_end = min(parent_start + parent_size, len(text))
        
        # Tentar terminar em fim de sentença
        if parent_end < len(text):
            for punct in ['. ', '.\n', '! ', '? ']:
                last_punct = text.rfind(punct, parent_start, parent_end)
                if last_punct > parent_start + parent_size // 2:
                    parent_end = last_punct + 1
                    break
        
        parent_content = text[parent_start:parent_end].strip()
        
        if parent_content:
            parent_chunk = {
                "content": parent_content,
                "metadata": {
                    **metadata,
                    "chunk_type": "parent",
                    "parent_index": parent_idx,
                    "char_start": parent_start,
                    "char_end": parent_end
                }
            }
            parent_chunks.append(parent_chunk)
            parent_idx += 1
        
        parent_start = parent_end
    
    # 2. Criar chunks filhos (pequenos) dentro de cada pai
    child_chunks = []
    
    for parent in parent_chunks:
        parent_content = parent["content"]
        parent_index = parent["metadata"]["parent_index"]
        parent_char_start = parent["metadata"]["char_start"]
        
        child_start = 0
        child_idx = 0
        
        while child_start < len(parent_content):
            child_end = min(child_start + child_size, len(parent_content))
            
            # Tentar terminar em fim de sentença
            if child_end < len(parent_content):
                for punct in ['. ', '.\n', '! ', '? ']:
                    last_punct = parent_content.rfind(punct, child_start, child_end)
                    if last_punct > child_start + child_size // 2:
                        child_end = last_punct + 1
                        break
            
            child_content = parent_content[child_start:child_end].strip()
            
            if child_content and len(child_content) > 50:  # Mínimo 50 chars
                child_chunk = {
                    "content": child_content,
                    "metadata": {
                        **metadata,
                        "chunk_type": "child",
                        "parent_index": parent_index,
                        "child_index": child_idx,
                        "char_start": parent_char_start + child_start,
                        "char_end": parent_char_start + child_end
                    }
                }
                child_chunks.append(child_chunk)
                child_idx += 1
            
            # Próximo chunk com overlap
            child_start = child_end - child_overlap
            if child_start >= len(parent_content) - child_overlap:
                break
    
    print(
        f"Hierarchical chunking: {len(parent_chunks)} parents, "
        f"{len(child_chunks)} children"
    )
    
    return parent_chunks, child_chunks


def get_parent_for_child(
    child_chunk: dict,
    parent_chunks: list[dict]
) -> Optional[dict]:
    """
    Recupera o chunk pai de um chunk filho.
    
    Args:
        child_chunk: Chunk filho
        parent_chunks: Lista de chunks pais
        
    Returns:
        Chunk pai ou None
    """
    parent_index = child_chunk.get("metadata", {}).get("parent_index")
    
    if parent_index is not None:
        for parent in parent_chunks:
            if parent.get("metadata", {}).get("parent_index") == parent_index:
                return parent
    
    return None


def expand_children_to_parents(
    child_results: list[dict],
    parent_chunks: list[dict],
    deduplicate: bool = True
) -> list[dict]:
    """
    Expande resultados de busca (filhos) para seus chunks pais.
    
    Args:
        child_results: Resultados da busca (chunks filhos)
        parent_chunks: Lista de todos os chunks pais
        deduplicate: Se True, remove pais duplicados
        
    Returns:
        Lista de chunks pais únicos
    """
    seen_parents = set()
    expanded = []
    
    for child in child_results:
        parent = get_parent_for_child(child, parent_chunks)
        
        if parent:
            parent_index = parent.get("metadata", {}).get("parent_index")
            
            if deduplicate and parent_index in seen_parents:
                continue
            
            seen_parents.add(parent_index)
            
            # Copiar parent e adicionar info do child que o encontrou
            parent_copy = parent.copy()
            parent_copy["found_via_child"] = child.get("metadata", {})
            parent_copy["child_similarity"] = child.get("similarity", 0)
            expanded.append(parent_copy)
    
    return expanded


def check_hierarchical_chunking_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "default_parent_size": DEFAULT_PARENT_SIZE,
        "default_child_size": DEFAULT_CHILD_SIZE
    }
