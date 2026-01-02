"""Add chunking_type to documentos_ingeridos table

Revision ID: 20260102_01
Revises: 20251231_02
Create Date: 2026-01-02
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260102_01'
down_revision = '20251231_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adicionar campo chunking_type à tabela documentos_ingeridos
    op.execute("""
        ALTER TABLE documentos_ingeridos 
        ADD COLUMN IF NOT EXISTS chunking_type VARCHAR(20);
    """)
    
    # Criar índice para consultas eficientes por chunking_type
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_ingeridos_chunking_type 
        ON documentos_ingeridos (chunking_type)
        WHERE chunking_type IS NOT NULL;
    """)
    
    # Criar índice composto para busca por tipo e coleção
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_ingeridos_type_collection 
        ON documentos_ingeridos (chunking_type, collection_id)
        WHERE chunking_type IS NOT NULL;
    """)
    
    # Adicionar comentários ao campo
    op.execute("""
        COMMENT ON COLUMN documentos_ingeridos.chunking_type IS 
        'Tipo de chunking usado na ingestão: hierarchical (parent-child), sentence (sentence window), ou NULL (legado)';
    """)
    
    # Migrar dados existentes - inferir tipo baseado nos chunks
    # Se encontrar chunks com chunk_type='sentence', marca como sentence
    # Se encontrar chunks com chunk_type IN ('parent', 'child'), marca como hierarchical
    op.execute("""
        UPDATE documentos_ingeridos di
        SET chunking_type = CASE
            WHEN EXISTS (
                SELECT 1 FROM documentos d
                WHERE d.metadata->>'source_path' = di.file_path
                AND d.metadata->>'chunk_type' = 'sentence'
                LIMIT 1
            ) THEN 'sentence'
            WHEN EXISTS (
                SELECT 1 FROM documentos d
                WHERE d.metadata->>'source_path' = di.file_path
                AND d.metadata->>'chunk_type' IN ('parent', 'child')
                LIMIT 1
            ) THEN 'hierarchical'
            ELSE NULL
        END
        WHERE chunking_type IS NULL;
    """)


def downgrade() -> None:
    # Remover índices
    op.execute("DROP INDEX IF EXISTS idx_documentos_ingeridos_type_collection;")
    op.execute("DROP INDEX IF EXISTS idx_documentos_ingeridos_chunking_type;")
    
    # Remover campo
    op.execute("""
        ALTER TABLE documentos_ingeridos 
        DROP COLUMN IF EXISTS chunking_type;
    """)
