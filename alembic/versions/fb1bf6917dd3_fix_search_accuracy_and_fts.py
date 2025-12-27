"""fix_search_accuracy_and_fts

Revision ID: fb1bf6917dd3
Revises: 20251226_03
Create Date: 2025-12-26 23:28:46.200431
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb1bf6917dd3'
down_revision = '20251226_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Trocar IVFFlat por HNSW (muito mais preciso e não precisa de rebuild constante)
    op.execute("DROP INDEX IF EXISTS idx_documentos_embedding;")
    op.execute(
        """
        CREATE INDEX idx_documentos_embedding 
        ON documentos 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
    )

    # 2. Corrigir Full-Text Search
    # Adicionar coluna
    op.execute("""
        ALTER TABLE documentos ADD COLUMN IF NOT EXISTS search_vector tsvector;
    """)
    
    # Criar índice GIN
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documentos_fts ON documentos USING GIN(search_vector);
    """)

    # Criar função de trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('portuguese', NEW.content);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Criar trigger
    op.execute("""
        DROP TRIGGER IF EXISTS trg_update_search_vector ON documentos;
        CREATE TRIGGER trg_update_search_vector
        BEFORE INSERT OR UPDATE ON documentos
        FOR EACH ROW
        EXECUTE FUNCTION update_search_vector();
    """)

    # Popular dados existentes
    op.execute("""
        UPDATE documentos SET search_vector = to_tsvector('portuguese', content)
        WHERE search_vector IS NULL;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_update_search_vector ON documentos;")
    op.execute("DROP FUNCTION IF EXISTS update_search_vector();")
    op.execute("DROP INDEX IF EXISTS idx_documentos_fts;")
    op.execute("ALTER TABLE documentos DROP COLUMN IF EXISTS search_vector;")
    
    op.execute("DROP INDEX IF EXISTS idx_documentos_embedding;")
    op.execute(
        """
        CREATE INDEX idx_documentos_embedding 
        ON documentos 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    )
