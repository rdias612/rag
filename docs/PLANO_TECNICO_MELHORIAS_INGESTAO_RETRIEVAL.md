# Plano Técnico de Melhorias para Ingestão e Retrieval

## Objetivo

Melhorar a qualidade dos dados enviados à LLM na etapa final do RAG, atuando em três camadas:

1. Ingestão: preservar melhor a estrutura semântica e a proveniência dos documentos.
2. Retrieval: aumentar recall sem perder precisão, com contexto mais consistente por evidência.
3. Context building: enviar para a LLM blocos de evidência mais úteis, menos redundantes e melhor rotulados.

## Diagnóstico Resumido

O código atual já possui bases importantes, mas ainda há gaps entre as capacidades implementadas e o fluxo principal:

- O pipeline principal busca chunks filhos, mas não expande os resultados hierárquicos para o chunk pai antes de montar o contexto.
- Query expansion está habilitado por configuração, mas não entra no fluxo principal de busca.
- O contexto final ainda é montado por concatenação simples de documentos/chunks.
- Metadados contextuais promissores já existem, mas não estão integrados à ingestão usada em produção.
- A compressão de contexto precisa ser revisada para compatibilizar interface e retorno.
- A extração atual preserva pouco da estrutura documental para citação, seleção de evidência e resposta final.

## Princípios de Implementação

1. Melhorar a qualidade do contexto sem aumentar excessivamente latência ou custo.
2. Entregar por fases pequenas e validáveis.
3. Medir retrieval e qualidade do contexto antes de medir só a resposta final.
4. Reutilizar o que já existe no código antes de criar novas abstrações.
5. Manter rollback simples por feature flag quando possível.

## Resultado Esperado

Ao final da entrega, o sistema deverá:

- recuperar evidências mais aderentes à pergunta;
- expandir precisão local para contexto suficiente;
- reduzir redundância no contexto final;
- melhorar citações, rastreabilidade e explicabilidade;
- elevar a taxa de respostas suportadas por evidência útil.

---

## Fase 0 - Baseline, Instrumentação e Critérios de Qualidade

### Objetivo

Criar um baseline reproduzível antes das mudanças funcionais, para medir ganho real de ingestão e retrieval.

### Entregas

- Definição de conjunto de perguntas de avaliação.
- Métricas de retrieval e contexto.
- Logs estruturados para comparação antes/depois.

### Mudanças por arquivo

#### src/core/rag/pipeline.py
- Adicionar payload estruturado de métricas por etapa:
  - quantidade de candidatos iniciais;
  - quantidade após MMR/rerank;
  - documentos únicos por source;
  - tamanho do contexto final;
  - modo de busca efetivo.

#### src/core/rag/services/context_service.py
- Expor métricas de contexto:
  - número de blocos incluídos;
  - caracteres por bloco;
  - fontes únicas;
  - taxa de truncamento por max_chars.

#### src/data/repositories/evaluation_repository.py
- Estender registro para armazenar:
  - retrieval_mode efetivo;
  - quantidade de fontes únicas;
  - redundância estimada;
  - coverage de evidência.

#### tests/
- Criar suíte nova de avaliação offline, sem depender da resposta da LLM:
  - tests/test_retrieval_quality_smoke.py
  - tests/test_context_builder_quality.py

### Métricas da fase

- Recall@5 e Recall@10 de evidências esperadas.
- MRR de retrieval.
- nDCG@10 para ordenação.
- Taxa de contexto redundante.
- Média de fontes únicas por resposta.
- Média de caracteres úteis por bloco.

### Critério de aceite

- Baseline executável localmente.
- Pelo menos 30 perguntas de validação classificadas por tipo:
  - factual;
  - definição;
  - procedimento;
  - comparação;
  - explicação.

### Risco controlado

- Sem alterar comportamento funcional do usuário final.

---

## Fase 1 - Retrieval Hierárquico Real

### Objetivo

Usar chunks filhos para localizar evidência precisa, mas entregar chunks pais para a LLM quando o modo for hierarchical.

### Problema atual

Hoje a busca recupera chunks pequenos com boa precisão, mas o contexto final não necessariamente recebe o texto pai correspondente. Isso prejudica explicações e respostas compostas.

### Mudanças por arquivo

#### src/core/rag/pipeline.py
- Inserir etapa explícita de expansão hierárquica após a busca inicial e antes da montagem de contexto.
- Quando o modo efetivo for hierarchical:
  - buscar children;
  - deduplicar por parent_index e source_path;
  - expandir para pais;
  - manter score do child que originou o parent.

#### src/core/rag/services/search_service.py
- Adicionar método dedicado para busca hierarchical:
  - search_with_hierarchical_context(...)
- Esse método deve:
  - recuperar children;
  - recuperar pais correspondentes;
  - devolver resultado pronto para contexto.

#### src/data/repositories/document_repository.py
- Reaproveitar get_parent_content e acrescentar método opcional para recuperação em lote:
  - get_parent_contents_batch(source_path_parent_pairs)
- Reduzir round-trips ao banco.

#### src/data/hierarchical_chunking.py
- Reusar expand_children_to_parents.
- Tornar o retorno mais adequado ao pipeline:
  - incluir source_path;
  - similarity do child;
  - metadata do child de origem;
  - parent_index.

#### tests/
- Criar testes específicos:
  - tests/test_hierarchical_retrieval_pipeline.py
  - garantir que hits em child retornem contexto pai correto.

### Métricas da fase

- Aumento de groundedness percebida em perguntas explicativas.
- Recall de contexto útil em perguntas longas.
- Queda da taxa de respostas incompletas por falta de contexto local.
- Delta de latência P50 e P95 após expansão pai-filho.

### Meta sugerida

- +15% a +25% em recall@5 para perguntas explicativas.
- Menos de 15% de aumento em latência P95 no modo hierarchical.

### Critério de aceite

- Toda busca hierarchical deve retornar blocos pais deduplicados.
- Respostas explicativas devem citar contexto com maior densidade factual.

---

## Fase 2 - Query Expansion no Fluxo Principal

### Objetivo

Aumentar recall do retrieval principal usando múltiplas variações da query, com fusão controlada dos resultados.

### Problema atual

Query expansion existe, mas não participa do pipeline principal. Assim, o sistema perde recuperação de sinônimos, reformulações e termos implícitos.

### Mudanças por arquivo

#### src/core/rag/strategies/retrieval_strategy.py
- Substituir o placeholder atual por implementação real:
  - gerar variações da query;
  - executar busca para cada variação;
  - combinar por RRF;
  - aplicar MMR;
  - aplicar reranking.

#### src/core/query_expansion.py
- Fortalecer o parser das variações.
- Garantir remoção de duplicatas semânticas simples.
- Limitar variações por tipo de pergunta.

#### src/core/rag/pipeline.py
- Passar contexto de tipo de pergunta e parâmetros da busca para a estratégia.
- Registrar métricas por variação gerada e por fusão.

#### src/config.py
- Adicionar parâmetros finos:
  - QUERY_EXPANSION_ENABLED_FOR_FACTUAL
  - QUERY_EXPANSION_ENABLED_FOR_PROCEDURE
  - QUERY_EXPANSION_MAX_VARIATIONS
  - QUERY_EXPANSION_TIMEOUT_MS

#### tests/test_query_expansion.py
- Atualizar testes para cobrir:
  - variações vazias;
  - duplicadas;
  - queries factuais curtas;
  - queries explicativas longas.

### Métricas da fase

- Recall@10 antes/depois da expansão.
- MRR das evidências corretas.
- Diversidade de fontes retornadas.
- Custo de latência por query expandida.

### Meta sugerida

- +10% a +20% em recall@10 em perguntas factuais e vagas.
- Aumento de latência P95 inferior a 20% com limite de 2 a 3 variações.

### Critério de aceite

- Query expansion deve melhorar recall em benchmark offline sem degradação forte de precisão.

---

## Fase 3 - Montagem de Contexto por Blocos de Evidência

### Objetivo

Substituir a concatenação simples de chunks por um formatador de evidências com orçamento de contexto, diversidade e metadados úteis para a LLM.

### Problema atual

O contexto hoje é uma sequência de trechos com pouco sinal estrutural. Isso reduz a capacidade da LLM de priorizar evidência, citar corretamente e sintetizar respostas complexas.

### Mudanças por arquivo

#### src/core/rag/services/context_service.py
- Refatorar build_context para operar em blocos de evidência.
- Cada bloco deve incluir, no mínimo:
  - fonte;
  - score ou rank;
  - tipo do chunk;
  - trecho principal;
  - seção detectada;
  - vizinhança resumida quando disponível.
- Adicionar orçamento por:
  - fonte;
  - bloco;
  - total de caracteres/tokens.

#### src/data/chunking.py
- Integrar add_contextual_metadata ao fluxo de ingestão usado em produção.

#### src/data/ingestion.py
- Ao gerar chunks hierarchical e sentence, enriquecer metadata com:
  - section_title;
  - prev_summary;
  - next_summary;
  - total_chunks;
  - chunk_index consistente.

#### src/config.py
- Adicionar parâmetros para contexto:
  - CONTEXT_MAX_BLOCKS
  - CONTEXT_MAX_CHARS_PER_BLOCK
  - CONTEXT_MAX_BLOCKS_PER_SOURCE
  - CONTEXT_MIN_UNIQUE_SOURCES
  - CONTEXT_ENABLE_NEIGHBOR_SUMMARIES

#### tests/
- Criar testes de builder:
  - ordem dos blocos;
  - limite por fonte;
  - preservação de metadados;
  - comportamento sob truncamento.

### Formato alvo do contexto

Exemplo conceitual:

```text
[EVIDENCIA 1]
Fonte: manual_x.pdf
Seção: Critérios de aprovação
Tipo: parent
Relevância: 0.82
Trecho:
...

[EVIDENCIA 2]
Fonte: politica_y.docx
Seção: Exceções
Tipo: sentence_window
Trecho central:
...
```

### Métricas da fase

- Redução da redundância do contexto.
- Aumento de fontes únicas por resposta.
- Queda de truncamento de contexto relevante.
- Melhor taxa de citações corretas na resposta final.

### Meta sugerida

- Redução de 25% a 40% em contexto redundante.
- Aumento de 20% em cobertura de fontes úteis por resposta.

### Critério de aceite

- O contexto final deve ser auditável, legível e orientado a evidência.

---

## Fase 4 - Ingestão com Preservação de Estrutura Documental

### Objetivo

Melhorar o valor semântico dos chunks já na origem, preservando melhor títulos, listas, páginas, tabelas e fronteiras lógicas.

### Problema atual

A extração baseada em markdown achatado simplifica muito o documento. Isso ajuda ingestão rápida, mas sacrifica proveniência e segmentação de alta qualidade.

### Mudanças por arquivo

#### src/data/ingestion.py
- Reestruturar o pipeline de ingestão para separar etapas:
  - extração;
  - limpeza;
  - normalização estrutural;
  - chunking;
  - enrichment.
- Adicionar metadata adicional:
  - page_start;
  - page_end;
  - heading_path;
  - content_type (paragraph, list, table, code, title);
  - structural_hash para deduplicação.

#### src/data/chunking.py
- Melhorar heurísticas de quebra:
  - evitar cortar lista e tabela no meio;
  - preservar cabeçalhos imediatamente acima do bloco;
  - manter sentenças com números e referências juntas.

#### src/data/sentence_window.py
- Incluir section_title e page range na janela expandida.
- Preservar melhor a sentença central versus contexto lateral.

#### src/data/repositories/document_repository.py
- Garantir persistência e leitura consistente dos novos metadados.

#### alembic/
- Só criar migration se algum metadata sair de JSON e for promovido a coluna física.
- Recomendação inicial: manter no JSON até comprovar necessidade operacional.

### Métricas da fase

- Taxa de chunks com section_title válido.
- Taxa de chunks com proveniência utilizável.
- Taxa de chunk_boundary_error em listas e tabelas.
- Qualidade percebida de citação da resposta.

### Meta sugerida

- Pelo menos 80% dos chunks com section_title ou heading_path útil.
- Queda de 30% em cortes ruins de bloco estrutural.

### Critério de aceite

- Respostas devem citar fonte de modo mais consistente e usar menos contexto irrelevante.

---

## Fase 5 - Reranking Real e Política de Fusão

### Objetivo

Melhorar a ordenação final das evidências antes da montagem do contexto.

### Problema atual

Reranking está desligado por padrão, e o modo LLM-as-reranker não é a melhor opção para consistência e custo operacional em produção.

### Mudanças por arquivo

#### src/core/reranker.py
- Priorizar cross-encoder via API ou endpoint dedicado.
- Adicionar fallback claro quando o serviço de rerank estiver indisponível.
- Registrar score original e rerank_score separadamente.

#### src/core/rag/strategies/retrieval_strategy.py
- Definir pipeline padrão:
  - expansão da query;
  - fusão por RRF;
  - MMR;
  - reranking final.

#### src/config.py
- Adicionar parâmetros:
  - RERANKING_ENABLED_BY_MODE
  - RERANKING_MIN_CANDIDATES
  - RERANKING_TIMEOUT_MS
  - RERANKING_FAIL_OPEN

### Métricas da fase

- nDCG@10 antes/depois do rerank.
- precisão das top 3 evidências.
- latência P95 do pipeline com reranking.

### Meta sugerida

- +10% ou mais em nDCG@10 nas queries difíceis.
- latência adicional controlada em no máximo 150 a 300 ms quando endpoint dedicado estiver saudável.

### Critério de aceite

- Evidências do topo devem refletir melhor intenção da pergunta e reduzir chunks irrelevantes no contexto final.

---

## Fase 6 - Compressão de Contexto e Prompt Final

### Objetivo

Garantir que, quando o contexto ainda ficar grande, a compressão preserve evidência essencial e não degrade groundedness.

### Problema atual

Há indício de incompatibilidade entre o serviço que chama compressão e a função que a implementa. Além disso, a compressão atual ainda pensa em contexto bruto, não em blocos de evidência.

### Mudanças por arquivo

#### src/core/context_compression.py
- Compatibilizar interface do serviço com a implementação.
- Permitir compressão por bloco, não apenas por texto bruto concatenado.
- Adicionar modo heurístico sem LLM como fallback estável.

#### src/core/rag/services/context_service.py
- Chamar compressão só depois de montar blocos estruturados.
- Permitir compressão seletiva:
  - por relevância;
  - por redundância;
  - por tipo de bloco.

#### src/core/rag/services/prompt_service.py
- Ajustar prompt para consumir contexto estruturado.
- Instruir a LLM a:
  - priorizar evidências de maior score;
  - citar por bloco/fonte;
  - declarar conflito entre fontes quando existir.

#### src/config.py
- Adicionar parâmetros:
  - CONTEXT_COMPRESSION_MODE
  - CONTEXT_COMPRESSION_MAX_BLOCKS
  - CONTEXT_COMPRESSION_MIN_RELEVANCE

### Métricas da fase

- redução de tokens sem perda de resposta suportada;
- groundedness da resposta após compressão;
- taxa de alucinação percebida em contexto comprimido.

### Meta sugerida

- Reduzir 30% a 50% do contexto em casos longos sem perda significativa de qualidade em benchmark controlado.

### Critério de aceite

- Compressão não pode piorar de forma material as respostas do conjunto de regressão.

---

## Fase 7 - Avaliação Contínua e Operação

### Objetivo

Transformar as melhorias em processo contínuo, não entrega pontual.

### Mudanças por arquivo

#### src/core/evaluation.py
- Adicionar avaliação específica de retrieval/contexto, além da resposta final.

#### src/data/repositories/evaluation_repository.py
- Persistir métricas por fase do pipeline.

#### frontend/
- Expor no modo debug:
  - chunks candidatos;
  - evidências finais;
  - fontes únicas;
  - contexto final enviado à LLM.

#### docs/
- Documentar playbook de tuning:
  - top_k;
  - alpha híbrido;
  - chunk sizes;
  - política de rerank.

### Métricas da fase

- tendência semanal de recall;
- groundedness por tipo de pergunta;
- latência por modo de busca;
- custo médio por resposta.

### Critério de aceite

- Time consegue comparar qualquer alteração contra baseline de forma objetiva.

---

## Ordem Recomendada de Entrega

### Sprint 1

- Fase 0 completa.
- Parte funcional mínima da Fase 1.

### Sprint 2

- Concluir Fase 1.
- Implementar Fase 3 parcialmente, com builder de contexto por evidência.

### Sprint 3

- Implementar Fase 2.
- Ativar RRF + MMR com benchmark.

### Sprint 4

- Implementar Fase 4.
- Ajustar ingestão, metadata e validações estruturais.

### Sprint 5

- Implementar Fase 5.
- Validar reranker dedicado.

### Sprint 6

- Implementar Fase 6.
- Revisar prompts, compressão e regressão de groundedness.

### Sprint 7

- Implementar Fase 7.
- Consolidar dashboards e playbook operacional.

---

## Backlog Prioritário por Impacto

### Prioridade Alta

1. Retrieval hierárquico real.
2. Context builder por evidência.
3. Query expansion no fluxo principal.
4. Correção da compressão de contexto.

### Prioridade Média

1. Enriquecimento de metadata na ingestão.
2. Reranker dedicado.
3. Exibição operacional de evidências no modo debug.

### Prioridade Baixa

1. Promotion de metadados JSON para colunas físicas.
2. Tuning por coleção.
3. Políticas específicas por tipo de documento.

---

## Dependências e Cuidados

### Dependências técnicas

- Conjunto de perguntas de benchmark.
- Base de documentos representativa.
- Endpoint estável de embeddings.
- Endpoint estável de rerank, se adotado.

### Cuidados de implementação

- Não misturar rollout de ingestão estrutural com rollout de retrieval no mesmo deploy sem baseline.
- Evitar migrar schema cedo demais; priorizar metadata JSON primeiro.
- Proteger mudanças com flags de configuração para rollback rápido.

### Flags recomendadas

- ENABLE_HIERARCHICAL_PARENT_EXPANSION
- ENABLE_QUERY_EXPANSION_MAIN_PIPELINE
- ENABLE_EVIDENCE_CONTEXT_BUILDER
- ENABLE_STRUCTURED_INGESTION_METADATA
- ENABLE_CONTEXT_COMPRESSION_V2

---

## Critérios de Sucesso do Programa

O programa será considerado bem-sucedido se atingir simultaneamente:

1. melhora mensurável em retrieval no benchmark offline;
2. melhora perceptível na qualidade das respostas citadas;
3. redução de contexto redundante enviado à LLM;
4. manutenção de latência aceitável para produção.

## Sequência Recomendada de Implementação no Código

1. pipeline.py e search_service.py
2. context_service.py
3. retrieval_strategy.py e query_expansion.py
4. ingestion.py e chunking.py
5. reranker.py
6. context_compression.py e prompt_service.py
7. evaluation.py, repositories e frontend debug

## Próximo Passo Recomendado

Iniciar pela Fase 1 junto com a parte mínima da Fase 0. É o melhor ponto de equilíbrio entre impacto, risco e reaproveitamento do código já existente.