"""
Módulo de ingestão de documentos: leitura de PDFs e chunking.
"""
import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Generator

import pypdf

from src.config import (
    DOCUMENTS_DIR, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP,
    USE_SEMANTIC_CHUNKING,
    MIN_CHUNK_SIZE,
    CHUNK_OVERLAP_SENTENCES
)
from src.data.chunking import chunk_text_semantic, analyze_chunk_quality

logger = logging.getLogger(__name__)


def clean_pdf_text(text: str) -> str:
    """
    Limpa texto extraído de PDF, corrigindo problemas comuns.
    
    - Remove hifenização de quebra de linha (pala-\nvra -> palavra)
    - Normaliza quebras de linha no meio de frases
    - Remove múltiplos espaços
    - Preserva parágrafos (linhas duplas)
    
    Args:
        text: Texto bruto extraído do PDF
        
    Returns:
        Texto limpo e normalizado
    """
    if not text:
        return ""
    
    # 1. Substituir quebras de linha duplas por marcador temporário
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalizar parágrafos
    text = text.replace('\n\n', '<<<PARAGRAPH>>>')
    
    # 2. Remover hifenização de quebra de linha (pala-\nvra -> palavra)
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # 3. Substituir quebras de linha simples por espaço
    text = re.sub(r'\n', ' ', text)
    
    # 4. Restaurar parágrafos
    text = text.replace('<<<PARAGRAPH>>>', '\n\n')
    
    # 5. Remover múltiplos espaços
    text = re.sub(r' +', ' ', text)
    
    # 6. Limpar espaços ao redor de parágrafos
    text = re.sub(r'\n +', '\n', text)
    text = re.sub(r' +\n', '\n', text)
    
    return text.strip()


def extract_text_from_pdf(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo PDF, página por página.
    
    Args:
        file_path: Caminho para o arquivo PDF
        
    Returns:
        Lista de dicts com text e page_number
    """
    pages = []
    
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                # Limpar texto extraído do PDF
                cleaned_text = clean_pdf_text(text)
                pages.append({
                    "text": cleaned_text,
                    "page": page_num
                })
    
    return pages


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
    
    Args:
        file_path: Caminho para o arquivo PDF
        
    Returns:
        Lista de chunks com content e metadata
    """
    pages = extract_text_from_pdf(file_path)
    all_chunks = []
    
    for page_data in pages:
        chunks = chunk_text(page_data["text"])
        
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "content": chunk,
                "metadata": {
                    "source": file_path.name,
                    "source_path": str(file_path),
                    "page": page_data["page"],
                    "chunk_index": i,
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    return all_chunks


def get_all_pdfs(directory: Path = DOCUMENTS_DIR) -> list[Path]:
    """
    Lista todos os arquivos PDF em um diretório (recursivo).
    
    Args:
        directory: Diretório para buscar PDFs
        
    Returns:
        Lista de caminhos para arquivos PDF
    """
    pdf_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(Path(root) / file)
    
    return pdf_files


def process_all_documents(directory: Path = DOCUMENTS_DIR) -> Generator[dict, None, None]:
    """
    Processa todos os PDFs de um diretório, gerando chunks.
    
    Args:
        directory: Diretório com os documentos
        
    Yields:
        Chunks com content e metadata
    """
    pdf_files = get_all_pdfs(directory)
    chunking_mode = "SEMÂNTICO (spaCy)" if USE_SEMANTIC_CHUNKING else "LEGADO (caracteres)"
    
    print(f"📁 Encontrados {len(pdf_files)} arquivos PDF")
    print(f"🔧 Modo de chunking: {chunking_mode}")
    logger.info(f"Iniciando processamento: {len(pdf_files)} PDFs, modo={chunking_mode}")
    
    if USE_SEMANTIC_CHUNKING:
        print(f"   └─ max_chunk={CHUNK_SIZE}, min_chunk={MIN_CHUNK_SIZE}, overlap_sentences={CHUNK_OVERLAP_SENTENCES}")
    
    total_chunks = 0
    
    for i, pdf_path in enumerate(pdf_files, start=1):
        print(f"📄 [{i}/{len(pdf_files)}] Processando: {pdf_path.name}")
        
        try:
            chunks = process_pdf(pdf_path)
            total_chunks += len(chunks)
            print(f"   ✂️ Gerados {len(chunks)} chunks")
            logger.info(f"Processado {pdf_path.name}: {len(chunks)} chunks")
            
            for chunk in chunks:
                yield chunk
                
        except Exception as e:
            print(f"   ❌ Erro ao processar {pdf_path.name}: {e}")
            logger.error(f"Erro ao processar {pdf_path.name}: {e}")
            continue
    
    print(f"\n✅ Total: {total_chunks} chunks gerados de {len(pdf_files)} arquivos")
    logger.info(f"Processamento concluído: {total_chunks} chunks de {len(pdf_files)} arquivos")


def get_document_stats(directory: Path = DOCUMENTS_DIR) -> dict:
    """
    Retorna estatísticas sobre os documentos no diretório.
    
    Args:
        directory: Diretório com os documentos
        
    Returns:
        Dict com estatísticas
    """
    pdf_files = get_all_pdfs(directory)
    
    total_pages = 0
    total_size = 0
    
    for pdf_path in pdf_files:
        total_size += pdf_path.stat().st_size
        
        try:
            with open(pdf_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                total_pages += len(reader.pages)
        except:
            pass
    
    return {
        "total_files": len(pdf_files),
        "total_pages": total_pages,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "files": [p.name for p in pdf_files]
    }
