"""
Módulo de ingestão de documentos: leitura de PDFs e chunking.
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Generator

import pypdf

from src.config import DOCUMENTS_DIR, CHUNK_SIZE, CHUNK_OVERLAP


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
                pages.append({
                    "text": text.strip(),
                    "page": page_num
                })
    
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Divide um texto em chunks com overlap.
    
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
    print(f"📁 Encontrados {len(pdf_files)} arquivos PDF")
    
    for i, pdf_path in enumerate(pdf_files, start=1):
        print(f"📄 [{i}/{len(pdf_files)}] Processando: {pdf_path.name}")
        
        try:
            chunks = process_pdf(pdf_path)
            print(f"   ✂️ Gerados {len(chunks)} chunks")
            
            for chunk in chunks:
                yield chunk
                
        except Exception as e:
            print(f"   ❌ Erro ao processar {pdf_path.name}: {e}")
            continue


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
