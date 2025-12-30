"""Add adaptive_retrieval_metrics table

Revision ID: 20251230_01
Revises: 20251227_01_add_prompt_metadata
Create Date: 2025-12-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251230_01_add_adaptive_retrieval_metrics'
down_revision = '20251227_01_add_prompt_metadata'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela adaptive_retrieval_metrics
    op.create_table(
        'adaptive_retrieval_metrics',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String(100), nullable=True, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('complexity_score', sa.Integer(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('top_k_original', sa.Integer(), nullable=False),
        sa.Column('top_k_adjusted', sa.Integer(), nullable=False),
        sa.Column('min_similarity_original', sa.Float(), nullable=False),
        sa.Column('min_similarity_adjusted', sa.Float(), nullable=False),
        sa.Column('adjustment_reason', sa.String(255), nullable=True),
        sa.Column('characteristics', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        schema='public'
    )
    
    # Criar índices para consultas frequentes
    op.create_index(
        'idx_adaptive_metrics_created_at',
        'adaptive_retrieval_metrics',
        ['created_at'],
        schema='public'
    )
    
    op.create_index(
        'idx_adaptive_metrics_complexity',
        'adaptive_retrieval_metrics',
        ['complexity_score'],
        schema='public'
    )


def downgrade():
    # Remover índices
    op.drop_index('idx_adaptive_metrics_complexity', schema='public')
    op.drop_index('idx_adaptive_metrics_created_at', schema='public')
    
    # Remover tabela
    op.drop_table('adaptive_retrieval_metrics', schema='public')
