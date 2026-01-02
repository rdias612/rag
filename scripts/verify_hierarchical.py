
import sys
import os
import logging
from pathlib import Path

# Adicionar root ao path
sys.path.append(str(Path(__file__).parent.parent))

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.data.ingestion import process_document
from src.data.database import insert_documents_batch, get_parent_content, search_similar
from src.core.embeddings import get_embedding
from src.core.rag import query_rag

def verify():
    test_file = Path('test_hierarchical.txt')
    logger.info(f"--- Verificando Ingestão de {test_file} ---")
    
    # 1. Processar documento
    chunks = process_document(test_file)
    logger.info(f"Gerados {len(chunks)} chunks no total.")
    
    parents = [c for c in chunks if c['metadata'].get('chunk_type') == 'parent']
    children = [c for c in chunks if c['metadata'].get('chunk_type') == 'child']
    
    logger.info(f"Chunks Pais: {len(parents)}")
    logger.info(f"Chunks Filhos: {len(children)}")
    
    if len(parents) == 0 or len(children) == 0:
        logger.error("ERRO: Hierarchical chunking não gerou pais ou filhos.")
        return
    
    # 2. Inserir no Banco (precisa de embeddings)
    logger.info("--- Gerando embeddings e inserindo no banco ---")
    texts = [c['content'] for c in chunks]
    from src.core.embeddings import get_embeddings_batch
    embeddings = get_embeddings_batch(texts)
    
    for chunk, emb in zip(chunks, embeddings):
        chunk['embedding'] = emb
        chunk['collection_id'] = 'test_hierarchical'
        
    success, msg = insert_documents_batch(chunks)
    if not success:
        logger.error(f"ERRO ao inserir no banco: {msg}")
        return
    logger.info("Inserção concluída com sucesso.")
    
    # 3. Testar Recuperação de Pai
    logger.info("--- Testando Recuperação de Contexto Expandido ---")
    child = children[0]
    parent_idx = child['metadata']['parent_index']
    source_path = child['metadata']['source_path']
    
    parent_text = get_parent_content(source_path, parent_idx)
    if parent_text:
        logger.info(f"SUCESSO: Conteúdo do pai recuperado ({len(parent_text)} chars).")
        logger.info(f"Snippet do pai: {parent_text[:100]}...")
    else:
        logger.error("ERRO: Não foi possível recuperar o conteúdo do pai.")
        
    # 4. Testar Pipeline RAG (End-to-End)
    logger.info("--- Testando Pipeline RAG (End-to-End) ---")
    question = "O que é o Sol?"
    response = query_rag(question, collection_id='test_hierarchical', debug_mode=True)
    
    logger.info(f"Pergunta: {question}")
    logger.info(f"Resposta: {response['answer'][:200]}...")
    
    # Verificar se o contexto usado foi expandido
    context_used = response.get('debug_info', {}).get('context_used', '')
    if 'CONTEÚDO EXPANDIDO' in context_used:
        logger.info("SUCESSO: O pipeline RAG usou o contexto expandido (Pai).")
    else:
        logger.warning("AVISO: 'CONTEÚDO EXPANDIDO' não encontrado no contexto usado. Verifique o log.")

if __name__ == "__main__":
    verify()
