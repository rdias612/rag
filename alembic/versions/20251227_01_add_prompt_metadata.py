"""Add prompt metadata fields (category, priority, tags, use_case)

Revision ID: 20251227_01
Revises: 20251226_04
Create Date: 2025-12-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251227_01'
down_revision = '20251226_04'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Adicionar novos campos à tabela prompts
    op.execute("""
        ALTER TABLE prompts 
        ADD COLUMN IF NOT EXISTS category VARCHAR(50),
        ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100,
        ADD COLUMN IF NOT EXISTS tags TEXT[],
        ADD COLUMN IF NOT EXISTS use_case TEXT,
        ADD COLUMN IF NOT EXISTS created_by VARCHAR(100) DEFAULT 'system',
        ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
    """)
    
    # 2. Criar índice em category para performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_prompts_category 
        ON prompts(category) 
        WHERE is_active = TRUE;
    """)
    
    # 3. Categorizar prompts existentes automaticamente
    
    # RAG prompts
    op.execute("""
        UPDATE prompts 
        SET category = 'rag_main',
            priority = 100,
            tags = ARRAY['default']
        WHERE name IN ('rag_prompt_enhanced', 'rag_prompt_enhanced_with_history')
          AND category IS NULL;
    """)
    
    # HyDE prompts
    op.execute("""
        UPDATE prompts 
        SET category = 'hyde',
            priority = 100,
            tags = ARRAY['default']
        WHERE name IN ('hyde_prompt', 'hyde_prompt_concise')
          AND category IS NULL;
    """)
    
    # Query expansion
    op.execute("""
        UPDATE prompts 
        SET category = 'query_expansion',
            priority = 100,
            tags = ARRAY['default']
        WHERE name = 'query_expansion_prompt'
          AND category IS NULL;
    """)
    
    # Instruções por tipo de pergunta
    op.execute("""
        UPDATE prompts 
        SET category = 'instruction',
            priority = 100,
            tags = ARRAY[REPLACE(name, 'instruction_', '')]::TEXT[],
            use_case = CONCAT('Instruções específicas para perguntas do tipo: ', REPLACE(name, 'instruction_', ''))
        WHERE name LIKE 'instruction_%'
          AND category IS NULL;
    """)

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_prompts_category;")
    op.execute("""
        ALTER TABLE prompts 
        DROP COLUMN IF EXISTS category,
        DROP COLUMN IF EXISTS priority,
        DROP COLUMN IF EXISTS tags,
        DROP COLUMN IF EXISTS use_case,
        DROP COLUMN IF EXISTS created_by,
        DROP COLUMN IF EXISTS version;
    """)
