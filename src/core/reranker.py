"""
Reranker leve usando a LLM servida pelo LM Studio.

Estratégia: enviar pares (query, documento) para a API /chat/completions
e extrair um score numérico entre 0 e 1 retornado pela LLM. Mantém a
imagem leve (sem torch/sentence-transformers) e reutiliza a infra do LM Studio.
"""
import logging
import re
from typing import Optional

import requests

from src.config import LM_STUDIO_BASE_URL, RERANKER_MODEL

logger = logging.getLogger(__name__)

_reranker_instance: Optional["LLMReranker"] = None


class LLMReranker:
    """Reranker baseado em LLM via LM Studio (chat/completions)."""

    def __init__(self, model_name: str, max_doc_chars: int = 2000):
        self.model_name = model_name
        self.max_doc_chars = max_doc_chars

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
        # Clipa para [0,1]
        return max(0.0, min(1.0, score))

    def score_pair(self, query: str, doc: str) -> float:
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
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._extract_score(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rerank LLM falhou: %s", exc)
            return 0.0

    def rerank(self, query: str, chunks: list[dict], top_k: int = 5, content_key: str = "content") -> list[dict]:
        if not chunks:
            return []

        scored = []
        for chunk in chunks:
            text = chunk.get(content_key) or ""
            score = self.score_pair(query, text)
            copy = chunk.copy()
            copy["rerank_score"] = score
            scored.append(copy)

        scored.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
        return scored[:top_k]


def get_reranker(model_name: Optional[str] = None) -> LLMReranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = LLMReranker(model_name=model_name or RERANKER_MODEL)
    return _reranker_instance


def rerank_chunks(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    reranker = get_reranker()
    return reranker.rerank(query, chunks, top_k)


def check_reranker_available() -> dict:
    return {
        "lm_studio_reranker": True,
        "model_name": (get_reranker().model_name if _reranker_instance else None),
    }
