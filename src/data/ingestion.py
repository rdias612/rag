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
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import Generator, Callable, Optional, Literal

# Suprimir avisos do pydub sobre ffmpeg (comum em Windows sem ffmpeg instalado)
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub")

from markitdown import MarkItDown

from src.core.embeddings import get_embeddings_batch
from src.core.advanced_batch_processor import get_advanced_processor

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
    CHILD_CHUNK_OVERLAP
)
from src.data.chunking import chunk_text_semantic, analyze_chunk_quality
from src.data.hierarchical_chunking import create_parent_child_chunks
from src.core.logger import ingestion_logger as logger, log_execution_time

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
    Extrai texto de qualquer formato suportado usando MarkItDown da Microsoft.
    Converte o arquivo para Markdown antes de retornar o texto.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista de dicts com text e page (Markdown total em page=1)
    """
    ext = file_path.suffix.lower()
    
    # Proteção contra formatos que requerem API Key (imagem/áudio)
    if ext in FORBIDDEN_EXTENSIONS:
        logger.error(f"Formato {ext} não suportado sem chave de API: {file_path.name}")
        raise ValueError(
            f"O formato {ext} requer uma chave de API para processamento (Multimodal) "
            "e não está habilitado no momento."
        )

    try:
        logger.info(f"Convertendo {file_path.name} para Markdown")
        start_time = datetime.now()
        result = md_converter.convert(str(file_path))
        text = result.text_content
        duration = (datetime.now() - start_time).total_seconds()
        
        if not text or not text.strip():
            logger.warning(f"MarkItDown retornou texto vazio para {file_path.name}")
            return []
            
        logger.debug(f"Extração concluída para {file_path.name} em {duration:.2f}s. Tamanho: {len(text)} caracteres.")
        return [{"text": text.strip(), "page": 1}]
    except Exception as e:
        logger.error(f"Erro ao converter {file_path.name} com MarkItDown: {e}")
        raise e


def get_extractor_for_file(file_path: Path) -> Callable[[Path], list[dict]]:
    """
    Retorna a função extratora MarkItDown.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        Função extratora de texto
    """
    return extract_text_with_markitdown


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Divide um texto em chunks.
    
    Se USE_SEMANTIC_CHUNKING estiver ativo, usa chunking por sentenças.
    Caso contrário, usa o método legado baseado em caracteres.
    
    Args:
        text: Texto a ser dividido
        chunk_size: Tamanho máximo de cada chunk em caracteres
        overlap: Sobreposição entre chunks (ignorado no modo semântico)
        
    Returns:
        Lista de chunks de texto
    """
    if USE_SEMANTIC_CHUNKING:
        return chunk_text_semantic(
            text=text,
            max_chunk_size=chunk_size,
            min_chunk_size=MIN_CHUNK_SIZE,
            overlap_sentences=CHUNK_OVERLAP_SENTENCES
        )
    
    # Modo legado (fallback)
    return chunk_text_legacy(text, chunk_size, overlap)


def chunk_text_legacy(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Divide um texto em chunks com overlap (método legado).
    
    Args:
        text: Texto a ser dividido
        chunk_size: Tamanho máximo de cada chunk em caracteres
        overlap: Sobreposição entre chunks
        
    Returns:
        Lista de chunks de texto
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Tentar quebrar em um espaço para não cortar palavras
        if end < len(text):
            # Procurar o último espaço dentro do chunk
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Próximo chunk começa com overlap
        start = end - overlap
        
        # Evitar loop infinito
        if start >= len(text) - overlap:
            break
    
    return chunks


def process_pdf(file_path: Path) -> list[dict]:
    """
    Processa um PDF completo: extrai texto e divide em chunks.
    
    DEPRECATED: Use process_document() para suporte a múltiplos formatos.
    
    Args:
        file_path: Caminho para o arquivo PDF
        
    Returns:
        Lista de chunks com content e metadata
    """
    return process_document(file_path)


def process_document(file_path: Path) -> list[dict]:
    """
    Processa um documento usando estratégia de Parent-Child Chunking.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista de chunks (filhos e pais) com metadados estruturados
    """
    return process_document_with_chunking_type(file_path, "hierarchical")


def process_document_sentence_window(file_path: Path) -> list[dict]:
    """
    Processa um documento usando Sentence Window Retrieval.
    
    Divide o documento em sentenças individuais, cada sentença
    torna-se um chunk com metadados de posição.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista de chunks de sentenças com metadados estruturados
    """
    from src.data.sentence_window import create_sentence_index
    
    # Obter extrator apropriado
    extractor = get_extractor_for_file(file_path)
    pages = extractor(file_path)
    
    # Unificar texto
    full_text = "\n\n".join([p["text"] for p in pages])
    
    base_metadata = {
        "source": file_path.name,
        "source_path": str(file_path),
        "file_type": file_path.suffix.lower(),
        "timestamp": datetime.now().isoformat(),
        "page": 1
    }
    
    # Gerar chunks de sentenças
    sentence_chunks = create_sentence_index(
        full_text,
        base_metadata
    )
    
    # Adicionar chunk_type aos metadados
    for chunk in sentence_chunks:
        chunk["metadata"]["chunk_type"] = "sentence"
        chunk["metadata"]["chunk_index"] = chunk["metadata"]["sentence_index"]
        chunk["metadata"]["page"] = 1
    
    logger.info(f"Created {len(sentence_chunks)} sentence chunks for {file_path.name}")
    
    return sentence_chunks


def process_document_with_chunking_type(
    file_path: Path,
    chunking_type: Literal["hierarchical", "sentence"] = "hierarchical"
) -> list[dict]:
    """
    Processa um documento usando o tipo de chunking especificado.
    
    Args:
        file_path: Caminho do arquivo
        chunking_type: "hierarchical" ou "sentence"
        
    Returns:
        Lista de chunks com metadados
    """
    if chunking_type == "hierarchical":
        # Chamar função existente (sem o prefixo "process_document" para evitar recursão)
        return _process_document_hierarchical(file_path)
    elif chunking_type == "sentence":
        return process_document_sentence_window(file_path)
    else:
        logger.warning(f"Unknown chunking type: {chunking_type}, using hierarchical")
        return _process_document_hierarchical(file_path)


def _process_document_hierarchical(file_path: Path) -> list[dict]:
    """
    Implementação interna de hierarchical chunking.
    
    Separado para evitar recursão com process_document().
    """
    # Obter extrator apropriado
    extractor = get_extractor_for_file(file_path)
    pages = extractor(file_path)
    
    # Unificar texto para chunking hierárquico (preservando estrutura)
    full_text = "\n\n".join([p["text"] for p in pages])
    
    base_metadata = {
        "source": file_path.name,
        "source_path": str(file_path),
        "file_type": file_path.suffix.lower(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Gerar chunks hierárquicos
    logger.debug(f"Iniciando chunking hierárquico para {file_path.name}")
    start_chunking = datetime.now()
    parent_chunks, child_chunks = create_parent_child_chunks(
        full_text,
        base_metadata,
        parent_size=PARENT_CHUNK_SIZE,
        child_size=CHILD_CHUNK_SIZE,
        child_overlap=CHILD_CHUNK_OVERLAP
    )
    duration_chunking = (datetime.now() - start_chunking).total_seconds()
    logger.debug(f"Chunking concluído: {len(parent_chunks)} pais, {len(child_chunks)} filhos em {duration_chunking:.2f}s")
    
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
        
        # Enriquecer filhos com possíveis títulos de seção se encontrados no pai
        parent_idx = c["metadata"]["parent_index"]
        if 0 <= parent_idx < len(parent_chunks):
            parent_text = parent_chunks[parent_idx]["content"]
            lines = parent_text.split('\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line) < 100 and len(first_line) > 3:
                    if first_line.isupper() or first_line.endswith(':'):
                        c["metadata"]["possible_section"] = first_line
    
    # Retornar ambos para inserção no banco
    return parent_chunks + child_chunks


def get_all_pdfs(directory: Path = DOCUMENTS_DIR) -> list[Path]:
    """
    Lista todos os arquivos PDF em um diretório (recursivo).
    
    DEPRECATED: Use get_all_documents() para suporte a múltiplos formatos.
    
    Args:
        directory: Diretório para buscar PDFs
        
    Returns:
        Lista de caminhos para arquivos PDF
    """
    return [f for f in get_all_documents(directory) if f.suffix.lower() == ".pdf"]


def get_all_documents(directory: Path = DOCUMENTS_DIR) -> list[Path]:
    """
    Lista todos os arquivos suportados em um diretório (recursivo).
    
    Formatos suportados: .pdf, .docx, .txt, .md, .html, .htm
    
    Args:
        directory: Diretório para buscar documentos
        
    Returns:
        Lista de caminhos para arquivos suportados
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
    
    Formatos suportados: .pdf, .docx, .txt, .md, .html, .htm
    
    Args:
        directory: Diretório com os documentos
        chunking_type: Tipo de chunking (hierarchical ou sentence), None usa default
        
    Yields:
        Chunks com content, metadata e collection_id
    """
    document_files = get_all_documents(directory)
    chunking_mode = "SEMÂNTICO (spaCy)" if USE_SEMANTIC_CHUNKING else "LEGADO (caracteres)"
    
    # Contar por tipo
    files_by_type = {}
    for f in document_files:
        ext = f.suffix.lower()
        files_by_type[ext] = files_by_type.get(ext, 0) + 1
    
    logger.info(f"Encontrados {len(document_files)} documentos")
    for ext, count in sorted(files_by_type.items()):
        logger.info(f"   - {ext}: {count} arquivo(s)")
    logger.info(f"Modo de chunking: {chunking_mode}")
    logger.info(f"Iniciando processamento: {len(document_files)} documentos, modo={chunking_mode}")
    
    if USE_SEMANTIC_CHUNKING:
        logger.info(f"   - max_chunk={CHUNK_SIZE}, min_chunk={MIN_CHUNK_SIZE}, overlap_sentences={CHUNK_OVERLAP_SENTENCES}")
    
    total_chunks = 0
    
    for i, doc_path in enumerate(document_files, start=1):
        # Determinar collection_id baseado no subdiretório
        # Ex: DOCUMENTS_DIR/projeto_A/doc.pdf -> collection_id = "projeto_A"
        # Ex: DOCUMENTS_DIR/doc.pdf -> collection_id = "default"
        try:
            relative_path = doc_path.relative_to(directory)
            if len(relative_path.parts) > 1:
                # O primeiro componente do caminho relativo é o nome da coleção
                collection_id = relative_path.parts[0]
            else:
                collection_id = "default"
        except ValueError:
            collection_id = "default"
            
        logger.info(f"[{i}/{len(document_files)}] Processando: {doc_path.name} (Coleção: {collection_id})")
        
        try:
            chunks = process_document_with_chunking_type(
                doc_path,
                chunking_type if chunking_type else "hierarchical"
            )
            total_chunks += len(chunks)
            logger.info(f"   Gerados {len(chunks)} chunks ({chunking_type or 'hierarchical'})")
            logger.info(f"Processado {doc_path.name}: {len(chunks)} chunks (Coleção: {collection_id})")
            
            for chunk in chunks:
                # Adicionar collection_id ao chunk
                chunk["collection_id"] = collection_id
                yield chunk
                
        except Exception as e:
            logger.error(f"Erro ao processar {doc_path.name}: {e}")
            continue
    
    logger.info(f"Total: {total_chunks} chunks gerados de {len(document_files)} arquivos")
    logger.info(f"Processamento concluído: {total_chunks} chunks de {len(document_files)} arquivos")


def get_document_stats(directory: Path = DOCUMENTS_DIR) -> dict:
    """
    Retorna estatísticas sobre os documentos no diretório.
    
    Args:
        directory: Diretório com os documentos
        
    Returns:
        Dict com estatísticas
    """
    document_files = get_all_documents(directory)
    total_size = 0
    files_by_type = {}
    
    for doc_path in document_files:
        ext = doc_path.suffix.lower()
        files_by_type[ext] = files_by_type.get(ext, 0) + 1
        total_size += doc_path.stat().st_size
    
    return {
        "total_files": len(document_files),
        "files_by_type": files_by_type,
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
    
    Extrai texto, cria chunks e gera embeddings usando o processador
    avançado com paralelismo quando apropriado.
    
    Args:
        file_path: Caminho do arquivo para processar
        use_advanced: Força uso do processador avançado (None usa config)
        progress_callback: Callback para progresso (current, total)
        
    Returns:
        Lista de chunks com metadados e embeddings
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
        logger.info(
            f"Using advanced batch processor for {file_path.name} "
            f"({len(texts)} texts)"
        )
        
        processor = get_advanced_processor()
        embeddings = processor.process_batch_sync(texts, progress_callback)
        
    else:
        # Usar processamento padrão
        mode = "standard" if not should_use_advanced else "small document (<32 chunks)"
        logger.info(
            f"Using standard batch processor for {file_path.name} "
            f"({len(texts)} texts, mode={mode})"
        )
        embeddings = get_embeddings_batch(texts)
    
    # Adicionar embeddings aos chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding
    
    return chunks
