# 09 - Refatorar rag.py em Services

## Objetivo
Dividir `src/core/rag.py` (1035 linhas) em services especializados seguindo Single Responsibility.

---

## Arquivos a Criar

| Arquivo | Responsabilidade |
|---------|------------------|
| `src/core/rag/pipeline.py` | Orquestrador leve (~150 linhas) |
| `src/core/rag/services/search_service.py` | Busca híbrida e vetorial |
| `src/core/rag/services/context_service.py` | Compressão e montagem de contexto |
| `src/core/rag/services/prompt_service.py` | Construção de prompts |
| `src/core/rag/services/response_service.py` | Fallbacks e formatação |
| `src/core/rag/strategies/retrieval_strategy.py` | Estratégias de retrieval |

---

## Passos de Implementação

### Passo 1: Criar Estrutura

```bash
mkdir src\core\rag
mkdir src\core\rag\services
mkdir src\core\rag\strategies
```

### Passo 2: Criar `search_service.py`

```python
"""
Serviço de busca de documentos.
"""
from typing import Optional
from src.data.database import search_similar
from src.core.hybrid_search import hybrid_search
from src.config import ENABLE_HYBRID_SEARCH, HYBRID_SEARCH_ALPHA


class SearchService:
    """Encapsula lógica de busca vetorial e híbrida."""
    
    def __init__(self):
        self._use_hybrid = ENABLE_HYBRID_SEARCH
        self._hybrid_alpha = HYBRID_SEARCH_ALPHA
    
    def search(
        self,
        question: str,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float = None,
        use_hybrid: bool = None,
        collection_id: str = None
    ) -> list[dict]:
        """
        Executa busca de documentos.
        
        Args:
            question: Texto da pergunta
            query_embedding: Embedding da pergunta
            top_k: Número de resultados
            min_similarity: Similaridade mínima
            use_hybrid: Forçar busca híbrida on/off
            collection_id: Filtrar por coleção
            
        Returns:
            Lista de documentos com score
        """
        should_use_hybrid = use_hybrid if use_hybrid is not None else self._use_hybrid
        
        if should_use_hybrid:
            return hybrid_search(
                question=question,
                query_embedding=query_embedding,
                top_k=top_k,
                alpha=self._hybrid_alpha,
                collection_id=collection_id
            )
        else:
            return search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                min_similarity=min_similarity,
                collection_id=collection_id
            )
```

### Passo 3: Criar `context_service.py`

```python
"""
Serviço de montagem e compressão de contexto.
"""
from src.core.context_compression import compress_context
from src.config import (
    ENABLE_CONTEXT_COMPRESSION,
    CONTEXT_COMPRESSION_THRESHOLD,
    CONTEXT_COMPRESSION_METHOD
)


class ContextService:
    """Gerencia montagem e otimização de contexto."""
    
    def __init__(self):
        self._compression_enabled = ENABLE_CONTEXT_COMPRESSION
        self._threshold = CONTEXT_COMPRESSION_THRESHOLD
        self._method = CONTEXT_COMPRESSION_METHOD
    
    def build_context(self, documents: list[dict]) -> str:
        """Monta contexto a partir dos documentos."""
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.get("metadata", {}).get("source", "desconhecido")
            content = doc.get("content", "")
            context_parts.append(f"[Documento {i} - Fonte: {source}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def compress_if_needed(
        self, 
        context: str, 
        question: str,
        force_compression: bool = None
    ) -> dict:
        """
        Comprime contexto se necessário.
        
        Returns:
            Dict com context, was_compressed, original_tokens, final_tokens
        """
        should_compress = force_compression if force_compression is not None else self._compression_enabled
        
        # Estimar tokens (~4 chars por token)
        original_tokens = len(context) // 4
        
        if not should_compress or original_tokens < self._threshold:
            return {
                "context": context,
                "was_compressed": False,
                "original_tokens": original_tokens,
                "final_tokens": original_tokens,
                "compression_ratio": 1.0
            }
        
        compressed = compress_context(
            context=context,
            question=question,
            method=self._method
        )
        
        final_tokens = len(compressed) // 4
        
        return {
            "context": compressed,
            "was_compressed": True,
            "original_tokens": original_tokens,
            "final_tokens": final_tokens,
            "compression_ratio": final_tokens / original_tokens if original_tokens > 0 else 1.0
        }
```

### Passo 4: Criar `prompt_service.py`

```python
"""
Serviço de construção de prompts.
"""
from src.core.prompts import get_active_prompt
from src.data.database import get_prompt
from src.core.question_classifier import get_instructions_for_type
from src.config import RAG_PROMPT_TEMPLATE, USE_ENHANCED_PROMPTS


class PromptService:
    """Gerencia construção de prompts dinâmicos."""
    
    def build_prompt(
        self,
        context: str,
        question: str,
        question_type: str = None,
        history: str = None,
        response_style: str = "detailed"
    ) -> str:
        """
        Constrói prompt final para o LLM.
        
        Args:
            context: Contexto dos documentos
            question: Pergunta do usuário
            question_type: Tipo classificado da pergunta
            history: Histórico de conversa (opcional)
            response_style: Estilo de resposta
            
        Returns:
            Prompt formatado
        """
        # Tentar carregar prompt do banco
        db_prompt = self._get_db_prompt(question_type, history is not None)
        
        if db_prompt:
            return self._format_db_prompt(db_prompt, context, question, history)
        
        # Fallback para template de config
        return self._format_default_prompt(context, question, question_type, history)
    
    def _get_db_prompt(self, question_type: str, with_history: bool) -> dict | None:
        """Busca prompt apropriado no banco."""
        # Lógica existente de get_active_prompt
        pass
    
    def _format_db_prompt(self, prompt: dict, context: str, question: str, history: str) -> str:
        """Formata prompt do banco com variáveis."""
        template = prompt["template"]
        return template.format(
            contexto=context,
            pergunta=question,
            historico=history or ""
        )
    
    def _format_default_prompt(self, context: str, question: str, question_type: str, history: str) -> str:
        """Formata prompt padrão de config."""
        instructions = get_instructions_for_type(question_type) if question_type else ""
        
        return RAG_PROMPT_TEMPLATE.format(
            contexto=context,
            pergunta=question,
            instrucoes_tipo=instructions
        )
```

### Passo 5: Criar `pipeline.py` (Orquestrador)

```python
"""
Pipeline RAG principal - orquestrador leve.
"""
from src.core.embeddings import generate_embedding
from src.core.llm import generate_response
from src.core.rag.services.search_service import SearchService
from src.core.rag.services.context_service import ContextService
from src.core.rag.services.prompt_service import PromptService
from src.core.question_classifier import classify_question
from src.core.metrics import LatencyTracker


class RAGPipeline:
    """Pipeline RAG com injeção de dependências."""
    
    def __init__(
        self,
        search_service: SearchService = None,
        context_service: ContextService = None,
        prompt_service: PromptService = None
    ):
        self.search = search_service or SearchService()
        self.context = context_service or ContextService()
        self.prompts = prompt_service or PromptService()
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        temperature: float = 0.7,
        include_sources: bool = True,
        collection_id: str = None,
        **kwargs
    ) -> dict:
        """Executa query RAG completa."""
        with LatencyTracker("rag_total"):
            # 1. Classificar pergunta
            question_type = classify_question(question)
            
            # 2. Gerar embedding
            with LatencyTracker("embedding"):
                embedding = generate_embedding(question)
            
            # 3. Buscar documentos
            with LatencyTracker("search"):
                documents = self.search.search(
                    question=question,
                    query_embedding=embedding,
                    top_k=top_k,
                    collection_id=collection_id
                )
            
            if not documents:
                return self._no_results_response(question, question_type)
            
            # 4. Montar e comprimir contexto
            raw_context = self.context.build_context(documents)
            context_result = self.context.compress_if_needed(raw_context, question)
            
            # 5. Construir prompt
            prompt = self.prompts.build_prompt(
                context=context_result["context"],
                question=question,
                question_type=question_type
            )
            
            # 6. Gerar resposta
            with LatencyTracker("llm"):
                answer = generate_response(prompt, temperature=temperature)
            
            return {
                "answer": answer,
                "sources": documents if include_sources else [],
                "question_type": question_type,
                "context_compressed": context_result["was_compressed"]
            }


# Instância global para compatibilidade
_pipeline = RAGPipeline()

def query_rag(question: str, **kwargs) -> dict:
    """Wrapper para compatibilidade com código existente."""
    return _pipeline.query(question, **kwargs)
```

### Passo 6: Atualizar Imports

```python
# src/core/rag/__init__.py
from .pipeline import RAGPipeline, query_rag

__all__ = ["RAGPipeline", "query_rag"]
```

---

## Verificação

```bash
# Testar que pipeline continua funcionando
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "O que é RAG?"}'
```

---

## Benefícios

- **Testabilidade**: Services podem ser testados isoladamente
- **Manutenção**: Cada arquivo com ~150-200 linhas
- **Extensibilidade**: Fácil adicionar novas estratégias
- **Injeção**: Pipeline aceita services customizados
