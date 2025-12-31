# 🎯 Implementação: Sentence Window Retrieval (Busca + Ingestão)

**Data:** 31/12/2025  
**Item:** #4 - Sentence Window Retrieval (SUGESTOES_MELHORIAS.md)  
**Status:** ✅ COMPLETO

---

## 📋 Resumo

Implementação completa do **Sentence Window Retrieval** integrando tanto **busca** quanto **ingestão** de documentos.

O sistema agora oferece uma solução unificada onde os usuários podem:

1. **Na Busca:** Escolher entre 3 modos de recuperação
   - 🔄 **Automático**: Sistema decide automaticamente
   - 📖 **Explicação (Hierarchical)**: Contexto amplo e detalhado
   - 🎯 **Precisão (Sentence Window)**: Respostas diretas e específicas

2. **Na Ingestão:** Selecionar tipo de chunking por documento
   - 📖 **Explicação (Hierarchical)**: Melhor para tutoriais e documentação
   - 🎯 **Precisão (Sentence Window)**: Melhor para dados e fatos específicos

---

## 🏗️ Arquitetura da Solução

### Visão Geral

O sistema foi expandido para suportar dois tipos de chunking que convivem harmonicamente:

```
┌─────────────────────────────────────────────────────────────────┐
│              BANCO DE DADOS (tabela: chunks)             │
├─────────────────────────────────────────────────────────────────┤
│                                                           │
│  chunk_type pode ser:                                      │
│  - "parent"    : Chunks grandes (Hierarchical)            │
│  - "child"     : Chunks médios (Hierarchical)             │
│  - "sentence"  : Chunks pequenos, 1 sentença cada (NOVO)  │
│                                                           │
│  Chunks "sentence" possuem metadados adicionais:            │
│  - sentence_index    : Posição da sentença no documento    │
│  - total_sentences  : Total de sentenças no documento      │
│  - char_start/char_end : Posição no texto original       │
│                                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE INGESTÃO                    │
├─────────────────────────────────────────────────────────────────┤
│                                                           │
│  Usuário clica em "Ingestão com Seleção"                    │
│                    ↓                                       │
│  Modal mostra documentos pendentes                           │
│                    ↓                                       │
│  Usuário escolhe tipo para cada arquivo:                    │
│    📖 Explicação → Processamento Hierarchical               │
│    🎯 Precisão  → Processamento Sentence Window             │
│                    ↓                                       │
│  Sistema gera chunks com chunk_type apropriado               │
│                    ↓                                       │
│  Chunks são indexados com embeddings                        │
│                                                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     FLUXO DE BUSCA                        │
├─────────────────────────────────────────────────────────────────┤
│                                                           │
│  Usuário escolhe modo de recuperação:                      │
│    🔄 Automático   → Sistema analisa a pergunta             │
│    📖 Explicação → Usa chunks parent/child (Hierarchical)   │
│    🎯 Precisão    → Usa chunks sentence (Sentence Window)    │
│                    ↓                                       │
│  Busca inicial:                                             │
│    Hierarchical → Busca chunks child                       │
│    Sentence    → Busca chunks sentence                     │
│                    ↓                                       │
│  Se Sentence Window:                                        │
│    Para cada sentença encontrada, expande janela             │
│    (3 antes + sentença + 3 depois)                        │
│                    ↓                                       │
│  Re-ranking, HyDE, Query Expansion (se habilitado)         │
│                    ↓                                       │
│  Resultados enviados para o LLM                             │
│                                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Decisão Automática (Modo Auto)

O sistema analisa a pergunta e decide automaticamente:

**Usa Sentence Window quando:**
- Perguntas muito curtas (≤5 palavras)
- Contém "qual é", "o que é", "quanto custa"
- Contém "onde fica", "quem é"

**Usa Hierarchical quando:**
- Perguntas começam com "como"
- Contém "como funciona", "por que"
- Contém "explique", "explicar"
- Padrão (mais seguro para perguntas complexas)

---

## 📁 Componentes Implementados

### Backend

1. **Database Migration**
   - Novos campos na tabela `chunks`: `chunk_type`, `sentence_index`, `total_sentences`, `char_start`, `char_end`
   - Índices para filtrar por tipo de chunk

2. **sentence_window.py**
   - Migrou de NLTK para **spaCy** (mais robusto em português)
   - Cria índice de sentenças com metadados de posição
   - Cada sentença torna-se um chunk individual

3. **ingestion.py**
   - Função para processar documentos com Sentence Window
   - Função unificada que aceita tipo de chunking
   - Suporte a ambos os tipos (hierarchical e sentence)

4. **rag/pipeline.py**
   - Função `determine_search_strategy()` para decisão automática
   - Integração com parâmetro `search_mode`

5. **search_service.py**
   - Método `search_with_sentence_window()` completo
   - Expansão dinâmica de janelas (recupera todas as sentenças do documento)
   - Deduplicação de resultados

6. **API Routes**
   - Novo endpoint: `GET /documents/scan-with-selection`
   - Atualizado: `POST /documents/ingest-all` (suporta chunking_type por arquivo)
   - Atualizados: `POST /api/query`, `/api/chat`, `/api/query/stream` (search_mode)

### Frontend

1. **RetrievalModeSelector.tsx**
   - 3 botões: Automático, Explicação, Precisão
   - Popover explicativo (botão ℹ️)
   - Persistência no localStorage
   - Toggle (clique no mesmo botão para desmarcar)

2. **ChunkingSelectionModal.tsx** (NOVO)
   - Modal para selecionar tipo de chunking por documento
   - Botões "Selecionar tudo como: Explicação/Precisão"
   - Estatísticas em tempo real (quantos de cada tipo)
   - Interface responsiva e acessível

3. **DocumentsPanel.tsx**
   - Novo botão roxo: "Ingestão com Seleção"
   - Integração completa com o modal de seleção
   - Funcionalidade para enviar seleção para backend

4. **App.tsx e api.ts**
   - Integração do seletor de modo no sidebar
   - Passagem de `search_mode` para API

---

## 🎨 Interface do Usuário

### 1. Painel de Documentos - Ingestão

```
┌─────────────────────────────────────────────────────────┐
│ 📄 Documentos                                          │
│                                                         │
│  [🔄 Atualizar] [📝 Ingestão com Seleção] [♻️] [↻] │
│     (Padrão)        (NOVO - Roxo)                      │
└─────────────────────────────────────────────────────────┘
```

### 2. Modal de Seleção de Chunking

```
┌─────────────────────────────────────────────────────────────────┐
│  📄 Documentos Pendentes (5)                              │
│  Selecione o tipo de chunking para cada documento            │
│                                                           │
│  [Selecionar tudo como: [📖 Explicação] [🎯 Precisão]]   │
│                                                           │
│  📊 Estatísticas:                                          │
│     📖 Explicação: 3    🎯 Precisão: 2                │
│                                                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 📄 documento1.pdf              [📖 Explicação ▼] │  │
│  │ 📄 documento2.pdf              [🎯 Precisão   ▼] │  │
│  │ 📄 relatorio.docx              [📖 Explicação ▼] │  │
│  │ ...                                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                           │
│  [Cancelar]                                       [✓ Iniciar]│
└─────────────────────────────────────────────────────────────────┘
```

### 3. Seletor de Modo de Busca (Sidebar)

```
┌─────────────────────────────────────────────────────────────────┐
│ Configurações                                            │
│                                                         │
│ 🔍 MODO DE BUSCA                                         │
│   [ℹ️ Como funciona?]                                    │
│                                                         │
│   ┌─────────────────────────────────────────────────────┐    │
│   │ [🔄] Automático (sistema decide)            │    │
│   │ Ideal para a maioria dos casos                 │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                         │
│   ┌─────────────────────────────────────────────────────┐    │
│   │ [📖] Explicação (Hierarchical)              │    │
│   │ Contexto mais detalhado                      │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                         │
│   ┌─────────────────────────────────────────────────────┐    │
│   │ [🎯] Precisão (Sentence Window)            │    │
│   │ Resposta direta                              │    │
│   └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Comparação: Hierarchical vs Sentence Window

| Aspecto | Hierarchical (Explicação) | Sentence Window (Precisão) |
|----------|---------------------------|---------------------------|
| **Tamanho do Chunk** | 500-800 tokens | 1 sentença (~15-20 tokens) |
| **Precisão de Busca** | Alta | Muito Alta |
| **Contexto no Prompt** | Alto (chunks grandes) | Médio (janela expandida) |
| **Melhor para** | Explicações, processos | Respostas diretas, dados específicos |
| **Performance** | Rápido | Ligeiramente mais lento (expansão dinâmica) |
| **Recall** | Alto | Muito Alto |
| **Quantidade de Chunks** | Menos | Muito mais |

---

## 🎯 Casos de Uso

### Quando usar 📖 Explicação (Hierarchical):

- **Tutoriais e guias**: Onde explicações detalhadas são necessárias
- **Documentação técnica**: Fluxos complexos que precisam de contexto
- **Artigos e blogs**: Conteúdo narrativo e fluido
- **Livros e manuais**: Informações estruturadas em capítulos
- **Perguntas**: "Como funciona?", "Por que isso acontece?", "Explique o processo"
- **Foco**: Contexto amplo e fluidez da explicação

### Quando usar 🎯 Precisão (Sentence Window):

- **Perguntas específicas de fatos**: "Qual o número de telefone?", "Quanto custa?"
- **Consultas de dados**: Tabelas, listas, especificações
- **Perguntas com resposta única**: Definições, valores, contatos
- **Documentos muito fragmentados**: Listas, bullet points, FAQs
- **Perguntas**: "Qual é?", "Onde fica?", "Quem é?"
- **Foco**: Resposta direta, precisa e focada

### Modo Automático 🔄:

Deixa o sistema decidir baseado em heurísticas da pergunta:
- Perguntas curtas (≤5 palavras) → Precisão
- Perguntas "qual é", "quanto custa" → Precisão
- Perguntas "como funciona", "por que" → Explicação
- Padrão → Explicação (mais seguro)

---

## ✅ Benefícios da Implementação

### 1. Flexibilidade Total

- ✅ **Escolha de chunking por documento**: Cada documento pode usar o tipo ideal
- ✅ **Escolha de modo de busca por query**: Cada pergunta pode usar a melhor estratégia
- ✅ **Suporte a re-ingestão**: Documentos já ingeridos podem ser reprocessados
- ✅ **Convivência pacífica**: Ambos os tipos de chunks coexistem sem conflito

### 2. Experiência do Usuário

- ✅ **Interface intuitiva**: Visual e fácil de usar
- ✅ **Botão rápido**: "Selecionar tudo como" para eficiência
- ✅ **Estatísticas em tempo real**: Feedback claro do que está sendo selecionado
- ✅ **Popover explicativo**: Ajuda os usuários a entender cada modo
- ✅ **Persistência**: Preferências salvas no localStorage

### 3. Qualidade da Busca

- ✅ **Melhor recall**: Sentence window recupera mais resultados relevantes
- ✅ **Melhor precisão**: Chunks menores = embeddings mais focados
- ✅ **Menos alucinações**: Contexto mais preciso para o LLM
- ✅ **Respostas mais adequadas**: Escolha da estratégia certa para cada tipo de pergunta

### 4. Performance

- ✅ **Embeddings mais focados**: Sentenças individuais têm vetores mais específicos
- ✅ **Melhor similaridade semântica**: Menos ruído nos embeddings
- ✅ **Índices otimizados**: Queries filtrando por chunk_type são rápidas

---

## 🔧 Configuração

### Dependências

- **spacy**: Biblioteca de NLP para processamento de português
- **pt_core_news_sm**: Modelo spaCy para português (deve ser instalado separadamente)

### Instalação

```bash
# Instalar modelo spaCy
python -m spacy download pt_core_news_sm
```

### Configuração do Sistema

- `SENTENCE_WINDOW_SIZE`: 3 (tamanho da janela de expansão)
  - Significa: 3 sentenças antes + sentença encontrada + 3 sentenças depois
  - Configurável em `src/config.py`

---

## 🧪 Como Testar

### 1. Teste de Ingestão com Seleção

1. Adicione arquivos novos ao diretório `docs/`
2. No frontend, clique em **"Ingestão com Seleção"**
3. No modal:
   - Selecione alguns documentos como **"Explicação"**
   - Selecione outros como **"Precisão"**
   - Use os botões **"Selecionar tudo como"** para rapidez
4. Clique em **"Iniciar"**
5. Verifique o progresso e logs

**Verificação no banco:**
```sql
SELECT chunk_type, COUNT(*) 
FROM chunks 
GROUP BY chunk_type;
-- Deve mostrar: parent, child, sentence
```

### 2. Teste de Busca - Modo Automático

1. Deixe o modo como **"Automático"** (default)
2. Faça perguntas curtas:
   - "Qual o preço do produto X?"
   - Sistema deve usar **Precisão** (Sentence Window)
3. Faça perguntas explicativas:
   - "Como funciona o processo de pagamento?"
   - Sistema deve usar **Explicação** (Hierarchical)
4. Compare qualidade das respostas

### 3. Teste de Busca - Modos Manuais

1. No Sidebar, selecione **"Precisão"**
2. Faça uma pergunta específica
3. Observe que a resposta é mais direta
4. Mude para **"Explicação"**
5. Faça a mesma pergunta
6. Observe que a resposta é mais detalhada

### 4. Teste de Re-ingestão

1. Selecione documentos já ingeridos (checkboxes na tabela)
2. Clique em **"Reprocessar selecionados"**
3. Observe se mantém a estrutura e se os chunks são recriados

---

## 📝 Notas Importantes

### Convivência de Chunks

O sistema suporta **três tipos de chunks** simultaneamente:
- `parent`: Chunks grandes para contexto
- `child`: Chunks médios para busca
- `sentence`: Chunks pequenos para precisão

Esta flexibilidade permite otimizar a busca para diferentes tipos de conteúdo sem conflitos.

### Migração de Dados

Chunks existentes (hierarchical) continuam funcionando normalmente. A migration adiciona apenas os campos novos, mantendo compatibilidade total.

### Performance Considerations

- **Sentence Window** é ligeiramente mais lento devido à expansão dinâmica
- O impacto é mínimo porque:
  - Busca inicial é em chunks pequenos (rápido)
  - Expansão é apenas nos documentos relevantes
  - Índices estão otimizados

### Limitações Atuais

1. Tamanho da janela é fixo (3) para todos os documentos
2. Não há detecção automática do tipo ideal de chunking
3. Modo automático usa heurísticas simples (pode ser melhorado com ML)

---

## 🚀 Próximos Passos Opcionais

### 1. Adaptação Automática

Detectar tipo de documento e sugerir chunking ideal:
- PDFs de tabelas → Sentence Window
- Tutoriais → Hierarchical
- FAQs → Sentence Window

### 2. Fine-tuning da Heurística

Coletar métricas de uso e ajustar os critérios:
- Acompanhar qual modo funciona melhor para cada tipo de pergunta
- Possibilidade de usar ML para decisão mais inteligente

### 3. Configuração Avançada

- Permitir `window_size` customizável por documento
- Suporte a múltiplas estratégias por documento
- Perfil de preferência por usuário

### 4. Analytics e A/B Testing

- Acompanhar qual tipo de chunking é mais usado
- Acompanhar qual modo de busca é mais usado
- Comparar métricas de satisfação (RAGAS) entre modos

---

## ✅ Checklist de Implementação

### Backend
- [x] Migration do banco de dados criada
- [x] `sentence_window.py` atualizado com spaCy
- [x] `process_document_sentence_window()` implementado
- [x] `process_document_with_chunking_type()` implementado
- [x] `determine_search_strategy()` implementado
- [x] `search_with_sentence_window()` implementado
- [x] Endpoint `/documents/scan-with-selection` criado
- [x] Endpoint `/documents/ingest-all` atualizado
- [x] Rotas de query atualizadas (`/api/query`, `/api/chat`, `/api/query/stream`)

### Frontend
- [x] `RetrievalModeSelector.tsx` criado
- [x] `ChunkingSelectionModal.tsx` criado
- [x] `DocumentsPanel.tsx` atualizado
- [x] Integração no Sidebar
- [x] Persistência no localStorage
- [x] Tipos TypeScript atualizados
- [x] API atualizada com `search_mode`

### Documentação e Testes
- [x] Documentação conceitual criada (este documento)
- [x] Casos de uso documentados
- [x] Testes manuais validados
- [x] Compatibilidade total verificada

---

## 🎉 Conclusão

O sistema agora oferece uma **solução completa e unificada** para o Sentence Window Retrieval:

### Flexibilidade Total:
- 📖 **Hierarchical**: Para explicações e contexto amplo
- 🎯 **Sentence Window**: Para precisão e respostas diretas
- 🔄 **Automático**: O sistema decide automaticamente

### Implementação Robusta:
- ✅ Convivência pacífica de múltiplos tipos de chunks
- ✅ Migração de banco de dados com índices otimizados
- ✅ Interface intuitiva e acessível
- ✅ Compatibilidade total com o sistema existente

### Qualidade Aumentada:
- ✅ Melhor recall e precisão para diferentes tipos de conteúdo
- ✅ Menos alucinações do LLM
- ✅ Respostas mais adequadas ao tipo de pergunta

Isso permite aos usuários otimizar a qualidade das respostas do LLM para diferentes tipos de conteúdo e perguntas, melhorando significativamente a experiência geral do sistema RAG.

**Status: ✅ PRODUÇÃO PRONTA**
