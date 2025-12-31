"""Create question_type_instructions table with few-shot examples

Revision ID: 20251231_01
Revises: 20251230_01_add_sentence_window_fields
Create Date: 2025-12-31

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20251231_01'
down_revision = '20251230_01_add_sentence_window_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela
    op.create_table(
        'question_type_instructions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('question_type', sa.String(50), nullable=False, unique=True),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )
    
    # Índice para busca rápida
    op.create_index(
        'idx_qti_question_type',
        'question_type_instructions',
        ['question_type']
    )
    
    # Inserir dados (instruções com exemplos few-shot)
    op.execute("""
        INSERT INTO question_type_instructions (question_type, template, description, is_active, version) VALUES
        ('definition', 
        '### INSTRUÇÕES DE DEFINIÇÃO:
- Forneça uma definição clara e concisa no primeiro parágrafo.
- Explique o conceito de forma progressiva (do básico ao avançado).
- Use **negrito** para termos técnicos importantes.
- Inclua exemplos práticos extraídos do contexto para ilustrar o conceito.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "O que é uma API REST?"
Resposta: Uma **API REST** (Representational State Transfer) é um estilo arquitetural para sistemas distribuídos que utiliza os métodos HTTP padrão (GET, POST, PUT, DELETE) para operações. Pense na REST como uma linguagem universal para comunicação entre sistemas: qualquer serviço que entenda REST pode conversar com qualquer outro. No contexto da empresa, a API REST do sistema de vendas permite que o aplicativo mobile consulte produtos em tempo real usando apenas requisições HTTP.

**Exemplo 2:**
Pergunta: "O que significa Docker?"
Resposta: **Docker** é uma plataforma de contêinerização que permite empacotar uma aplicação com todas as suas dependências em uma unidade portátil chamada contêiner. O contêiner é como uma "caixa" que contém tudo o que a aplicação precisa: código, bibliotecas, configurações e sistema operacional. Isso elimina o problema clássico "funciona na minha máquina" pois o ambiente é idêntico em qualquer lugar. Na nossa empresa, usamos Docker para garantir que a aplicação funcione da mesma forma no laptop dos desenvolvedores, em staging e em produção.

---

Agora responda seguindo este formato:', 
        'Instruções para perguntas de definição/explicação com exemplos few-shot', 
        TRUE, 
        1),
        
        ('comparison',
        '### INSTRUÇÕES DE COMPARAÇÃO:
- **Obrigatoriamente** apresente uma tabela comparativa ou uma lista contrastante (Lado A vs Lado B).
- Destaque semelhanças E diferenças fundamentais.
- Ao final, forneça uma recomendação de uso para cada opção baseada no contexto.
- Seja objetivo e cite fontes para cada característica comparada.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "Qual a diferença entre PostgreSQL e MongoDB?"
Resposta: | Característica | PostgreSQL | MongoDB |
|----------------|------------|---------|
| **Tipo** | Banco Relacional (SQL) | Banco de Documentos (NoSQL) |
| **Estrutura** | Tabelas fixas com schema | Documentos JSON flexíveis |
| **Transações** | ACID completo | Multi-document ACID (versão 4.0+) |
| **Escalabilidade** | Vertical principalmente | Horizontal (sharding) |
| **Consultas** | SQL complexo, joins | Query API, agregações |

**Recomendação:** Use PostgreSQL para dados financeiros e transacionais (sistema de pagamentos). Use MongoDB para logs, catálogos de produtos e dados com estrutura variável.

**Exemplo 2:**
Pergunta: "Diferença entre desenvolvimento monolítico e microserviços?"
Resposta: **Monolítico:**
- Único deployment para toda a aplicação
- Acoplamento forte entre componentes
- Mais simples para pequenas equipes
- Dificuldade de escalar partes específicas

**Microserviços:**
- Cada serviço é deployado independentemente
- Baixo acoplamento, alta coesão
- Requer mais infraestrutura (CI/CD, monitoramento)
- Permite escalar apenas serviços sobrecarregados

**Recomendação:** Comece com monolítico para MVPs e projetos simples. Migre para microserviços quando houver equipes independentes e requisitos de escalabilidade diferenciada por componente.

---

Agora responda seguindo este formato:',
        'Instruções para perguntas comparativas com exemplos few-shot',
        TRUE,
        1),
        
        ('listing',
        '### INSTRUÇÕES DE LISTAGEM:
- Use uma lista numerada ou com bullets para organizar os itens.
- Forneça uma breve descrição (1-2 frases) para cada item listado.
- Agrupe itens por categorias lógicas se a lista for longa (>5 itens).
- Indique claramente se a lista apresentada é exaustiva ou apenas exemplificativa.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "Quais são os tipos de testes de software?"
Resposta: **1. Unitários:** Testam funções isoladas de código (ex: testar cálculo de imposto individualmente).
**2. Integração:** Verificam comunicação entre componentes (ex: API + banco de dados).
**3. E2E (End-to-End):** Testam fluxos completos do usuário (ex: checkout completo em e-commerce).
**4. Performance:** Avaliam velocidade e carga do sistema (ex: 1000 requisições simultâneas).

*Esta lista inclui os principais tipos, mas existem variações como testes de aceitação e smoke tests.*

**Exemplo 2:**
Pergunta: "Quais tecnologias usamos no projeto?"
Resposta: **Backend:**
- Python 3.11 com FastAPI
- PostgreSQL para banco de dados
- Redis para cache

**Frontend:**
- React 18 com TypeScript
- Tailwind CSS para estilização

**Infraestrutura:**
- Docker para containerização
- Kubernetes para orquestração
- AWS como provedor cloud

---

Agora responda seguindo este formato:',
        'Instruções para perguntas de listagem/enumeração com exemplos few-shot',
        TRUE,
        1),
        
        ('procedure',
        '### INSTRUÇÕES DE PROCEDIMENTO:
- Apresente os passos em ordem sequencial estritamente numerada.
- Adicione uma seção de **"Pré-requisitos"** antes de iniciar os passos.
- Utilize o formato `Passo X: [Ação]` para cada etapa.
- Se houver alertas no contexto, inclua uma seção **"⚠️ IMPORTANTE"** para avisos de segurança ou erros comuns.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "Como funciona o processo de autenticação JWT?"
Resposta: **Pré-requisitos:**
- Usuário deve possuir credenciais válidas (email/senha)
- Servidor deve ter a chave secreta JWT configurada

**Passo 1:** O cliente envia as credenciais (email/senha) para o endpoint `/api/login`
**Passo 2:** O servidor valida as credenciais no banco de dados
**Passo 3:** Se válidas, o servidor gera um token JWT contendo: user_id, email, exp (tempo de expiração)
**Passo 4:** O servidor assina o token com a chave secreta e retorna ao cliente
**Passo 5:** O cliente armazena o token (localStorage, cookie, etc.)
**Passo 6:** Em requisições subsequentes, o cliente envia o token no header `Authorization: Bearer {token}`
**Passo 7:** O servidor valida a assinatura e expiração do token
**Passo 8:** Se válido, o servidor autoriza o acesso e processa a requisição

**⚠️ IMPORTANTE:** O token deve ser enviado via HTTPS para evitar interceptação. Tokens expiram após um período definido (ex: 24 horas).

---

Agora responda seguindo este formato:',
        'Instruções para perguntas de procedimento/processo com exemplos few-shot',
        TRUE,
        1),
        
        ('factual',
        '### INSTRUÇÕES FACTUAIS:
- Responda de forma direta, sem introduções desnecessárias.
- **Destaque o dado principal** (data, nome, valor) em negrito.
- Cite exatamente a fonte e página de onde a informação foi extraída.
- Se houver ambiguidade no contexto, mencione todas as versões encontradas.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "Quando foi lançado o PostgreSQL 15?"
Resposta: O PostgreSQL 15 foi lançado em **14 de outubro de 2022**. Fonte: Documentação oficial PostgreSQL, Release Notes.

**Exemplo 2:**
Pergunta: "Quem criou o Docker?"
Resposta: O Docker foi criado por **Solomon Hykes** em 2013 como um projeto interno da empresa dotCloud. Fonte: Documentação Docker, "History" section.

---

Agora responda seguindo este formato:',
        'Instruções para perguntas factuais com exemplos few-shot',
        TRUE,
        1),
        
        ('reason',
        '### INSTRUÇÕES DE CAUSA/MOTIVO:
- Explique a relação de causa e efeito de forma lógica e encadeada.
- Use conectivos como "devido a", "consequentemente" e "visto que".
- Se houver múltiplos fatores, organize-os por ordem de impacto.
- Conecte a explicação a cenários reais mencionados no contexto.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "Por que usar Docker em desenvolvimento?"
Resposta: O uso de Docker em desenvolvimento é recomendado por diversos motivos. **Primeiro**, ele elimina o problema clássico "funciona na minha máquina" pois cria ambientes idênticos em todos os computadores. **Segundo**, permite configurar serviços complexos (banco de dados, cache, filas) com um único comando. **Terceiro**, facilita o onboarding de novos desenvolvedores pois não precisam configurar tudo manualmente. **Consequentemente**, reduz tempo de setup e aumenta a produtividade da equipe. No contexto da empresa, reduzimos o tempo de onboarding de 2 dias para 2 horas usando Docker.

**Exemplo 2:**
Pergunta: "Por que o sistema está lento?"
Resposta: A lentidão no sistema ocorre devido a múltiplos fatores identificados. **Principalmente**, há uma query N+1 no endpoint `/products` que faz 1000 consultas ao banco em vez de 1. **Adicionalmente**, o cache Redis não está configurado corretamente, forçando leituras repetidas. **Visto que** o volume de acessos aumentou 5x na última semana, esses problemas se agravaram. A recomendação é: 1) Implementar eager loading para resolver N+1, 2) Configurar TTL de 5 minutos no cache. Fonte: Logs de performance do New Relic, 15/12/2025.

---

Agora responda seguindo este formato:',
        'Instruções para perguntas de causa/motivo com exemplos few-shot',
        TRUE,
        1),
        
        ('general',
        '### INSTRUÇÕES GERAIS:
- Estruture a resposta com títulos ou tópicos para facilitar a leitura.
- Use exemplos do contexto para validar suas afirmações.
- Se o tema for complexo, adicione um breve "Resumo Executivo" ao final.
- Garanta que todas as afirmações técnicas tenham uma fonte citada.

---

### EXEMPLOS DE COMO RESPONDER:

**Exemplo 1:**
Pergunta: "Como funciona o sistema de pagamentos?"
Resposta: **Arquitetura:**
O sistema de pagamentos usa uma arquitetura orientada a eventos com 3 componentes principais: API Gateway, Processador de Pagamentos e Notificador.

**Fluxo:**
1. Cliente envia requisição com dados do cartão (criptografados)
2. API Gateway valida formato e encaminha para Processador
3. Processador se comunica com gateway de pagamento (Stripe)
4. Stripe aprova/rejeita a transação
5. Processador salva resultado no banco
6. Notificador envia email/confirmação ao cliente

**Resumo Executivo:** O sistema processa 500 transações/hora com 99.9% de uptime. Fonte: Documentação do sistema, arquitetura de pagamentos.

---

Agora responda seguindo este formato:',
        'Instruções para perguntas gerais com exemplos few-shot',
        TRUE,
        1)
    """)


def downgrade():
    # Remover dados
    op.execute("DELETE FROM question_type_instructions")
    
    # Remover índice
    op.drop_index('idx_qti_question_type', table_name='question_type_instructions')
    
    # Remover tabela
    op.drop_table('question_type_instructions')
