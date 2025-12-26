"""Add ingestion control table

Revision ID: 20251226_02
Revises: 20251226_01
Create Date: 2025-12-26
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251226_02"
down_revision = "20251226_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela de controle de ingestão
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS documentos_ingeridos (
            id SERIAL PRIMARY KEY,
            file_path TEXT NOT NULL UNIQUE,
            file_hash VARCHAR(64) NOT NULL,
            file_size BIGINT NOT NULL,
            collection_id VARCHAR(100) DEFAULT 'default',
            chunks_count INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'success',
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Índices
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documentos_ingeridos_collection 
        ON documentos_ingeridos (collection_id);
        """
    )
    
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documentos_ingeridos_hash 
        ON documentos_ingeridos (file_hash);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documentos_ingeridos_hash;")
    op.execute("DROP INDEX IF EXISTS idx_documentos_ingeridos_collection;")
    op.execute("DROP TABLE IF EXISTS documentos_ingeridos;")
