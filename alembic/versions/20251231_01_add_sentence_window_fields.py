"""Add sentence window retrieval fields

Revision ID: 20251231_01
Revises: 20251230_01_add_adaptive_retrieval_metrics
Create Date: 2025-12-31
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251231_01'
down_revision = '20251230_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar campos à tabela documentos para suporte a Sentence Window Retrieval
    op.execute("""
        ALTER TABLE documentos 
        ADD COLUMN IF NOT EXISTS chunk_type VARCHAR(20),
        ADD COLUMN IF NOT EXISTS sentence_index INTEGER,
        ADD COLUMN IF NOT EXISTS total_sentences INTEGER,
        ADD COLUMN IF NOT EXISTS char_start INTEGER,
        ADD COLUMN IF NOT EXISTS char_end INTEGER;
    """)
    
    # Criar índice para busca eficiente por chunk_type
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_chunk_type 
        ON documentos(chunk_type) 
        WHERE chunk_type IS NOT NULL;
    """)
    
    # Criar índice composto para busca por tipo e coleção
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_type_collection 
        ON documentos(chunk_type, collection_id) 
        WHERE chunk_type IS NOT NULL;
    """)
    
    # Criar índice para busca por sentence_index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_sentence_index 
        ON documentos (((metadata->>'sentence_index')::INTEGER)) 
        WHERE (metadata->>'sentence_index') IS NOT NULL;
    """)
    
    # Adicionar comentários aos novos campos
    op.execute("""
        COMMENT ON COLUMN documentos.chunk_type IS 'Tipo de chunk: parent, child ou sentence (para Sentence Window Retrieval)';
        COMMENT ON COLUMN documentos.sentence_index IS 'Índice da sentença no documento (para Sentence Window)';
        COMMENT ON COLUMN documentos.total_sentences IS 'Total de sentenças no documento';
        COMMENT ON COLUMN documentos.char_start IS 'Posição inicial do chunk no documento original';
        COMMENT ON COLUMN documentos.char_end IS 'Posição final do chunk no documento original';
    """)
    
    # Atualizar documentos existentes para marcar como hierarchical (parent/child)
    op.execute("""
        UPDATE documentos 
        SET chunk_type = 'child'
        WHERE chunk_type IS NULL 
          AND (metadata->>'chunk_index') IS NOT NULL;
    """)
    
    op.execute("""
        UPDATE documentos 
        SET chunk_type = 'parent'
        WHERE chunk_type IS NULL 
          AND (metadata->>'chunk_index') IS NOT NULL 
          AND (metadata->>'parent_index') IS NULL;
    """)


def downgrade() -> None:
    # Remover índices
    op.execute("DROP INDEX IF EXISTS idx_documentos_sentence_index;")
    op.execute("DROP INDEX IF EXISTS idx_documentos_type_collection;")
    op.execute("DROP INDEX IF EXISTS idx_documentos_chunk_type;")
    
    # Remover campos
    op.execute("""
        ALTER TABLE documentos 
        DROP COLUMN IF EXISTS chunk_type,
        DROP COLUMN IF EXISTS sentence_index,
        DROP COLUMN IF EXISTS total_sentences,
        DROP COLUMN IF EXISTS char_start,
        DROP COLUMN IF EXISTS char_end;
    """)
