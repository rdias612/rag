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
