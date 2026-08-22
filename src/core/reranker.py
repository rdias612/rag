"""
Módulo de Reranking.

Suporta dois modos:
1. LLM: Usa uma LLM (via LM Studio) com prompt para pontuar documentos.
2. API: Usa um endpoint /rerank dedicado (Cross-Encoder real, ex: TEI, Jina, Cohere).
"""
import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import requests

from src.config import (
    LM_STUDIO_BASE_URL, 
    RERANKER_MODEL, 
    LLM_MODEL, 
    RERANKER_TYPE, 
    RERANKER_API_URL
)
from src.core.logger import get_logger

logger = get_logger("core.reranker")


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5, content_key: str = "content", request_id: str = None) -> List[Dict[str, Any]]:
        """Reordena chunks com base na relevância para a query."""
        pass


class LLMReranker(Reranker):
    """Reranker baseado em LLM via LM Studio (chat/completions)."""

    def __init__(self, model_name: str, max_doc_chars: int = 2000):
        self.model_name = model_name
        self.max_doc_chars = max_doc_chars
        self.fallback_model = LLM_MODEL

    def _build_prompt(self, query: str, doc: str) -> list[dict]:
        truncated_doc = doc[: self.max_doc_chars]
        system = (
            "You are a retrieval reranker. Given a user query and a document, "
            "return only a numeric relevance score between 0 and 1. Use high scores "
            "for semantically relevant documents. Output format: SCORE: <float>"
        )
        user = f"Query: {query}\nDocument:\n{truncated_doc}\nAnswer only the score."
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _extract_score(self, text: str) -> float:
        match = re.search(r"([0-1](?:\.\d+)?|0?\.\d+)", text)
        if not match:
            return 0.0
        try:
            score = float(match.group(1))
        except ValueError:
            return 0.0
        return max(0.0, min(1.0, score))

    def score_pair(self, query: str, doc: str, use_fallback: bool = True, request_id: str = None) -> float:
        request_id = request_id or "unknown"
        
        payload = {
            "model": self.model_name,
            "messages": self._build_prompt(query, doc),
            "temperature": 0,
            "max_tokens": 8,
        }
        try:
            resp = requests.post(
                f"{LM_STUDIO_BASE_URL}/chat/completions", json=payload, timeout=30
            )
            
            if resp.status_code == 400 and use_fallback and self.model_name != self.fallback_model:
                logger.warning("Reranker model '%s' falhou (400). Tentando fallback para '%s'...", 
                               self.model_name, self.fallback_model)
                payload["model"] = self.fallback_model
                resp = requests.post(
                    f"{LM_STUDIO_BASE_URL}/chat/completions", json=payload, timeout=30
                )

            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            score = self._extract_score(content)
            return score
        except Exception as exc:
            logger.error("LLM Reranker Error | request_id=%s | model=%s | error=%s",
                         request_id, self.model_name, exc)
            return 0.0

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5, content_key: str = "content", request_id: str = None) -> List[Dict[str, Any]]:
        request_id = request_id or "unknown"
        
        if not chunks:
            return []
        
        logger.info("LLM Reranking Started | request_id=%s | chunks_count=%d | top_k=%d",
                    request_id, len(chunks), top_k)

        scored = []
        for chunk in chunks:
            text = chunk.get(content_key) or ""
            score = self.score_pair(query, text, request_id=request_id)
            copy = chunk.copy()
            copy["rerank_score"] = score
            scored.append(copy)

        scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return scored[:top_k]


class CrossEncoderAPIReranker(Reranker):
    """Reranker que usa um endpoint /rerank real (Cross-Encoder)."""
    
    def __init__(self, api_url: str, model_name: str):
        self.api_url = api_url
        self.model_name = model_name

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5, content_key: str = "content", request_id: str = None) -> List[Dict[str, Any]]:
        request_id = request_id or "unknown"
        
        if not chunks:
            return []
        
        logger.info("Cross-Encoder Reranking Started | request_id=%s | chunks_count=%d | top_k=%d",
                    request_id, len(chunks), top_k)
        
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": [c.get(content_key, "") for c in chunks],
            "top_n": top_k
        }
        
        try:
            url = self.api_url if self.api_url.endswith("/rerank") else f"{self.api_url.rstrip('/')}/rerank"
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            
            scored_chunks = []
            for res in results:
                idx = res["index"]
                score = res["relevance_score"]
                if 0 <= idx < len(chunks):
                    copy = chunks[idx].copy()
                    copy["rerank_score"] = score
                    scored_chunks.append(copy)
                    
            scored_chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return scored_chunks[:top_k]
            
        except Exception as exc:
            logger.error("Cross-Encoder Rerank falhou: %s", exc)
            return chunks[:top_k]


def get_reranker() -> Reranker:
    """Factory para instanciar o reranker configurado."""
    if RERANKER_TYPE == "api" and RERANKER_API_URL:
        return CrossEncoderAPIReranker(api_url=RERANKER_API_URL, model_name=RERANKER_MODEL)
    return LLMReranker(model_name=RERANKER_MODEL)


def rerank_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 5, request_id: str = None) -> List[Dict[str, Any]]:
    """Função de conveniência para reordenar chunks usando o reranker padrão."""
    reranker = get_reranker()
    return reranker.rerank(query, chunks, top_k=top_k, request_id=request_id)
