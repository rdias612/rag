# Melhoria de Prompts para o Sistema RAG

Este documento detalha as sugestões de melhoria para os prompts utilizados no sistema, visando respostas mais precisas, melhor utilização do contexto e maior consistência no formato.

## 1. Princípios Gerais de Melhoria

Para todos os prompts, foram aplicados os seguintes princípios:
- **Definição Clara de Persona**: Atribuição de um papel específico ao modelo.
- **Instruções Negativas**: Definição explícita do que o modelo *não* deve fazer.
- **Formatação Estruturada**: Uso de Markdown para facilitar a leitura e o parsing.
- **Tratamento de Incerteza**: Instruções robustas para quando a informação não estiver presente.
- **Citações Explícitas**: Exigência de referências aos documentos fonte.

---

## 2. Prompts de Geração (RAG)

### Atual: `RAG_PROMPT_ENHANCED`
O prompt atual é bom, mas pode ser mais enfático na separação entre conhecimento interno e contexto fornecido.

### Sugestão: `RAG_PROMPT_V2`
```markdown
Você é o **Assistente de Base de Conhecimento**, um especialista em extrair e sintetizar informações de documentos técnicos. Sua missão é fornecer respostas precisas, baseando-se estritamente no [CONTEXTO] fornecido.

### DIRETRIZES:
1. **Fidelidade ao Contexto**: Responda APENAS com informações contidas no [CONTEXTO]. Se a informação não for encontrada, admita claramente: "Não encontrei informações sobre [tópico] nos documentos fornecidos."
2. **Citações**: Sempre que fizer uma afirmação baseada em um documento, cite a fonte (ex: [Fonte: manual_tecnico.pdf, pág. 12]).
3. **Formatação**: Use negrito para termos chave e listas para processos passo a passo.
4. **Tom de Voz**: Profissional, direto e objetivo.

### [CONTEXTO]
{contexto}

### [HISTÓRICO] (Se disponível)
{historico}

### [PERGUNTA DO USUÁRIO]
{pergunta}

### [INSTRUÇÕES ADICIONAIS]
{instrucoes_tipo}

---
**RESPOSTA:**
```

---

## 3. Prompts de Classificação e Especialização

As instruções atuais em `QUESTION_TYPE_INSTRUCTIONS` podem ser melhoradas com "Few-Shot Examples" (exemplos de poucas passagens) para guiar o modelo.

### Sugestão para `comparison`:
> [!TIP]
> Em vez de apenas dizer "Destaque semelhanças e diferenças", use um comando mais estruturado:
> "Sua resposta deve conter obrigatoriamente uma tabela comparativa no início, seguida de uma análise qualitativa das vantagens de cada item."

### Sugestão para `procedure`:
> "Se o contexto descrever um erro comum para este procedimento, inclua uma seção de '⚠️ Atenção' ou 'Dica Pro' ao final do passo a passo."

---

## 4. Prompt de Expansão de Query (`HYDE` e `Query Expansion`)

O prompt de HyDE atual é funcional, mas tende a ser genérico.

### Sugestão para `HYDE_PROMPT`:
```markdown
Como um redator técnico senior, escreva um parágrafo que seria a resposta ideal para a pergunta abaixo. 
Não use frases como "Eu acho que" ou "Este documento descreve". Escreva como se fosse o próprio conteúdo do manual.

Pergunta: "{question}"
Conteúdo Técnico Esperado:
```

---

## 5. Próximos Passos Sugeridos

1. **Centralização**: Mover os templates de prompt de `src/core/*.py` para um arquivo `src/core/prompts.py` ou para o `src/config.py` de forma organizada.
2. **Versionamento**: Adicionar um sufixo de versão aos prompts para facilitar testes A/B futuros.
3. **Parâmetros**: Permitir que o usuário escolha o "estilo" da resposta (Conciso vs. Detalhado) via frontend.

---
*Documento gerado por Antigravity em 26/12/2025.*
