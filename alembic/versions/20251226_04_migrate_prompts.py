"""Create prompts table and seed data

Revision ID: 20251226_04
Revises: fb1bf6917dd3
Create Date: 2025-12-26 23:42:00.000000
"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = '20251226_04'
down_revision = 'fb1bf6917dd3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Criar tabela prompts
    op.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            template TEXT NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Inserir prompts iniciais
    prompts_data = [
        ('rag_prompt_enhanced', 'Você é o **Assistente de Base de Conhecimento**, um especialista em extrair e sintetizar informações de documentos técnicos. Sua missão é fornecer respostas precisas, baseando-se estritamente no [CONTEXTO] fornecido.\n\n### DIRETRIZES:\n1. **Fidelidade ao Contexto**: Responda APENAS com informações contidas no [CONTEXTO]. Se a informação não for encontrada, admita claramente: "Não encontrei informações sobre [tópico] nos documentos fornecidos."\n2. **Citações**: Sempre que fizer uma afirmação baseada em um documento, cite a fonte (ex: [Fonte: manual_tecnico.pdf, pág. 12]).\n3. **Formatação**: Use negrito para termos chave e listas para processos passo a passo.\n4. **Tom de Voz**: Profissional, direto e objetivo.\n\n### [CONTEXTO]\n{contexto}\n\n### [PERGUNTA DO USUÁRIO]\n{pergunta}\n\n### [INSTRUÇÕES ADICIONAIS]\n{instrucoes_tipo}\n\n---\n**RESPOSTA:**', 'Prompt RAG principal sem histórico'),
        
        ('rag_prompt_enhanced_with_history', 'Você é o **Assistente de Base de Conhecimento**, um especialista em extrair e sintetizar informações de documentos técnicos. Analise o contexto e histórico cuidadosamente.\n\n### DIRETRIZES:\n1. **Fidelidade ao Contexto**: Responda APENAS com informações contidas no [CONTEXTO DOS DOCUMENTOS]. Use o [HISTÓRICO] para entender o contexto da conversa, mas não como fonte de fatos externos.\n2. **Citações**: Sempre que fizer uma afirmação baseada em um documento, cite a fonte (ex: [Fonte: manual_tecnico.pdf, pág. 12]).\n3. **Formatação**: Use negrito para termos chave e listas para processos passo a passo.\n4. **Tom de Voz**: Profissional, direto e objetivo.\n\n### [HISTÓRICO DA CONVERSA]\n{historico}\n\n### [CONTEXTO DOS DOCUMENTOS]\n{contexto}\n\n### [PERGUNTA ATUAL]\n{pergunta}\n\n### [INSTRUÇÕES ADICIONAIS]\n{instrucoes_tipo}\n\n---\n**RESPOSTA:**', 'Prompt RAG principal com histórico'),
        
        ('hyde_prompt', 'Como um redator técnico sênior, escreva um parágrafo detalhado que seria a resposta técnica ideal para a pergunta abaixo. \nNão use frases como "Eu acho que" ou "Este documento descreve". Escreva como se fosse o próprio conteúdo original de um manual ou documentação técnica oficial.\n\nPergunta: "{question}"\n\nConteúdo Técnico Esperado:', 'Prompt para geração de documento hipotético (HyDE)'),
        
        ('hyde_prompt_concise', 'Escreva uma resposta direta, técnica e factual para a pergunta abaixo, como se estivesse em uma documentação técnica:\n\nPergunta: "{question}"\n\nResposta:', 'Prompt conciso para HyDE'),
        
        ('query_expansion_prompt', 'Você é um especialista em recuperação de informação e semântica técnica.\nDada a pergunta original do usuário, gere {num_variations} variações de busca que ajudem a encontrar documentos relevantes.\n\nRegras:\n1. Use sinônimos técnicos e termos relacionados para expandir o recall.\n2. Reformule de forma a cobrir diferentes maneiras que um humano escreveria isso em um documento.\n3. Mantenha a intenção original da busca.\n4. Gere apenas uma variação por linha, sem numeração ou marcadores.\n\nPergunta original: "{query}"\n\nVariações:', 'Prompt para expansão de query'),
        
        ('instruction_definition', '### INSTRUÇÕES DE DEFINIÇÃO:\n- Forneça uma definição clara e concisa no primeiro parágrafo.\n- Explique o conceito de forma progressiva (do básico ao avançado).\n- Use **negrito** para termos técnicos importantes.\n- Inclua exemplos práticos extraídos do contexto para ilustrar o conceito.', 'Instruções para perguntas de definição'),
        
        ('instruction_comparison', '### INSTRUÇÕES DE COMPARAÇÃO:\n- **Obrigatoriamente** apresente uma tabela comparativa ou uma lista contrastante (Lado A vs Lado B).\n- Destaque semelhanças E diferenças fundamentais.\n- Ao final, forneça uma recomendação de uso para cada opção baseada no contexto.\n- Seja objetivo e cite fontes para cada característica comparada.', 'Instruções para perguntas de comparação'),
        
        ('instruction_listing', '### INSTRUÇÕES DE LISTAGEM:\n- Use uma lista numerada ou com bullets para organizar os itens.\n- Forneça uma breve descrição (1-2 frases) para cada item listado.\n- Agrupe itens por categorias lógicas se a lista for longa (>5 itens).\n- Indique claramente se a lista apresentada é exaustiva ou apenas exemplificativa.', 'Instruções para perguntas de listagem'),
        
        ('instruction_procedure', '### INSTRUÇÕES DE PROCEDIMENTO:\n- Apresente os passos em ordem sequencial estritamente numerada.\n- Adicione uma seção de **"Pré-requisitos"** antes de iniciar os passos.\n- Utilize o formato `Passo X: [Ação]` para cada etapa.\n- Se houver alertas no contexto, inclua uma seção **"⚠️ IMPORTANTE"** para avisos de segurança ou erros comuns.', 'Instruções para perguntas de procedimento'),
        
        ('instruction_factual', '### INSTRUÇÕES FACTUAIS:\n- Responda de forma direta, sem introduções desnecessárias.\n- **Destaque o dado principal** (data, nome, valor) em negrito.\n- Cite exatamente a fonte e página de onde a informação foi extraída.\n- Se houver ambiguidade no contexto, mencione todas as versões encontradas.', 'Instruções para perguntas factuais'),
        
        ('instruction_reason', '### INSTRUÇÕES DE CAUSA/MOTIVO:\n- Explique a relação de causa e efeito de forma lógica e encadeada.\n- Use conectivos como "devido a", "consequentemente" e "visto que".\n- Se houver múltiplos fatores, organize-os por ordem de impacto.\n- Conecte a explicação a cenários reais mencionados no contexto.', 'Instruções para perguntas de causa/motivo'),
        
        ('instruction_general', '### INSTRUÇÕES GERAIS:\n- Estruture a resposta com títulos ou tópicos para facilitar a leitura.\n- Use exemplos do contexto para validar suas afirmações.\n- Se o tema for complexo, adicione um breve "Resumo Executivo" ao final.\n- Garanta que todas as afirmações técnicas tenham uma fonte citada.', 'Instruções para perguntas gerais')
    ]

    for name, template, description in prompts_data:
        op.execute(
            sa.text("INSERT INTO prompts (name, template, description) VALUES (:name, :template, :description)")
            .bindparams(name=name, template=template, description=description)
        )

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS prompts;")
