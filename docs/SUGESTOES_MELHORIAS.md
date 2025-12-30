# 🚀 Próximas Melhorias para o Sistema RAG

Este documento contém os itens pendentes para otimização do sistema RAG, reordenados por prioridade após a implementação das fases iniciais.

---

## 📊 Status de Implementação (Atualizado: Dezembro 2025)

Até o momento, o sistema já conta com:
- ✅ **Busca Híbrida** (Vetorial + FTS) com RRF
- ✅ **Re-ranking** com Cross-Encoder
- ✅ **Query Expansion** e **HyDE**
- ✅ **Cache de Embeddings** (LRU + MD5)
- ✅ **Hierarchical RAG** (Parent-Child Chunking)
- ✅ **Classificação de Perguntas** e Prompts Especializados
- ✅ **Avaliação RAGAS** (Faithfulness, Relevancy, Precision)
- ✅ **Multi-tenancy** (Coleções separadas no banco)
- ✅ **Controle de Ingestão** (Incremental Re-ingestion)
- ✅ **Modo Debug Avançado** (Explicação do pipeline via API)

---

## 🔴 Alta Prioridade (Evolução Técnica & Core)

### 1. Self-RAG / Reflexão
**Problema:** O LLM pode gerar respostas incorretas ou incompletas mesmo com o contexto correto.
**Solução:** Implementar loop de reflexão.
*Obs: Configuração `ENABLE_SELF_RAG` já existe.*

### 2. Persistência do Cache (Redis)
**Problema:** O cache atual é em memória e se perde ao reiniciar o servidor.
**Solução:** Migrar o `EmbeddingCache` para o Redis. Isso permite compartilhamento de cache entre múltiplas instâncias e persistência entre deploys.

### 3. Adaptive Retrieval
**Problema:** Busca fixa pode ser ineficiente para queries muito simples ou muito complexas.
**Solução:** Ajustar `top_k` e `min_similarity` dinamicamente baseado na complexidade da query.
*Obs: Configuração `ENABLE_ADAPTIVE_RETRIEVAL` já existe.*

### 4. Containerização Completa (Docker)
**Problema:** Atualmente apenas o banco de dados está dockerizado.
**Solução:** Dockerizar a API (Flask) e o Frontend (React), permitindo que todo o ecossistema suba com um único `docker-compose up`.

---

## 🟡 Média Prioridade (Refinamento de Dados & UX)

### 5. Suporte Multi-modal (Imagens + Texto)
**Problema:** Atualmente imagens em PDFs/Docs são ignoradas.
**Solução:** Extrair imagens durante a ingestão, gerar descrições via LLaVA/GPT-4V e indexá-las como contexto.

### 6. Streaming no Chat com Histórico
**Problema:** O endpoint de streaming atual (`/api/query/stream`) não suporta sessões de chat com histórico.
**Solução:** Unificar a lógica de streaming para que suporte `session_id` e mantenha a continuidade da conversa.

### 7. Sentence Window Retrieval
**Problema:** Chunks isolados podem perder a fluidez da explicação.
**Solução:** Recuperar chunks pequenos, mas expandir dinamicamente para sentenças vizinhas antes do prompt.

### 8. Fine-tuning do Modelo de Embeddings
**Problema:** Modelos genéricos podem ter baixa performance em nichos técnicos específicos.
**Solução:** Treinar/Ajustar o modelo de embeddings com pares (pergunta, documento) da própria base.

---

## 🟢 Otimizações de Processo & Gestão

### 9. Sistema de Feedback (Endpoint API)
**Problema:** Falta a rota `/api/feedback` para expor a lógica de avaliação do banco de dados ao frontend.

### 10. Expansão da Suíte de Testes
**Problema:** Cobertura de testes limitada.
**Solução:** Implementar suite completa com `pytest` (Unitários, Integração e E2E).

### 11. Documentação OpenAPI/Swagger
**Problema:** Difícil para novos desenvolvedores entenderem e testarem os 28 endpoints da API.
**Solução:** Integrar Swagger UI para documentação interativa e testável.

### 12. OCR e Tabelas Aprimorados (Ingestão)
**Sugestão:** Integrar `pytesseract` e `tabula-py` para PDFs complexos.

---

## 📋 Novo Roadmap Sugerido

### Fase de Infraestrutura & Inteligência
1. [ ] Implementar loop de reflexão (Self-RAG)
2. [ ] Migrar cache para Redis
3. [ ] Ajuste adaptativo de busca
4. [ ] Dockerização Completa (API + Frontend)

### Fase de IA Avançada & UX
5. [ ] Streaming com suporte a Histórico
6. [ ] Suporte Multi-modal (Vision)
7. [ ] Sentence Window Retrieval
8. [ ] Fine-tuning de Embeddings

### Fase de Qualidade & APIs
9. [ ] Endpoint de Feedback API
10. [ ] Documentação OpenAPI/Swagger
11. [ ] Suíte Completa de Testes
12. [ ] Ingestão especializada (OCR/Tabelas)