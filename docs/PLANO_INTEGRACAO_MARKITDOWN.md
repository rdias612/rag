# 📋 Plano de Implementação: Integração MarkItDown

## 📌 Objetivo
Substituir os múltiplos extratores manuais de texto por uma solução unificada baseada na biblioteca `markitdown` da Microsoft. O objetivo é converter todos os documentos (PDF, Docx, XLSX, etc.) para Markdown antes de realizar o chunking e embedding, preservando a semântica e estrutura (tabelas, títulos, listas).

---

## 🔍 Benefícios Esperados
1. **Preservação de Estrutura**: Títulos (#, ##) ajudam o `SemanticChunker` a identificar limites de seções.
2. **Tabelas**: Conversão superior de tabelas para formato Markdown, facilitando a compreensão pelo LLM.
3. **Redução de Código**: Eliminação de extratores customizados em `src/data/ingestion.py`.
4. **Novos Formatos**: Suporte nativo a Excel (.xlsx) e PowerPoint (.pptx).

---

## 🛠️ Mudanças Propostas

### 1. Dependências (`requirements.txt`)
Adicionar a biblioteca `markitdown` e remover ou manter como secundárias as bibliotecas de processamento direto se não forem mais necessárias para outros fins.

```text
markitdown>=0.0.1
```

### 2. Configurações (`src/config.py`)
Adicionar flag para habilitar/desabilitar o uso do MarkItDown para facilitar rollback se necessário.

```python
ENABLE_MARKITDOWN: bool = True
```

### 3. Refatoração da Ingestão (`src/data/ingestion.py`)
- Instanciar `MarkItDown` globalmente ou dentro das funções de processamento.
- Criar um extrator unificado `extract_text_with_markitdown(file_path)`.
- Atualizar `get_extractor_for_file` para priorizar o MarkItDown.
- Remover/Simplificar: `extract_text_from_pdf`, `extract_text_from_docx`, `extract_text_from_csv`, etc.

### 4. Ajustes no Chunking (`src/data/chunking.py`)
- O `SemanticChunker` já possui detecção básica de títulos Markdown. Podemos refinar a função `extract_section_title` para aproveitar melhor os headers gerados pelo MarkItDown.

---

## ✅ Tarefas de Implementação

### Fase 1: Setup
- [ ] Adicionar `markitdown` ao `requirements.txt`.
- [ ] Executar instalação das dependências.
- [ ] Adicionar `ENABLE_MARKITDOWN` ao `src/config.py`.

### Fase 2: Desenvolvimento
- [ ] Implementar a lógica do `MarkItDown` em `src/data/ingestion.py`.
- [ ] Criar fallback para extratores antigos caso o `markitdown` falhe em arquivos específicos.
- [ ] Atualizar o suporte a extensões (`SUPPORTED_EXTENSIONS`) para incluir `.xlsx` e `.pptx`.

### Fase 3: Validação
- [ ] Testar ingestão de um PDF com tabelas complexas.
- [ ] Testar ingestão de um arquivo Excel.
- [ ] Verificar a qualidade dos chunks gerados com a nova estrutura Markdown.

### Fase 4: Re-ingestão Geral
- [ ] Limpar o banco de dados (`python -m scripts.ingest --clear`).
- [ ] Processar todos os arquivos novamente com a nova pipeline.

---

## ⚠️ Riscos e Considerações
- **Dependências de Sistema**: O `markitdown` pode exigir ferramentas de sistema adicionais para certos formatos (ex: `libmagic`).
- **Performance**: A conversão para Markdown pode ser ligeiramente mais lenta que a extração de texto puro em arquivos muito grandes.
- **Tamanho dos Chunks**: Chunks contendo tabelas Markdown longas podem exceder o limite de caracteres original; pode ser necessário ajustar `CHUNK_SIZE`.

---
*Plano criado em: 29 de Dezembro de 2024*
