"""Update embedding dimension to 1024

Revision ID: 20251226_03
Revises: 20251226_02
Create Date: 2025-12-26
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251226_03"
down_revision = "20251226_02"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Remover o índice de busca vetorial existente
    op.execute("DROP INDEX IF EXISTS idx_documentos_embedding;")

    # 2. Limpar a tabela documentos (opcional, mas recomendado para evitar conflito de dimensões no cast)
    op.execute("DELETE FROM documentos;")

    # 3. Alterar a coluna embedding para VECTOR(1024)
    op.execute("ALTER TABLE documentos ALTER COLUMN embedding TYPE VECTOR(1024);")

    # 4. Recriar o índice ivfflat
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
        ON documentos 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_documentos_embedding;")
    op.execute("DELETE FROM documentos;")
    op.execute("ALTER TABLE documentos ALTER COLUMN embedding TYPE VECTOR(768);")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_documentos_embedding 
        ON documentos 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
    )
