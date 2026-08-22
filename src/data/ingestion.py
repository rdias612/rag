"""
Módulo de ingestão de documentos: leitura de múltiplos formatos e chunking.

Formatos suportados:
- PDF (.pdf)
- Word (.docx)
- Excel (.xlsx)
- PowerPoint (.pptx)
- Texto (.txt)
- Markdown (.md)
- HTML (.html, .htm)
- CSV (.csv)
"""
import os
import warnings
from pathlib import Path
from datetime import datetime
from typing import Generator, Callable, Optional, Literal, List, Dict, Any

from markitdown import MarkItDown

from src.core.embeddings import get_embeddings_batch
from src.core.advanced_batch_processor import get_advanced_processor
from src.core.logger import get_logger

logger = get_logger("data.ingestion")

from src.config import (
    DOCUMENTS_DIR, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP,
    USE_SEMANTIC_CHUNKING, 
    MIN_CHUNK_SIZE,
    CHUNK_OVERLAP_SENTENCES,
    ENABLE_ADVANCED_BATCH_PROCESSING,
    PARENT_CHUNK_SIZE,
    CHILD_CHUNK_SIZE,
    CHILD_CHUNK_OVERLAP,
    ENABLE_CONTEXTUAL_RETRIEVAL
)
from src.data.chunking import chunk_text_semantic, analyze_chunk_quality
from src.data.hierarchical_chunking import create_parent_child_chunks
from src.data.sentence_window import create_sentence_index
from src.data.contextual_retrieval import contextualize_document_chunks

# =============================================================================
# Formatos suportados e Proibidos (MarkItDown requer API key para estes)
# =============================================================================
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".html", ".htm", ".csv"
}

FORBIDDEN_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",  # Imagens
    ".mp3", ".wav", ".m4a", ".flac"    # Áudio
}

# Instância global do MarkItDown
md_converter = MarkItDown()


def extract_text_with_markitdown(file_path: Path) -> list[dict]:
    """
    Converte qualquer documento suportado para Markdown usando a biblioteca MarkItDown da Microsoft.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista de dicts com text e page (Markdown total em page=1)
    """
    ext = file_path.suffix.lower()
    
    # Proteção contra formatos que requerem API Key (imagem/áudio)
    if ext in FORBIDDEN_EXTENSIONS:
        logger.warning("Formato %s não suportado sem chave de API: %s", ext, file_path.name)
        raise ValueError(
            f"O formato {ext} requer uma chave de API para processamento (Multimodal) "
            "e não está habilitado no momento."
        )

    try:
        logger.info("Convertendo %s para Markdown...", file_path.name)
        start_time = datetime.now()
        result = md_converter.convert(str(file_path))
        text = result.text_content
        duration = (datetime.now() - start_time).total_seconds()
        
        if not text or not text.strip():
            logger.warning("MarkItDown retornou texto vazio para %s", file_path.name)
            return []
            
        logger.info("Extração concluída para %s em %.2fs. Tamanho: %d caracteres.", file_path.name, duration, len(text))
        return [{"text": text.strip(), "page": 1}]
    except Exception as e:
        logger.error("Erro ao converter %s com MarkItDown: %s", file_path.name, e)
        raise e


def get_extractor_for_file(file_path: Path) -> Callable[[Path], list[dict]]:
    """
    Retorna a função extratora MarkItDown.
    """
    return extract_text_with_markitdown


def extract_text_from_pdf(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo PDF.
    DEPRECATED: Use extract_text_with_markitdown() ou get_extractor_for_file().
    """
    return extract_text_with_markitdown(file_path)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """
    Divide o texto em chunks menores com sobreposição (overlapping).
    DEPRECATED: Use chunk_text_semantic() para chunking inteligente.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space != -1 and last_space > start + (chunk_size // 2):
                end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - chunk_overlap
        if start >= len(text) - chunk_overlap:
            break
    
    return chunks


def process_pdf(file_path: Path) -> list[dict]:
    """
    Processa um arquivo PDF: extrai texto e cria chunks com metadados.
    DEPRECATED: Use process_document() para suporte a múltiplos formatos.
    """
    return process_document(file_path)


def process_document(file_path: Path) -> list[dict]:
    """
    Processa um documento suportado: extrai texto e cria chunks com metadados.
    """
    return process_document_with_chunking_type(file_path, "hierarchical")


def process_document_sentence_window(file_path: Path) -> list[dict]:
    """
    Processa um documento usando Sentence Window Retrieval.
    """
    extractor = get_extractor_for_file(file_path)
    pages = extractor(file_path)
    
    full_text = "\n\n".join([p["text"] for p in pages])
    
    base_metadata = {
        "source": file_path.name,
        "source_path": str(file_path),
        "file_type": file_path.suffix.lower(),
        "timestamp": datetime.now().isoformat(),
        "page": 1
    }
    
    sentence_chunks = create_sentence_index(
        full_text,
        base_metadata
    )
    
    for chunk in sentence_chunks:
        chunk["metadata"]["chunk_type"] = "sentence"
        chunk["metadata"]["chunk_index"] = chunk["metadata"]["sentence_index"]
        chunk["metadata"]["page"] = 1
    
    logger.debug("Created %d sentence chunks for %s", len(sentence_chunks), file_path.name)
    return sentence_chunks


def process_document_with_chunking_type(
    file_path: Path,
    chunking_type: Literal["hierarchical", "sentence"] = "hierarchical"
) -> list[dict]:
    """
    Processa um documento usando o tipo de chunking especificado.
    """
    if chunking_type == "hierarchical":
        return _process_document_hierarchical(file_path)
    elif chunking_type == "sentence":
        return process_document_sentence_window(file_path)
    else:
        logger.warning("Unknown chunking type: %s, using hierarchical", chunking_type)
        return _process_document_hierarchical(file_path)


def _process_document_hierarchical(file_path: Path) -> list[dict]:
    """
    Implementação interna de hierarchical chunking com Contextual Retrieval opcional.
    """
    extractor = get_extractor_for_file(file_path)
    pages = extractor(file_path)
    
    full_text = "\n\n".join([p["text"] for p in pages])
    
    base_metadata = {
        "source": file_path.name,
        "source_path": str(file_path),
        "file_type": file_path.suffix.lower(),
        "timestamp": datetime.now().isoformat()
    }
    
    logger.debug("Iniciando chunking hierárquico para %s", file_path.name)
    start_chunking = datetime.now()
    parent_chunks, child_chunks = create_parent_child_chunks(
        full_text,
        base_metadata,
        parent_size=PARENT_CHUNK_SIZE,
        child_size=CHILD_CHUNK_SIZE,
        child_overlap=CHILD_CHUNK_OVERLAP
    )
    duration_chunking = (datetime.now() - start_chunking).total_seconds()
    logger.debug("Chunking concluído: %d pais, %d filhos em %.2fs", len(parent_chunks), len(child_chunks), duration_chunking)
    
    # 1. Processar Chunks Pais
    for i, p in enumerate(parent_chunks):
        p["metadata"]["chunk_index"] = i
        p["metadata"]["page"] = 1
        p["metadata"]["chunk_type"] = "parent"
        
    # 2. Processar Chunks Filhos
    for i, c in enumerate(child_chunks):
        c["metadata"]["chunk_index"] = i
        c["metadata"]["page"] = 1
        c["metadata"]["chunk_type"] = "child"
        
        parent_idx = c["metadata"].get("parent_index", -1)
        if 0 <= parent_idx < len(parent_chunks):
            parent_text = parent_chunks[parent_idx]["content"]
            lines = parent_text.split('\n')
            if lines:
                first_line = lines[0].strip()
                if 3 < len(first_line) < 100 and (first_line.isupper() or first_line.endswith(':')):
                    c["metadata"]["possible_section"] = first_line
    
    # 3. Contextual Retrieval (Padrão Anthropic - opcional)
    if ENABLE_CONTEXTUAL_RETRIEVAL:
        child_chunks = contextualize_document_chunks(full_text, child_chunks, enabled=True)
    
    # Retornar ambos para inserção no banco
    return parent_chunks + child_chunks


def get_all_pdfs(directory: Path = DOCUMENTS_DIR) -> list[Path]:
    """Lista todos os arquivos PDF em um diretório (recursivo)."""
    return [f for f in get_all_documents(directory) if f.suffix.lower() == ".pdf"]


def get_all_documents(directory: Path = DOCUMENTS_DIR) -> list[Path]:
    """
    Lista todos os arquivos suportados em um diretório (recursivo).
    """
    document_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                document_files.append(Path(root) / file)
    return document_files


def process_all_documents(
    directory: Path = DOCUMENTS_DIR,
    chunking_type: Optional[Literal["hierarchical", "sentence"]] = None
) -> Generator[dict, None, None]:
    """
    Processa todos os documentos suportados de um diretório, gerando chunks.
    """
    document_files = get_all_documents(directory)
    chunking_mode = "SEMÂNTICO (spaCy)" if USE_SEMANTIC_CHUNKING else "LEGADO (caracteres)"
    
    logger.info("Encontrados %d documentos para processamento (Modo: %s)", len(document_files), chunking_mode)
    
    total_chunks = 0
    for i, doc_path in enumerate(document_files, start=1):
        try:
            relative_path = doc_path.relative_to(directory)
            if len(relative_path.parts) > 1:
                collection_id = relative_path.parts[0]
            else:
                collection_id = "default"
        except ValueError:
            collection_id = "default"
            
        logger.info("[%d/%d] Processando: %s (Coleção: %s)", i, len(document_files), doc_path.name, collection_id)
        
        try:
            chunks = process_document_with_chunking_type(
                doc_path,
                chunking_type if chunking_type else "hierarchical"
            )
            total_chunks += len(chunks)
            logger.debug("Gerados %d chunks para %s", len(chunks), doc_path.name)
            
            for chunk in chunks:
                chunk["collection_id"] = collection_id
                yield chunk
        except Exception as e:
            logger.error("Erro ao processar %s: %s", doc_path.name, e)
            continue
    
    logger.info("Processamento concluído: %d chunks gerados de %d arquivos", total_chunks, len(document_files))


def get_document_stats(directory: Path = DOCUMENTS_DIR) -> dict:
    """
    Retorna estatísticas sobre os documentos no diretório.
    """
    document_files = get_all_documents(directory)
    total_size = 0
    files_by_type = {}
    
    for doc_path in document_files:
        ext = doc_path.suffix.lower()
        files_by_type[ext] = files_by_type.get(ext, 0) + 1
        try:
            total_size += doc_path.stat().st_size
        except OSError:
            pass
    
    return {
        "total_documents": len(document_files),
        "by_type": files_by_type,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "supported_formats": list(SUPPORTED_EXTENSIONS),
        "files": [p.name for p in document_files]
    }


def process_document_advanced(
    file_path: Path,
    use_advanced: Optional[bool] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[dict]:
    """
    Processa documento usando processador avançado quando disponível.
    """
    chunks = process_document_with_chunking_type(file_path, "hierarchical")
    
    if not chunks:
        return []
    
    should_use_advanced = (
        use_advanced if use_advanced is not None 
        else ENABLE_ADVANCED_BATCH_PROCESSING
    )
    
    texts = [chunk["content"] for chunk in chunks]
    
    if should_use_advanced and len(texts) >= 32:
        logger.info("Usando advanced batch processor para %s (%d textos)", file_path.name, len(texts))
        processor = get_advanced_processor()
        embeddings = processor.process_batch_sync(texts, progress_callback)
    else:
        logger.debug("Usando standard batch processor para %s (%d textos)", file_path.name, len(texts))
        embeddings = get_embeddings_batch(texts)
    
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    
    return chunks
