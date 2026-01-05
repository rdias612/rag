"""
Módulo de cache de embeddings para evitar recálculo de embeddings para queries repetidas.

Usa cache em memória com LRU (Least Recently Used) para limitar tamanho.
"""
import hashlib
import time
from collections import OrderedDict
from typing import Optional


from src.core.metrics import (
    inc_cache_hit,
    inc_cache_miss,
    inc_cache_set,
    inc_cache_evict,
    set_cache_size
)

print(__name__)


class EmbeddingCache:
    """
    Cache de embeddings em memória com política LRU.
    
    Armazena embeddings usando hash MD5 do texto normalizado como chave.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Inicializa o cache.
        
        Args:
            max_size: Número máximo de embeddings a manter em cache
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._created_at = time.time()
        
        print(f"EmbeddingCache initialized with max_size={max_size}")
    
    def _normalize_key(self, text: str) -> str:
        """
        Normaliza texto e gera hash como chave.
        
        Args:
            text: Texto original
            
        Returns:
            Hash MD5 do texto normalizado
        """
        # Normalizar: lowercase, strip, remover múltiplos espaços
        normalized = " ".join(text.lower().strip().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def get(self, text: str) -> Optional[list[float]]:
        """
        Busca embedding no cache.
        
        Args:
            text: Texto para buscar
            
        Returns:
            Embedding se encontrado, None caso contrário
        """
        key = self._normalize_key(text)
        
        if key in self._cache:
            # Move para o final (mais recentemente usado)
            self._cache.move_to_end(key)
            self._hits += 1
            inc_cache_hit()  # Prometheus metric
            print(f"Cache HIT for key {key[:8]}...")
            return self._cache[key]
        
        self._misses += 1
        inc_cache_miss()  # Prometheus metric
        print(f"Cache MISS for key {key[:8]}...")
        return None
    
    def set(self, text: str, embedding: list[float]) -> None:
        """
        Armazena embedding no cache.
        
        Args:
            text: Texto original
            embedding: Embedding a armazenar
        """
        key = self._normalize_key(text)
        
        # Se chave já existe, atualizar e mover para o final
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = embedding
            return
        
        # Verificar limite de tamanho
        if len(self._cache) >= self.max_size:
            # Remover o mais antigo (primeiro item)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            inc_cache_evict()  # Prometheus metric
            print(f"Cache evicted oldest entry: {oldest_key[:8]}...")
        
        self._cache[key] = embedding
        inc_cache_set()  # Prometheus metric
        set_cache_size(len(self._cache))  # Prometheus gauge
        print(f"Cache SET for key {key[:8]}...")
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        set_cache_size(0)  # Prometheus gauge
        print("Cache cleared")
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dict com métricas do cache
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        uptime_seconds = time.time() - self._created_at
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "uptime_seconds": round(uptime_seconds, 2)
        }
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def __contains__(self, text: str) -> bool:
        key = self._normalize_key(text)
        return key in self._cache


# Instância global do cache
embedding_cache = EmbeddingCache(max_size=1000)


# Funções de conveniência
def get_cached_embedding(text: str) -> Optional[list[float]]:
    """Busca embedding no cache global."""
    return embedding_cache.get(text)


def set_cached_embedding(text: str, embedding: list[float]) -> None:
    """Armazena embedding no cache global."""
    embedding_cache.set(text, embedding)


def clear_embedding_cache() -> None:
    """Limpa o cache global de embeddings."""
    embedding_cache.clear()


def get_cache_stats() -> dict:
    """Retorna estatísticas do cache global."""
    return embedding_cache.get_stats()
