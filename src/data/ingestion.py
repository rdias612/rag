"""
Módulo de ingestão de documentos: leitura de múltiplos formatos e chunking.

Formatos suportados:
- PDF (.pdf)
- Word (.docx)
- Texto (.txt)
- Markdown (.md)
- HTML (.html, .htm)
- CSV (.csv)
"""
import os
import re
import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Generator, Callable

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


# =============================================================================
# Formatos suportados
# =============================================================================
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".csv"}


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


def extract_text_from_docx(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo Word (.docx).
    
    Args:
        file_path: Caminho para o arquivo .docx
        
    Returns:
        Lista de dicts com text (documento inteiro, page=1)
    """
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx não instalado. Execute: pip install python-docx")
        raise ImportError("python-docx é necessário para processar arquivos .docx")
    
    doc = Document(file_path)
    
    # Extrair texto de todos os parágrafos
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    
    # Extrair texto de tabelas também
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                paragraphs.append(row_text)
    
    full_text = "\n\n".join(paragraphs)
    
    if not full_text.strip():
        return []
    
    return [{"text": full_text, "page": 1}]


def extract_text_from_txt(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo de texto plano (.txt).
    
    Args:
        file_path: Caminho para o arquivo .txt
        
    Returns:
        Lista de dicts com text (arquivo inteiro, page=1)
    """
    # Tentar diferentes encodings
    encodings = ["utf-8", "latin-1", "cp1252"]
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        logger.error(f"Não foi possível decodificar {file_path}")
        return []
    
    if not text.strip():
        return []
    
    return [{"text": text.strip(), "page": 1}]


def extract_text_from_markdown(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo Markdown (.md).
    Converte para HTML e depois extrai texto limpo.
    
    Args:
        file_path: Caminho para o arquivo .md
        
    Returns:
        Lista de dicts com text (arquivo inteiro, page=1)
    """
    try:
        import markdown
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("markdown ou beautifulsoup4 não instalado")
        raise ImportError("markdown e beautifulsoup4 são necessários para processar arquivos .md")
    
    # Ler arquivo markdown
    with open(file_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # Converter para HTML
    html = markdown.markdown(md_content, extensions=["tables", "fenced_code"])
    
    # Extrair texto limpo do HTML
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n\n")
    
    # Limpar múltiplas quebras de linha
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    if not text.strip():
        return []
    
    return [{"text": text.strip(), "page": 1}]


def extract_text_from_html(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo HTML (.html, .htm).
    
    Args:
        file_path: Caminho para o arquivo HTML
        
    Returns:
        Lista de dicts com text (arquivo inteiro, page=1)
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 não instalado. Execute: pip install beautifulsoup4")
        raise ImportError("beautifulsoup4 é necessário para processar arquivos HTML")
    
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remover scripts e styles
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
    
    # Extrair texto
    text = soup.get_text(separator="\n\n")
    
    # Limpar múltiplas quebras de linha e espaços
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    
    if not text.strip():
        return []
    
    return [{"text": text.strip(), "page": 1}]


def extract_text_from_csv(file_path: Path) -> list[dict]:
    """
    Extrai texto de um arquivo CSV (.csv).
    Converte a tabela para formato Markdown para preservar a estrutura.
    
    Args:
        file_path: Caminho para o arquivo .csv
        
    Returns:
        Lista de dicts com text (arquivo inteiro, page=1)
    """
    # Tentar diferentes encodings
    encodings = ["utf-8", "latin-1", "cp1252"]
    
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding, newline="") as f:
                # Detectar delimitador automaticamente
                sample = f.read(4096)
                f.seek(0)
                
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel  # Fallback para delimitador padrão (,)
                
                reader = csv.reader(f, dialect)
                rows = list(reader)
            break
        except UnicodeDecodeError:
            continue
    else:
        logger.error(f"Não foi possível decodificar {file_path}")
        return []
    
    if not rows:
        return []
    
    # Converter para formato Markdown
    headers = rows[0]
    data_rows = rows[1:]
    
    # Construir tabela Markdown
    lines = []
    
    # Header
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Data rows
    for row in data_rows:
        # Garantir que a linha tenha o mesmo número de colunas que o header
        padded_row = row + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(padded_row[:len(headers)]) + " |")
    
    text = "\n".join(lines)
    
    if not text.strip():
        return []
    
    return [{"text": text.strip(), "page": 1}]


def get_extractor_for_file(file_path: Path) -> Callable[[Path], list[dict]]:
    """
    Retorna a função extratora apropriada para o tipo de arquivo.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        Função extratora de texto
        
    Raises:
        ValueError: Se o formato não for suportado
    """
    ext = file_path.suffix.lower()
    
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".txt": extract_text_from_txt,
        ".md": extract_text_from_markdown,
        ".html": extract_text_from_html,
        ".htm": extract_text_from_html,
        ".csv": extract_text_from_csv,
    }
    
    if ext not in extractors:
        raise ValueError(f"Formato não suportado: {ext}. Formatos válidos: {', '.join(extractors.keys())}")
    
    return extractors[ext]


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
    Processa um documento de qualquer formato suportado: extrai texto e divide em chunks.
    
    Formatos suportados: .pdf, .docx, .txt, .md, .html, .htm
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista de chunks com content e metadata enriquecido (Contextual Chunking)
    """
    # Obter extrator apropriado
    extractor = get_extractor_for_file(file_path)
    pages = extractor(file_path)
    
    # 1. Gerar todos os chunks brutos primeiro
    raw_chunks = []
    global_chunk_index = 0
    
    for page_data in pages:
        chunks = chunk_text(page_data["text"])
        
        for chunk in chunks:
            raw_chunks.append({
                "content": chunk,
                "metadata": {
                    "source": file_path.name,
                    "source_path": str(file_path),
                    "file_type": file_path.suffix.lower(),
                    "page": page_data["page"],
                    "chunk_index": global_chunk_index,
                    "timestamp": datetime.now().isoformat()
                }
            })
            global_chunk_index += 1
            
    # 2. Enriquecer com contexto (Contextual Chunking)
    enriched_chunks = []
    total_chunks = len(raw_chunks)
    
    for i, chunk_data in enumerate(raw_chunks):
        metadata = chunk_data["metadata"]
        
        # Adicionar contexto do chunk anterior e posterior
        # Limitamos o tamanho para não explodir o metadata
        if i > 0:
            prev_content = raw_chunks[i-1]["content"]
            metadata["prev_chunk_text"] = prev_content[-500:] # Últimos 500 chars
        else:
            metadata["prev_chunk_text"] = None
            
        if i < total_chunks - 1:
            next_content = raw_chunks[i+1]["content"]
            metadata["next_chunk_text"] = next_content[:500] # Primeiros 500 chars
        else:
            metadata["next_chunk_text"] = None
            
        # Tentar identificar possível título de seção (heurística simples)
        # Pega a primeira linha se for curta e parecer um título
        lines = chunk_data["content"].split('\n')
        if lines:
            first_line = lines[0].strip()
            # Heurística: linha curta, não termina com pontuação comum de frase (exceto :)
            if len(first_line) < 100 and len(first_line) > 3:
                if first_line.isupper() or first_line.endswith(':'):
                    metadata["possible_section"] = first_line
                elif len(lines) > 1 and lines[1].strip() == "": # Linha isolada
                    metadata["possible_section"] = first_line

        enriched_chunks.append(chunk_data)
    
    return enriched_chunks


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


def process_all_documents(directory: Path = DOCUMENTS_DIR) -> Generator[dict, None, None]:
    """
    Processa todos os documentos suportados de um diretório, gerando chunks.
    
    Formatos suportados: .pdf, .docx, .txt, .md, .html, .htm
    
    Args:
        directory: Diretório com os documentos
        
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
    
    print(f"📁 Encontrados {len(document_files)} documentos")
    for ext, count in sorted(files_by_type.items()):
        print(f"   └─ {ext}: {count} arquivo(s)")
    print(f"🔧 Modo de chunking: {chunking_mode}")
    logger.info(f"Iniciando processamento: {len(document_files)} documentos, modo={chunking_mode}")
    
    if USE_SEMANTIC_CHUNKING:
        print(f"   └─ max_chunk={CHUNK_SIZE}, min_chunk={MIN_CHUNK_SIZE}, overlap_sentences={CHUNK_OVERLAP_SENTENCES}")
    
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
            
        print(f"📄 [{i}/{len(document_files)}] Processando: {doc_path.name} (Coleção: {collection_id})")
        
        try:
            chunks = process_document(doc_path)
            total_chunks += len(chunks)
            print(f"   ✂️ Gerados {len(chunks)} chunks")
            logger.info(f"Processado {doc_path.name}: {len(chunks)} chunks (Coleção: {collection_id})")
            
            for chunk in chunks:
                # Adicionar collection_id ao chunk
                chunk["collection_id"] = collection_id
                yield chunk
                
        except Exception as e:
            print(f"   ❌ Erro ao processar {doc_path.name}: {e}")
            logger.error(f"Erro ao processar {doc_path.name}: {e}")
            continue
    
    print(f"\n✅ Total: {total_chunks} chunks gerados de {len(document_files)} arquivos")
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
    
    total_pages = 0
    total_size = 0
    files_by_type = {}
    
    for doc_path in document_files:
        ext = doc_path.suffix.lower()
        files_by_type[ext] = files_by_type.get(ext, 0) + 1
        total_size += doc_path.stat().st_size
        
        # Contar páginas apenas para PDFs
        if ext == ".pdf":
            try:
                with open(doc_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    total_pages += len(reader.pages)
            except:
                pass
    
    return {
        "total_files": len(document_files),
        "files_by_type": files_by_type,
        "total_pdf_pages": total_pages,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "supported_formats": list(SUPPORTED_EXTENSIONS),
        "files": [p.name for p in document_files]
    }
