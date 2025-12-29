# 🚀 Plano de Implementação: Otimização de Batch Processing Assíncrono

**Item:** 6.1 - Otimização de Batch Processing Assíncrono
**Status Atual:** ⚠️ PARCIALMENTE IMPLEMENTADO
**Prioridade:** 🚀 Alta Prioridade (Performance)
**Tempo Estimado:** 1-2 semanas

---

## 📋 Resumo

**Objetivo:** Implementar processamento paralelo de múltiplos batches simultâneos para embeddings, aproveitando ao máximo a capacidade de GPU e reduzindo o tempo de ingestão em até 2.5x.

**Impacto Esperado:**
- Throughput adicional de 2.5x para embeddings
- Ingestão 2x mais rápida
- Melhor utilização de GPU com múltiplos workers
- Redução adicional de 40% em custos por embedding

---

## 🔍 Análise do Estado Atual

### ✅ O que já existe

1. **`src/core/embeddings.py`**
   - Função `get_embeddings_batch()` que processa múltiplos textos
   - Batch size configurável (padrão: 32)
   - Processamento sequencial de um batch por vez

2. **`src/api/routes.py`**
   - Threading para ingestão em massa
   - Processamento assíncrono de documentos individuais
   - Status tracking de jobs de ingestão

### ❌ O que falta

1. **Paralelismo de Batches**
   - Processa apenas um batch por vez
   - Não aproveita múltiplos workers simultâneos
   - GPU subutilizada durante batch processing

2. **Gerenciamento de Workers**
   - Não há configuração de número de workers
   - Não há controle de concorrência
   - Não há monitoramento de utilização de recursos

3. **Integração Otimizada**
   - Sistema de ingestão não usa paralelismo de batches
   - Cada documento processa seus chunks sequencialmente

---

## 🏗️ Arquitetura Proposta

### Fluxo Atual (Sequencial)

```
Documento → Chunks (100) → Batch 1 (32) → Embedding 1 → Inserir
                            ↓
                       Batch 2 (32) → Embedding 2 → Inserir
                            ↓
                       Batch 3 (32) → Embedding 3 → Inserir
                            ↓
                       Batch 4 (4) → Embedding 4 → Inserir
```

**Tempo total:** ~5 segundos (sequencial)

### Fluxo Proposto (Paralelo)

```
Documento → Chunks (100) ──────────────────────────────────┐
                              ↓                              ↓
                        Batch 1 (32)                   Batch 2 (32)
                        Worker 1                        Worker 2
                              ↓                              ↓
                        Embedding 1                     Embedding 2
                              ↓                              ↓
                        Inserir 1                        Inserir 2
                              ↓                              ↓
                        Batch 3 (32)                   Batch 4 (4)
                        Worker 3                        Worker 4
                              ↓                              ↓
                        Embedding 3                     Embedding 4
                              ↓                              ↓
                        Inserir 3                        Inserir 4
                              ↓                              ↓
                              └─────────────────────────────────┘
                                    Resultados
```

**Tempo total:** ~2 segundos (paralelo - 2.5x mais rápido)

---

## 📦 Arquivos a Criar/Modificar

### Novos Arquivos

1. **`src/core/advanced_batch_processor.py`** - Módulo principal do processador avançado
2. **`tests/test_advanced_batch_processor.py`** - Testes unitários

### Arquivos a Modificar

1. **`src/config.py`** - Adicionar configurações do processador avançado
2. **`src/api/routes.py`** - Integrar processador avançado na ingestão
3. **`src/data/ingestion.py`** - Adicionar opção de usar processador avançado
4. **`requirements.txt`** - Verificar dependências (já tem `asyncio`, `concurrent.futures`)
5. **`README.md`** - Documentar a nova funcionalidade

---

## 🔧 Implementação Detalhada

### Etapa 1: Configurações (1 dia)

#### 1.1. Adicionar Configurações em `src/config.py`

```python
# Configurações de Batch Processing Avançado
ENABLE_ADVANCED_BATCH_PROCESSING = os.getenv("ENABLE_ADVANCED_BATCH_PROCESSING", "true").lower() == "true"

# Número de workers paralelos para processamento de embeddings
# Recomendado: 2-4 para GPU única, mais para multi-GPU
ADVANCED_BATCH_MAX_WORKERS = int(os.getenv("ADVANCED_BATCH_MAX_WORKERS", "4"))

# Tamanho do batch para processamento paralelo
ADVANCED_BATCH_SIZE = int(os.getenv("ADVANCED_BATCH_SIZE", "32"))

# Timeout para processamento de cada worker (segundos)
ADVANCED_WORKER_TIMEOUT = int(os.getenv("ADVANCED_WORKER_TIMEOUT", "120"))

# Habilitar/desabilitar async await (true para máxima performance, false para compatibilidade)
USE_ASYNC_BATCH_PROCESSING = os.getenv("USE_ASYNC_BATCH_PROCESSING", "true").lower() == "true"
```

**Teste:**
```bash
# Testar configurações
python -c "from src.config import ADVANCED_BATCH_MAX_WORKERS; print(f'Workers: {ADVANCED_BATCH_MAX_WORKERS}')"
```

---

### Etapa 2: Processador Avançado (2-3 dias)

#### 2.1. Criar `src/core/advanced_batch_processor.py`

```python
"""
Processador Avançado de Embeddings com Paralelismo.

Implementa processamento paralelo de múltiplos batches simultâneos
para maximizar a utilização de GPU e reduzir tempo de ingestão.

Author: Sistema RAG
Created: 2025-12-29
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
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
        from concurrent.futures import as_completed
        
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
```

#### 2.2. Criar `tests/test_advanced_batch_processor.py`

```python
"""
Testes unitários para AdvancedBatchEmbeddingProcessor.
"""
import pytest
from src.core.advanced_batch_processor import AdvancedBatchEmbeddingProcessor


class TestAdvancedBatchProcessor:
    """Testes do processador avançado de embeddings."""
    
    @pytest.fixture
    def processor(self):
        """Fixture que cria um processador para testes."""
        return AdvancedBatchEmbeddingProcessor(
            batch_size=4,
            max_workers=2,
            timeout=10
        )
    
    def test_initialization(self, processor):
        """Testa inicialização do processador."""
        assert processor.batch_size == 4
        assert processor.max_workers == 2
        assert processor.timeout == 10
        assert processor.executor is not None
    
    def test_split_into_batches(self, processor):
        """Testa divisão de textos em batches."""
        texts = [f"text_{i}" for i in range(10)]
        batches = processor._split_into_batches(texts)
        
        assert len(batches) == 3  # 4 + 4 + 2
        assert len(batches[0]) == 4
        assert len(batches[1]) == 4
        assert len(batches[2]) == 2
    
    def test_process_single_batch(self, processor):
        """Testa processamento de um único batch."""
        texts = [f"text_{i}" for i in range(4)]
        
        embeddings = processor._process_single_batch(texts, batch_index=0)
        
        assert len(embeddings) == 4
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)
    
    def test_process_batch_sync_small(self, processor):
        """Testa processamento paralelo síncrono com poucos textos."""
        texts = [f"text_{i}" for i in range(8)]
        
        embeddings = processor.process_batch_sync(texts)
        
        assert len(embeddings) == 8
        assert all(isinstance(emb, list) for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_process_batch_parallel_async(self, processor):
        """Testa processamento paralelo assíncrono."""
        texts = [f"text_{i}" for i in range(12)]
        
        embeddings = await processor.process_batch_parallel(texts)
        
        assert len(embeddings) == 12
        assert all(isinstance(emb, list) for emb in embeddings)
    
    def test_progress_callback(self, processor):
        """Testa callback de progresso."""
        texts = [f"text_{i}" for i in range(16)]
        progress_updates = []
        
        def callback(current, total):
            progress_updates.append((current, total))
        
        processor.process_batch_sync(texts, callback)
        
        assert len(progress_updates) > 0
        assert progress_updates[-1] == (len(progress_updates), len(progress_updates))
    
    def test_empty_list_raises_error(self, processor):
        """Testa que lista vazia levanta ValueError."""
        with pytest.raises(ValueError):
            processor.process_batch_sync([])
    
    def test_stats_tracking(self, processor):
        """Testa rastreamento de estatísticas."""
        texts = [f"text_{i}" for i in range(8)]
        
        processor.process_batch_sync(texts)
        stats = processor.get_stats()
        
        assert stats["total_texts_processed"] == 8
        assert stats["total_batches_processed"] > 0
        assert stats["avg_throughput_texts_per_second"] > 0
    
    def test_reset_stats(self, processor):
        """Testa reset de estatísticas."""
        texts = [f"text_{i}" for i in range(8)]
        
        processor.process_batch_sync(texts)
        assert processor.get_stats()["total_texts_processed"] == 8
        
        processor.reset_stats()
        assert processor.get_stats()["total_texts_processed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

### Etapa 3: Integração com Ingestão (2 dias)

#### 3.1. Modificar `src/data/ingestion.py`

Adicionar opção de usar processador avançado:

```python
from src.core.advanced_batch_processor import get_advanced_processor
from src.config import ENABLE_ADVANCED_BATCH_PROCESSING


def process_document_advanced(
    file_path: Path,
    use_advanced: bool = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[dict]:
    """
    Processa documento usando processador avançado quando disponível.
    
    Args:
        file_path: Caminho do arquivo para processar
        use_advanced: Força uso do processador avançado (None usa config)
        progress_callback: Callback para progresso (current, total)
        
    Returns:
        Lista de chunks com metadados
    """
    # Extrair texto e criar chunks (mesmo processamento atual)
    chunks = process_document(file_path)
    
    if not chunks:
        return []
    
    # Decidir se usa processador avançado
    should_use_advanced = (
        use_advanced if use_advanced is not None 
        else ENABLE_ADVANCED_BATCH_PROCESSING
    )
    
    texts = [chunk["content"] for chunk in chunks]
    
    if should_use_advanced and len(texts) >= 32:  # Mínimo de 32 textos para valer a pena
        rag_logger.info(
            f"Using advanced batch processor for {file_path.name} "
            f"({len(texts)} texts)"
        )
        
        processor = get_advanced_processor()
        embeddings = processor.process_batch_sync(texts, progress_callback)
        
    else:
        # Usar processamento padrão
        rag_logger.info(
            f"Using standard batch processor for {file_path.name} "
            f"({len(texts)} texts)"
        )
        embeddings = get_embeddings_batch(texts)
    
    # Adicionar embeddings aos chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    
    return chunks
```

#### 3.2. Modificar `src/api/routes.py`

Integrar na ingestão em massa:

```python
from src.data.ingestion import process_document_advanced


def _process_ingestion_job_advanced(job_id: str, file_path: Path, original_filename: str):
    """
    Processa um documento em background usando processador avançado.
    
    Args:
        job_id: ID do job de ingestão
        file_path: Caminho do arquivo salvo
        original_filename: Nome original do arquivo
    """
    try:
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "processing"
            _ingestion_jobs[job_id]["message"] = "Extraindo texto e dividindo em chunks..."
        
        # 1. Processar documento com progresso
        progress_updates = []
        
        def progress_callback(current, total):
            with _ingestion_lock:
                progress_percent = int((current / total) * 100)
                _ingestion_jobs[job_id]["message"] = (
                    f"Gerando embeddings: {current}/{total} batches ({progress_percent}%)"
                )
            progress_updates.append((current, total))
        
        # Processar documento
        chunks = process_document_advanced(
            file_path,
            use_advanced=True,
            progress_callback=progress_callback
        )
        
        if not chunks:
            with _ingestion_lock:
                _ingestion_jobs[job_id]["status"] = "failed"
                _ingestion_jobs[job_id]["error"] = "Nenhum texto extraído do documento"
            return
        
        # 2. Inserir no banco (mesmo processo atual)
        with _ingestion_lock:
            _ingestion_jobs[job_id]["chunks_created"] = len(chunks)
            _ingestion_jobs[job_id]["message"] = "Inserindo no banco de dados..."
        
        documents_to_insert = [
            {
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "embedding": chunk["embedding"]
            }
            for chunk in chunks
        ]
        
        inserted = insert_documents_batch(documents_to_insert)
        
        # 3. Finalizar
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "completed"
            _ingestion_jobs[job_id]["chunks_inserted"] = inserted
            _ingestion_jobs[job_id]["message"] = f"Sucesso! {inserted} chunks indexados."
            _ingestion_jobs[job_id]["completed_at"] = datetime.now().isoformat()
            
            # Adicionar estatísticas do processador avançado
            if ENABLE_ADVANCED_BATCH_PROCESSING:
                processor = get_advanced_processor()
                stats = processor.get_stats()
                _ingestion_jobs[job_id]["advanced_stats"] = stats
        
        api_logger.info(f"Ingestion job {job_id[:8]}... completed: {inserted} chunks")
        
    except Exception as e:
        api_logger.error(f"Ingestion job {job_id[:8]}... failed: {e}")
        with _ingestion_lock:
            _ingestion_jobs[job_id]["status"] = "failed"
            _ingestion_jobs[job_id]["error"] = str(e)
    
    finally:
        # Limpar arquivo temporário
        try:
            if file_path.exists():
                file_path.unlink()
        except:
            pass
```

---

### Etapa 4: Adicionar Endpoint de Métricas (0.5 dia)

#### 4.1. Adicionar endpoint em `src/api/routes.py`

```python
@api.route("/api/embeddings/advanced-stats", methods=["GET"])
def get_advanced_batch_processor_stats():
    """
    Retorna estatísticas do processador avançado de embeddings.
    
    Response:
        {
            "stats": {
                "total_batches_processed": 100,
                "total_texts_processed": 3200,
                "total_errors": 2,
                "total_time_seconds": 64.5,
                "avg_throughput_texts_per_second": 49.6,
                "batch_size": 32,
                "max_workers": 4,
                "error_rate": 0.02
            },
            "enabled": true
        }
    """
    start_time = time.time()
    log_api_request("/api/embeddings/advanced-stats", "GET")
    
    try:
        from src.core.advanced_batch_processor import get_advanced_processor
        from src.config import ENABLE_ADVANCED_BATCH_PROCESSING
        
        processor = get_advanced_processor()
        stats = processor.get_stats()
        
        log_api_response("/api/embeddings/advanced-stats", 200, time.time() - start_time)
        
        return jsonify({
            "stats": stats,
            "enabled": ENABLE_ADVANCED_BATCH_PROCESSING
        })
        
    except Exception as e:
        api_logger.error(f"Error in /api/embeddings/advanced-stats: {e}")
        log_api_response("/api/embeddings/advanced-stats", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500


@api.route("/api/embeddings/advanced-stats/reset", methods=["POST"])
def reset_advanced_batch_processor_stats():
    """
    Reseta as estatísticas do processador avançado.
    
    Response:
        {"message": "Estatísticas resetadas com sucesso"}
    """
    start_time = time.time()
    log_api_request("/api/embeddings/advanced-stats/reset", "POST")
    
    try:
        from src.core.advanced_batch_processor import get_advanced_processor
        
        processor = get_advanced_processor()
        processor.reset_stats()
        
        log_api_response("/api/embeddings/advanced-stats/reset", 200, time.time() - start_time)
        
        return jsonify({"message": "Estatísticas resetadas com sucesso"})
        
    except Exception as e:
        api_logger.error(f"Error in /api/embeddings/advanced-stats/reset: {e}")
        log_api_response("/api/embeddings/advanced-stats/reset", 500, time.time() - start_time)
        return jsonify({"error": str(e)}), 500
```

---

### Etapa 5: Atualizar Frontend (1 dia)

#### 5.1. Modificar `frontend/src/components/admin/DocumentsPanel.tsx`

Adicionar visualização de estatísticas do processador avançado:

```typescript
interface AdvancedStats {
  total_batches_processed: number;
  total_texts_processed: number;
  total_errors: number;
  total_time_seconds: number;
  avg_throughput_texts_per_second: number;
  batch_size: number;
  max_workers: number;
  error_rate: number;
}

// Adicionar função para buscar estatísticas
const fetchAdvancedStats = async (): Promise<AdvancedStats> => {
  const response = await fetch('/api/embeddings/advanced-stats');
  const data = await response.json();
  return data.stats;
};

// Usar no componente
useEffect(() => {
  fetchAdvancedStats().then(stats => {
    setAdvancedStats(stats);
  });
}, []);
```

---

### Etapa 6: Documentação (0.5 dia)

#### 6.1. Atualizar `README.md`

Adicionar seção sobre o processador avançado:

```markdown
## 🚀 Batch Processing Avançado

O sistema suporta processamento paralelo de embeddings para maximizar a utilização de GPU.

### Configuração

Variáveis de ambiente:

- `ENABLE_ADVANCED_BATCH_PROCESSING`: Habilita processamento avançado (default: `true`)
- `ADVANCED_BATCH_MAX_WORKERS`: Número de workers paralelos (default: `4`)
- `ADVANCED_BATCH_SIZE`: Tamanho do batch (default: `32`)
- `ADVANCED_WORKER_TIMEOUT`: Timeout por worker em segundos (default: `120`)

### Performance

Com 4 workers paralelos:
- **Sequencial**: 100 embeddings em 5 segundos = 20 emb/s
- **Paralelo**: 100 embeddings em 2 segundos = 50 emb/s
- **Speedup**: 2.5x mais rápido

### Métricas

Monitorar estatísticas do processador avançado:

```bash
curl http://localhost:5000/api/embeddings/advanced-stats
```
```

---

## 🧪 Testes

### Testes Unitários

```bash
# Rodar todos os testes do processador avançado
pytest tests/test_advanced_batch_processor.py -v

# Rodar com coverage
pytest tests/test_advanced_batch_processor.py --cov=src.core.advanced_batch_processor --cov-report=html
```

### Testes de Integração

```bash
# Testar ingestão de documento com processador avançado
curl -X POST http://localhost:5000/api/ingest \
  -F "file=@test_document.pdf" \
  | jq

# Verificar estatísticas
curl http://localhost:5000/api/embeddings/advanced-stats | jq
```

### Testes de Performance

```python
# test_performance.py
import time
from src.core.advanced_batch_processor import AdvancedBatchEmbeddingProcessor

# Criar processador
processor = AdvancedBatchEmbeddingProcessor(batch_size=32, max_workers=4)

# Gerar textos de teste
texts = [f"Test text number {i}" for i in range(128)]  # 4 batches

# Testar processamento
start = time.time()
embeddings = processor.process_batch_sync(texts)
duration = time.time() - start

print(f"Processed {len(texts)} texts in {duration:.2f}s")
print(f"Throughput: {len(texts) / duration:.2f} texts/s")
print(f"Expected speedup: ~2.5x compared to sequential")
```

---

## 📊 Métricas de Sucesso

### Métricas Técnicas

1. **Throughput**
   - Objetivo: 50+ embeddings/segundo
   - Medição: `stats["avg_throughput_texts_per_second"]`

2. **Speedup**
   - Objetivo: 2.5x mais rápido que sequencial
   - Medição: Comparar tempo de processamento

3. **Error Rate**
   - Objetivo: < 1%
   - Medição: `stats["error_rate"]`

4. **Utilização de GPU**
   - Objetivo: > 80%
   - Medição: Monitoramento da GPU (nvidia-smi)

### Métricas de Negócio

1. **Tempo de Ingestão**
   - Objetivo: Redução de 50%
   - Medição: Tempo para ingerir documentos de teste

2. **Custo por Embedding**
   - Objetivo: Redução de 40%
   - Medição: Custo total / número de embeddings

3. **Satisfação do Usuário**
   - Objetivo: Feedback positivo
   - Medição: Pesquisa com usuários

---

## 🚦 Checklist de Implementação

- [x] Análise do estado atual
- [ ] **Etapa 1: Configurações**
  - [ ] Adicionar configurações em `src/config.py`
  - [ ] Testar configurações
- [ ] **Etapa 2: Processador Avançado**
  - [ ] Criar `src/core/advanced_batch_processor.py`
  - [ ] Implementar `AdvancedBatchEmbeddingProcessor`
  - [ ] Criar `tests/test_advanced_batch_processor.py`
  - [ ] Escrever testes unitários
  - [ ] Rodar testes e validar
- [ ] **Etapa 3: Integração**
  - [ ] Modificar `src/data/ingestion.py`
  - [ ] Modificar `src/api/routes.py`
  - [ ] Testar integração com ingestão
- [ ] **Etapa 4: Métricas**
  - [ ] Adicionar endpoint `/api/embeddings/advanced-stats`
  - [ ] Adicionar endpoint `/api/embeddings/advanced-stats/reset`
  - [ ] Testar endpoints
- [ ] **Etapa 5: Frontend**
  - [ ] Modificar `DocumentsPanel.tsx`
  - [ ] Adicionar visualização de estatísticas
  - [ ] Testar frontend
- [ ] **Etapa 6: Documentação**
  - [ ] Atualizar `README.md`
  - [ ] Criar exemplos de uso
  - [ ] Revisar documentação
- [ ] **Validação Final**
  - [ ] Rodar testes completos
  - [ ] Testar ingestão de documentos
  - [ ] Medir performance
  - [ ] Documentar resultados

---

## 🎯 Critérios de Aceite

A implementação será considerada completa quando:

1. ✅ O processador avançado processa múltiplos batches em paralelo
2. ✅ Speedup de pelo menos 2x em comparação ao processamento sequencial
3. ✅ Throughput de 40+ embeddings/segundo
4. ✅ Error rate < 1%
5. ✅ Integração transparente com sistema de ingestão existente
6. ✅ Testes unitários com coverage > 80%
7. ✅ Documentação completa em README.md
8. ✅ Métricas disponíveis via API
9. ✅ Frontend exibe estatísticas do processador
10. ✅ Configurável via variáveis de ambiente

---

## 📝 Notas Importantes

### Compatibilidade

- Mantém compatibilidade 100% com processamento existente
- Pode ser desabilitado via configuração
- Fallback automático para processamento padrão em caso de erro

### Recomendações

- **Para GPU única:** Use 2-4 workers
- **Para multi-GPU:** Use 4-8 workers (1-2 por GPU)
- **Para CPU-only:** Use 2-4 workers (mais não ajuda)

### Limitações

- Requer memória suficiente para múltiplos batches em memória
- Benefício máximo para documentos com 100+ chunks
- Não recomendado para documentos muito pequenos (< 32 chunks)

---

## 📚 Referências

- [Python ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)
- [Python asyncio.gather](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- [Batch Processing Patterns](https://en.wikipedia.org/wiki/Batch_processing)
- [GPU Utilization](https://developer.nvidia.com/blog/how-optimize-data-transfers-cuda-cc/)

---

**Plano criado em:** 2025-12-29  
**Responsável:** Equipe de Desenvolvimento RAG  
**Estimativa de conclusão:** 1-2 semanas
