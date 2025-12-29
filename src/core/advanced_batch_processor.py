"""
Processador Avançado de Embeddings com Paralelismo.

Implementa processamento paralelo de múltiplos batches simultâneos
para maximizar a utilização de GPU e reduzir tempo de ingestão.

Author: Sistema RAG
Created: 2025-12-29
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from typing import List, Optional, Callable, Any
from functools import partial
import time

from src.config import (
    ADVANCED_BATCH_MAX_WORKERS,
    ADVANCED_BATCH_SIZE,
    ADVANCED_WORKER_TIMEOUT,
    USE_ASYNC_BATCH_PROCESSING
)
from src.core.embeddings import get_embeddings_batch
from src.core.logger import rag_logger

rag_logger = logging.getLogger(__name__)


class AdvancedBatchEmbeddingProcessor:
    """
    Processador avançado de embeddings com paralelismo.
    
    Processa múltiplos batches em paralelo usando ThreadPoolExecutor,
    aproveitando ao máximo a capacidade da GPU.
    
    Attributes:
        batch_size: Tamanho de cada batch (default: 32)
        max_workers: Número máximo de workers paralelos (default: 4)
        executor: ThreadPoolExecutor para processamento paralelo
        timeout: Timeout para cada worker em segundos
    """
    
    def __init__(
        self,
        batch_size: int = ADVANCED_BATCH_SIZE,
        max_workers: int = ADVANCED_BATCH_MAX_WORKERS,
        timeout: int = ADVANCED_WORKER_TIMEOUT
    ):
        """
        Inicializa o processador avançado.
        
        Args:
            batch_size: Tamanho de cada batch de textos
            max_workers: Número máximo de workers paralelos
            timeout: Timeout para cada worker em segundos
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.timeout = timeout
        
        # Criar executor de thread pool
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="embed-worker-"
        )
        
        # Estatísticas
        self.stats = {
            "total_batches_processed": 0,
            "total_texts_processed": 0,
            "total_errors": 0,
            "total_time_seconds": 0.0
        }
        
        rag_logger.info(
            f"AdvancedBatchEmbeddingProcessor initialized: "
            f"batch_size={batch_size}, max_workers={max_workers}, timeout={timeout}s"
        )
    
    def _split_into_batches(self, texts: List[str]) -> List[List[str]]:
        """
        Divide a lista de textos em batches.
        
        Args:
            texts: Lista de textos para dividir
            
        Returns:
            Lista de batches
        """
        return [
            texts[i:i + self.batch_size]
            for i in range(0, len(texts), self.batch_size)
        ]
    
    def _process_single_batch(
        self,
        texts: List[str],
        batch_index: int,
        timeout: Optional[int] = None
    ) -> List[List[float]]:
        """
        Processa um único batch de textos.
        
        Args:
            texts: Batch de textos para processar
            batch_index: Índice do batch (para logging)
            timeout: Timeout opcional em segundos
            
        Returns:
            Lista de embeddings
            
        Raises:
            TimeoutError: Se processamento exceder timeout
            Exception: Se houver erro no processamento
        """
        actual_timeout = timeout or self.timeout
        start_time = time.time()
        
        try:
            rag_logger.debug(f"Processing batch {batch_index} with {len(texts)} texts")
            
            # Reusa a implementação existente de batch processing
            embeddings = get_embeddings_batch(texts, batch_size=len(texts))
            
            duration = time.time() - start_time
            rag_logger.debug(
                f"Batch {batch_index} completed in {duration:.2f}s "
                f"({len(embeddings)} embeddings)"
            )
            
            return embeddings
            
        except Exception as e:
            duration = time.time() - start_time
            rag_logger.error(
                f"Error processing batch {batch_index} after {duration:.2f}s: {e}",
                exc_info=True
            )
            raise
    
    async def process_batch_parallel(
        self,
        texts: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[float]]:
        """
        Processa lista de textos com paralelismo.
        
        Divide os textos em batches e processa múltiplos batches
        simultaneamente usando ThreadPoolExecutor.
        
        Args:
            texts: Lista de textos para gerar embeddings
            progress_callback: Callback opcional (current, total) para progresso
            
        Returns:
            Lista de embeddings na mesma ordem dos textos
            
        Raises:
            ValueError: Se lista de textos estiver vazia
            RuntimeError: Se todos os workers falharem
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        total_texts = len(texts)
        total_batches = (total_texts + self.batch_size - 1) // self.batch_size
        
        rag_logger.info(
            f"Processing {total_texts} texts in {total_batches} batches "
            f"with {self.max_workers} workers"
        )
        
        start_time = time.time()
        
        # Dividir em batches
        batches = self._split_into_batches(texts)
        
        # Processar MÚLTIPLOS BATCHES em paralelo
        try:
            if USE_ASYNC_BATCH_PROCESSING:
                embeddings = await self._process_with_async(batches, progress_callback)
            else:
                embeddings = self._process_with_executor(batches, progress_callback)
            
        except Exception as e:
            rag_logger.error(f"Parallel processing failed: {e}", exc_info=True)
            raise RuntimeError(f"Parallel processing failed: {e}")
        
        # Concatenar resultados mantendo ordem
        flattened_embeddings = [emb for batch in embeddings for emb in batch]
        
        # Atualizar estatísticas
        duration = time.time() - start_time
        self.stats["total_batches_processed"] += len(batches)
        self.stats["total_texts_processed"] += total_texts
        self.stats["total_time_seconds"] += duration
        
        # Calcular throughput
        throughput = total_texts / duration if duration > 0 else 0
        
        rag_logger.info(
            f"Parallel processing completed: {total_texts} texts "
            f"in {duration:.2f}s ({throughput:.2f} texts/s)"
        )
        
        return flattened_embeddings
    
    async def _process_with_async(
        self,
        batches: List[List[str]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[List[float]]]:
        """
        Processa batches usando asyncio.gather.
        
        Mais eficiente para I/O bound e operations que suportam async.
        
        Args:
            batches: Lista de batches para processar
            progress_callback: Callback opcional para progresso
            
        Returns:
            Lista de embeddings por batch
        """
        loop = asyncio.get_event_loop()
        
        # Criar função parcial com índice do batch
        tasks = []
        for i, batch in enumerate(batches):
            task = loop.run_in_executor(
                self.executor,
                partial(self._process_single_batch, batch, i),
            )
            tasks.append(task)
        
        # Processar todos os batches em paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verificar erros
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            self.stats["total_errors"] += len(errors)
            rag_logger.warning(
                f"{len(errors)} batches failed out of {len(batches)}"
            )
            # Re-raise primeiro erro se todos falharem
            if len(errors) == len(batches):
                raise errors[0]
        
        # Filtrar apenas resultados válidos
        valid_results = [r for r in results if not isinstance(r, Exception)]
        
        # Notificar progresso
        if progress_callback:
            progress_callback(len(valid_results), len(batches))
        
        return valid_results
    
    def _process_with_executor(
        self,
        batches: List[List[str]],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[List[float]]]:
        """
        Processa batches usando submit e wait direto.
        
        Alternativa mais simples que não usa asyncio.
        
        Args:
            batches: Lista de batches para processar
            progress_callback: Callback opcional para progresso
            
        Returns:
            Lista de embeddings por batch
        """
        # Submeter todos os batches
        future_to_batch = {}
        for i, batch in enumerate(batches):
            future = self.executor.submit(
                partial(self._process_single_batch, batch, i)
            )
            future_to_batch[future] = i
        
        # Coletar resultados
        results = [None] * len(batches)
        completed = 0
        
        for future in as_completed(future_to_batch, timeout=self.timeout * len(batches)):
            batch_index = future_to_batch[future]
            try:
                result = future.result()
                results[batch_index] = result
                completed += 1
                
                # Notificar progresso
                if progress_callback:
                    progress_callback(completed, len(batches))
                    
            except Exception as e:
                rag_logger.error(
                    f"Batch {batch_index} failed: {e}",
                    exc_info=True
                )
                results[batch_index] = e
                self.stats["total_errors"] += 1
        
        # Verificar se pelo menos um batch teve sucesso
        successful = [r for r in results if not isinstance(r, Exception)]
        if not successful:
            raise RuntimeError("All batches failed")
        
        # Filtrar apenas resultados válidos (None para falhas)
        return [r for r in results if r is not None and not isinstance(r, Exception)]
    
    def process_batch_sync(
        self,
        texts: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[float]]:
        """
        Versão síncrona do processamento paralelo.
        
        Wrapper síncrono para ser usado em código não-async.
        
        Args:
            texts: Lista de textos para gerar embeddings
            progress_callback: Callback opcional para progresso
            
        Returns:
            Lista de embeddings na mesma ordem dos textos
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                self.process_batch_parallel(texts, progress_callback)
            )
            return result
        finally:
            loop.close()
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do processador.
        
        Returns:
            Dicionário com estatísticas
        """
        if self.stats["total_time_seconds"] > 0:
            avg_throughput = (
                self.stats["total_texts_processed"] / 
                self.stats["total_time_seconds"]
            )
        else:
            avg_throughput = 0
        
        return {
            **self.stats,
            "avg_throughput_texts_per_second": round(avg_throughput, 2),
            "batch_size": self.batch_size,
            "max_workers": self.max_workers,
            "error_rate": (
                self.stats["total_errors"] / 
                max(self.stats["total_batches_processed"], 1)
            )
        }
    
    def reset_stats(self):
        """Reseta as estatísticas do processador."""
        self.stats = {
            "total_batches_processed": 0,
            "total_texts_processed": 0,
            "total_errors": 0,
            "total_time_seconds": 0.0
        }
    
    def shutdown(self, wait: bool = True):
        """
        Desliga o executor de workers.
        
        Args:
            wait: Se True, espera que todos os workers completem
        """
        rag_logger.info(f"Shutting down AdvancedBatchEmbeddingProcessor (wait={wait})")
        self.executor.shutdown(wait=wait)


# Instância global do processador avançado
advanced_processor = AdvancedBatchEmbeddingProcessor()


def get_advanced_processor() -> AdvancedBatchEmbeddingProcessor:
    """
    Retorna a instância global do processador avançado.
    
    Returns:
        Instância de AdvancedBatchEmbeddingProcessor
    """
    return advanced_processor
