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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para busca vetorial (IVFFlat - bom para datasets médios)
-- O parâmetro 'lists' deve ser ajustado conforme o tamanho do dataset
-- Regra geral: lists = sqrt(número de registros)
CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
ON documentos 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Índice para busca por metadata (opcional, útil para filtros)
CREATE INDEX IF NOT EXISTS idx_documentos_metadata 
ON documentos 
USING gin (metadata);

-- Índice para busca por data (opcional)
CREATE INDEX IF NOT EXISTS idx_documentos_created_at 
ON documentos (created_at DESC);

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
