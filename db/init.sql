-- ============================================================================
-- Script de inicialização do banco de dados RAG
-- Executar após criar o banco 'ragdb'
-- ============================================================================

-- Habilitar extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabela principal de documentos
CREATE TABLE IF NOT EXISTS documentos (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(768),  -- Dimensão do Nomic Embed v1.5
    search_vector TSVECTOR, -- Para Full-Text Search (busca híbrida)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para busca vetorial (IVFFlat - bom para datasets médios)
-- O parâmetro 'lists' deve ser ajustado conforme o tamanho do dataset
-- Regra geral: lists = sqrt(número de registros)
CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
ON documentos 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Índice GIN para Full-Text Search (busca por palavras-chave)
CREATE INDEX IF NOT EXISTS idx_documentos_fts 
ON documentos 
USING gin(search_vector);

-- Índice para busca por metadata (opcional, útil para filtros)
CREATE INDEX IF NOT EXISTS idx_documentos_metadata 
ON documentos 
USING gin (metadata);

-- Índice para busca por data (opcional)
CREATE INDEX IF NOT EXISTS idx_documentos_created_at 
ON documentos (created_at DESC);

-- ============================================================================
-- Trigger para atualizar automaticamente o search_vector
-- ============================================================================

-- Função que atualiza o search_vector
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('portuguese', NEW.content);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger que chama a função antes de INSERT ou UPDATE
DROP TRIGGER IF EXISTS trg_update_search_vector ON documentos;
CREATE TRIGGER trg_update_search_vector
BEFORE INSERT OR UPDATE ON documentos
FOR EACH ROW
EXECUTE FUNCTION update_search_vector();

-- ============================================================================
-- Queries úteis para debug e manutenção
-- ============================================================================

-- Contar documentos
-- SELECT COUNT(*) FROM documentos;

-- Ver últimos documentos inseridos
-- SELECT id, LEFT(content, 100), metadata->>'source', created_at 
-- FROM documentos 
-- ORDER BY created_at DESC 
-- LIMIT 10;

-- Buscar por fonte específica
-- SELECT * FROM documentos WHERE metadata->>'source' = 'nome_do_arquivo.pdf';

-- Limpar todos os documentos (CUIDADO!)
-- TRUNCATE TABLE documentos RESTART IDENTITY;
