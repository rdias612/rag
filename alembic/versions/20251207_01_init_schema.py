"""Initial schema for documentos with pgvector and collection support

Revision ID: 20251207_01
Revises: 
Create Date: 2025-12-07
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251207_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensão pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Tabela principal
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documentos (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB,
            embedding VECTOR(768),
            collection_id VARCHAR(100) DEFAULT 'default',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Índices
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
        ON documentos 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documentos_collection 
        ON documentos (collection_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documentos_collection;")
    op.execute("DROP INDEX IF EXISTS idx_documentos_embedding;")
    op.execute("DROP TABLE IF EXISTS documentos;")
    # Não removemos a extensão vector para evitar afetar outros objetos
