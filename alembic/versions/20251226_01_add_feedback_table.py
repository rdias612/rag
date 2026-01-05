"""Add feedback table for quality loop

Revision ID: 20251226_01
Revises: 20251207_01
Create Date: 2025-12-26
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251226_01"
down_revision = "20251207_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabela de feedback
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(100),
            message_index INTEGER,
            rating INTEGER NOT NULL, -- 1 para positivo, 0 para negativo
            comment TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Índice para buscas rápidas por sessão
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feedback_session 
        ON feedback (session_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_feedback_session;")
    op.execute("DROP TABLE IF EXISTS feedback;")
