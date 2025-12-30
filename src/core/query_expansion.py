"""
Módulo de Query Expansion.

Expande a query original com variações geradas pelo LLM
para melhorar o recall da busca.
"""
import logging
from typing import Optional

from src.core.llm import generate_response
from src.core.logger import rag_logger
from src.core.prompts import get_active_prompt

logger = logging.getLogger(__name__)


def expand_query(
    query: str,
    num_variations: int = 3,
    temperature: float = 0.7
) -> list[str]:
    """
    Expande a query original gerando variações.
    
    Args:
        query: Query original do usuário
        num_variations: Número de variações a gerar
        temperature: Temperatura para diversidade
        
    Returns:
        Lista com query original + variações
    """
    rag_logger.info(f"Expanding query: '{query[:50]}...' with {num_variations} variations")
    
    try:
        # Gerar variações usando LLM
        prompt_template = get_active_prompt('query_expansion_prompt')
        prompt = prompt_template.format(
            query=query,
            num_variations=num_variations
        )
        
        response = generate_response(prompt, temperature=temperature, max_tokens=256)
        
        # Parsear variações (uma por linha)
        variations = []
        for line in response.strip().split("\n"):
            line = line.strip()
            # Remover numeração se houver
            if line and len(line) > 3:
                # Remove "1.", "1)", "- " etc
                if line[0].isdigit() and (line[1] in ".)" or (line[1].isdigit() and line[2] in ".)")):
                    line = line.split(" ", 1)[-1] if " " in line else line
                elif line.startswith("- "):
                    line = line[2:]
                if line:
                    variations.append(line.strip())
        
        # Limitar ao número solicitado
        variations = variations[:num_variations]
        
        # Query original + variações
        all_queries = [query] + variations
        
        rag_logger.info(f"Query expanded to {len(all_queries)} variations")
        
        return all_queries
        
    except Exception as e:
        logger.error(f"Error expanding query: {e}")
        # Fallback: retornar apenas query original
        return [query]


def merge_search_results(
    results_list: list[list[dict]],
    top_k: int = 10,
    k_constant: int = 60
) -> list[dict]:
    """
    Combina resultados de múltiplas buscas usando Reciprocal Rank Fusion (RRF).
    
    Args:
        results_list: Lista de listas de resultados (cada uma de uma variação)
        top_k: Número de resultados finais
        k_constant: Constante RRF (padrão 60)
        
    Returns:
        Lista de resultados combinados e ordenados
    """
    if not results_list:
        return []
    
    if len(results_list) == 1:
        return results_list[0][:top_k]
    
    # Mapa de scores por ID do documento
    doc_scores = {}
    doc_data = {}
    
    for result_set in results_list:
        for rank, doc in enumerate(result_set):
            # Usar content como chave única (ou id se disponível)
            doc_id = doc.get("id") or hash(doc.get("content", "")[:100])
            
            rrf_score = 1.0 / (k_constant + rank + 1)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_data[doc_id] = doc
            
            doc_scores[doc_id] += rrf_score
    
    # Ordenar por score combinado
    sorted_docs = sorted(
        [(doc_id, score) for doc_id, score in doc_scores.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Construir resultado final
    result = []
    for doc_id, score in sorted_docs[:top_k]:
        doc = doc_data[doc_id].copy()
        doc["rrf_score"] = score
        result.append(doc)
    
    logger.debug(f"RRF merged {sum(len(r) for r in results_list)} results into {len(result)}")
    
    return result


def check_query_expansion_available() -> dict:
    """Verifica status do módulo."""
    return {
        "available": True,
        "method": "llm"
    }
