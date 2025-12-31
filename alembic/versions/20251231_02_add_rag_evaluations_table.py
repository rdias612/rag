"""add rag_evaluations table

Revision ID: 20251231_02
Revises: 20251231_01_create_question_type_instructions_table
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251231_02'
down_revision = '20251231_01_create_question_type_instructions_table'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rag_evaluations',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('context', sa.Text(), nullable=False),
        sa.Column('faithfulness', sa.Float(), nullable=True),
        sa.Column('answer_relevancy', sa.Float(), nullable=True),
        sa.Column('context_precision', sa.Float(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('evaluation_summary', sa.Text(), nullable=True),
        sa.Column('session_id', sa.String(36), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('chunks_retrieved', sa.Integer(), nullable=True),
        sa.Column('search_mode', sa.String(20), nullable=True),
        sa.Column('adaptive_used', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    
    # Índices para performance
    op.create_index('idx_evaluations_created', 'rag_evaluations', ['created_at'])
    op.create_index('idx_evaluations_score', 'rag_evaluations', ['overall_score'])
    op.create_index('idx_evaluations_session', 'rag_evaluations', ['session_id'])


def downgrade():
    op.drop_index('idx_evaluations_session', table_name='rag_evaluations')
    op.drop_index('idx_evaluations_score', table_name='rag_evaluations')
    op.drop_index('idx_evaluations_created', table_name='rag_evaluations')
    op.drop_table('rag_evaluations')
