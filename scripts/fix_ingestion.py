
import sys
import logging
from pathlib import Path

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

path = Path('c:/GIT/rag/src/data/ingestion.py')
if not path.exists():
    logger.error(f'Error: {path} not found')
    sys.exit(1)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'def process_document(file_path: Path) -> list[dict]:'
end_marker = 'def get_all_pdfs('

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_func = """def process_document(file_path: Path) -> list[dict]:
    \"\"\"
    Processa um documento usando estratégia de Parent-Child Chunking.
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        Lista de chunks (filhos e pais) com metadados estruturados
    \"\"\"
    # Obter extrator apropriado
    extractor = get_extractor_for_file(file_path)
    pages = extractor(file_path)
    
    # Unificar texto para chunking hierárquico (preservando estrutura)
    full_text = "\\n\\n".join([p["text"] for p in pages])
    
    base_metadata = {
        "source": file_path.name,
        "source_path": str(file_path),
        "file_type": file_path.suffix.lower(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Gerar chunks hierárquicos
    parent_chunks, child_chunks = create_parent_child_chunks(
        full_text,
        base_metadata,
        parent_size=PARENT_CHUNK_SIZE,
        child_size=CHILD_CHUNK_SIZE,
        child_overlap=CHILD_CHUNK_OVERLAP
    )
    
    # 1. Processar Chunks Pais
    for i, p in enumerate(parent_chunks):
        p["metadata"]["chunk_index"] = i
        p["metadata"]["page"] = 1
        
    # 2. Processar Chunks Filhos
    for i, c in enumerate(child_chunks):
        c["metadata"]["chunk_index"] = i
        c["metadata"]["page"] = 1
        
        # Enriquecer filhos com possíveis títulos de seção se encontrados no pai
        parent_idx = c["metadata"]["parent_index"]
        if 0 <= parent_idx < len(parent_chunks):
            parent_text = parent_chunks[parent_idx]["content"]
            lines = parent_text.split('\\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line) < 100 and len(first_line) > 3:
                    if first_line.isupper() or first_line.endswith(':'):
                        c["metadata"]["possible_section"] = first_line
            
    # Retornar ambos para inserção no banco
    return parent_chunks + child_chunks


"""
    new_content = content[:start_idx] + new_func + content[end_idx:]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    logger.info('Successfully updated ingestion.py')
else:
    logger.error(f'Error: Markers not found. start={start_idx}, end={end_idx}')
    sys.exit(1)
