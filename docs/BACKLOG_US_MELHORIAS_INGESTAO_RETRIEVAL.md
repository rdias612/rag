# Backlog de USs - Melhorias de Ingestão e Retrieval

## Objetivo

Detalhar as fases do plano técnico em User Stories pequenas e executáveis, permitindo implementação incremental, priorização por impacto e validação por critérios objetivos.

## Convenções

- Prefixo: US-RAG-XXX
- Tipo: técnica, mas escrita no formato de User Story para facilitar gestão.
- Granularidade: cada US deve ser implementável e validável isoladamente.
- Dependências: sempre que uma US bloquear outra, isso deve ficar explícito.

## Sugestão de Campos para Gestão em ferramenta

- ID
- Título
- Fase
- Prioridade
- Dependências
- Arquivos alvo
- Critérios de aceite
- Métricas afetadas

---

## Fase 0 - Baseline, Instrumentação e Critérios de Qualidade

### US-RAG-001 - Definir conjunto base de perguntas de avaliação

Como time de engenharia, quero definir um conjunto padrão de perguntas de avaliação para medir retrieval e contexto antes e depois das mudanças.

Arquivos alvo:
- docs/PLANO_TECNICO_MELHORIAS_INGESTAO_RETRIEVAL.md
- tests/fixtures/
- tests/

Detalhamento:
- Criar conjunto mínimo de 30 perguntas.
- Distribuir perguntas por tipo: factual, definição, procedimento, comparação e explicação.
- Associar para cada pergunta pelo menos uma evidência esperada.

Critérios de aceite:
- Existe um arquivo versionado com o benchmark inicial.
- Cada pergunta possui categoria e evidência esperada.
- O benchmark pode ser reutilizado por testes automatizados.

Métricas afetadas:
- Recall@5
- Recall@10
- MRR

Dependências:
- Nenhuma.

### US-RAG-002 - Estruturar fixture de evidências esperadas

Como time de engenharia, quero armazenar evidências esperadas por pergunta para permitir avaliação offline do retrieval sem depender da resposta da LLM.

Arquivos alvo:
- tests/fixtures/retrieval_benchmark.json
- tests/fixtures/

Detalhamento:
- Definir schema com question, category, expected_source, expected_terms, expected_section opcional.
- Validar consistência mínima do arquivo.

Critérios de aceite:
- Fixture carrega em teste automatizado.
- Não há perguntas sem evidência associada.
- O schema é documentado no próprio arquivo ou em comentário adjacente.

Métricas afetadas:
- Recall benchmark
- Cobertura de benchmark

Dependências:
- US-RAG-001.

### US-RAG-003 - Expor métricas estruturadas do pipeline por etapa

Como time de engenharia, quero registrar métricas estruturadas do pipeline para comparar comportamento antes e depois das mudanças.

Arquivos alvo:
- src/core/rag/pipeline.py
- src/core/metrics.py

Detalhamento:
- Registrar candidatos iniciais.
- Registrar documentos após MMR/rerank.
- Registrar modo efetivo de busca.
- Registrar fontes únicas e duração por etapa.

Critérios de aceite:
- Logs e métricas identificam claramente cada etapa.
- É possível diferenciar busca inicial, refinamento, contexto e resposta.
- Não há quebra do fluxo atual.

Métricas afetadas:
- Latência P50/P95
- Candidates count
- Unique sources count

Dependências:
- Nenhuma.

### US-RAG-004 - Expor métricas do contexto montado

Como time de engenharia, quero medir a qualidade do contexto montado para detectar redundância, truncamento e cobertura.

Arquivos alvo:
- src/core/rag/services/context_service.py

Detalhamento:
- Medir número de blocos incluídos.
- Medir chars por bloco.
- Medir fontes únicas.
- Medir quantidade de conteúdo descartado por orçamento.

Critérios de aceite:
- O retorno interno do builder contém métricas de contexto.
- O pipeline consegue logar essas métricas.
- O comportamento atual permanece compatível.

Métricas afetadas:
- Context redundancy
- Context truncation rate
- Unique sources per response

Dependências:
- US-RAG-003.

### US-RAG-005 - Persistir métricas de retrieval/contexto em repositório de avaliação

Como time de engenharia, quero persistir dados de retrieval e contexto para análise histórica e comparação entre versões.

Arquivos alvo:
- src/data/repositories/evaluation_repository.py
- alembic/versions/ se necessário

Detalhamento:
- Salvar retrieval_mode efetivo.
- Salvar fontes únicas.
- Salvar redundância estimada.
- Salvar tamanho do contexto final.

Critérios de aceite:
- As novas métricas ficam disponíveis no banco ou storage atual.
- O salvamento não interrompe a query principal em caso de falha.
- Campos novos ficam documentados.

Métricas afetadas:
- Histórico de qualidade
- Comparação entre versões

Dependências:
- US-RAG-003
- US-RAG-004.

### US-RAG-006 - Criar teste smoke de retrieval quality

Como time de engenharia, quero um teste automatizado que valide o retrieval com benchmark mínimo para detectar regressões cedo.

Arquivos alvo:
- tests/test_retrieval_quality_smoke.py

Detalhamento:
- Carregar fixture de benchmark.
- Executar retrieval sem geração final da LLM quando possível.
- Comparar resultado com evidências esperadas.

Critérios de aceite:
- Teste executa localmente.
- Teste falha quando retrieval perde evidências críticas do benchmark.
- Saída aponta perguntas com pior desempenho.

Métricas afetadas:
- Recall@K
- MRR

Dependências:
- US-RAG-001
- US-RAG-002.

### US-RAG-007 - Criar teste smoke de context builder quality

Como time de engenharia, quero validar o builder de contexto de forma automatizada para garantir que orçamento e diversidade funcionem corretamente.

Arquivos alvo:
- tests/test_context_builder_quality.py

Detalhamento:
- Verificar limites por fonte.
- Verificar limites totais de caracteres.
- Verificar diversidade de fontes e estabilidade de ordenação.

Critérios de aceite:
- Teste cobre truncamento e priorização.
- Teste falha se builder gerar contexto redundante acima do esperado em cenários artificiais.

Métricas afetadas:
- Context redundancy
- Context truncation rate

Dependências:
- US-RAG-004.

---

## Fase 1 - Retrieval Hierárquico Real

### US-RAG-008 - Identificar e encapsular o modo hierarchical no pipeline

Como time de engenharia, quero que o pipeline trate explicitamente o modo hierarchical para que a expansão child para parent fique clara e controlável.

Arquivos alvo:
- src/core/rag/pipeline.py

Detalhamento:
- Separar o fluxo hierarchical do fluxo sentence e do fluxo genérico.
- Aplicar flag de feature para rollback rápido.

Critérios de aceite:
- O código do pipeline deixa explícito quando a expansão hierárquica é usada.
- Existe flag de configuração para habilitar/desabilitar a lógica.

Métricas afetadas:
- Latência por modo
- Volume de documentos por modo

Dependências:
- US-RAG-003.

### US-RAG-009 - Implementar recuperação de chunks filhos para o modo hierarchical

Como time de engenharia, quero recuperar chunks filhos como primeira etapa da busca hierarchical para manter precisão local na localização da evidência.

Arquivos alvo:
- src/core/rag/services/search_service.py
- src/data/repositories/document_repository.py

Detalhamento:
- Buscar apenas child chunks no fluxo hierarchical.
- Preservar similarity e metadata original.

Critérios de aceite:
- Busca hierarchical não retorna chunks parent diretamente na etapa inicial.
- Resultados trazem parent_index e source_path quando disponíveis.

Métricas afetadas:
- Candidate precision
- Child hit rate

Dependências:
- US-RAG-008.

### US-RAG-010 - Implementar deduplicação por source_path e parent_index

Como time de engenharia, quero deduplicar hits por pai lógico para evitar multiplicidade artificial de chunks filhos da mesma região documental.

Arquivos alvo:
- src/core/rag/services/search_service.py
- src/data/hierarchical_chunking.py

Detalhamento:
- Deduplicar por combinação source_path + parent_index.
- Preservar melhor score do child que ganhou a vaga.

Critérios de aceite:
- Não existem pais repetidos na lista expandida.
- O score do melhor child é mantido para ordenação do parent.

Métricas afetadas:
- Context redundancy
- Parent diversity

Dependências:
- US-RAG-009.

### US-RAG-011 - Implementar recuperação em lote dos chunks pais

Como time de engenharia, quero recuperar chunks pais em lote para evitar round-trips excessivos ao banco no modo hierarchical.

Arquivos alvo:
- src/data/repositories/document_repository.py

Detalhamento:
- Criar get_parent_contents_batch.
- Permitir entrada em lote por source_path e parent_index.

Critérios de aceite:
- Método em lote retorna os mesmos pais que a recuperação individual.
- A busca hierarchical não executa uma query por parent quando o método em lote estiver disponível.

Métricas afetadas:
- DB round-trips
- Latência P95 hierarchical

Dependências:
- US-RAG-010.

### US-RAG-012 - Expandir resultados child para parent no search service

Como time de engenharia, quero que o search service devolva o contexto hierarchical já expandido para pais, pronto para o builder de contexto.

Arquivos alvo:
- src/core/rag/services/search_service.py
- src/data/hierarchical_chunking.py

Detalhamento:
- Criar search_with_hierarchical_context.
- Devolver parent content, metadata do pai e metadata do child de origem.

Critérios de aceite:
- Fluxo hierarchical retorna parents deduplicados.
- Resultado inclui found_via_child ou estrutura equivalente.

Métricas afetadas:
- Hierarchical recall@K
- Groundedness em perguntas explicativas

Dependências:
- US-RAG-011.

### US-RAG-013 - Integrar expansão parent ao pipeline principal

Como time de engenharia, quero integrar a expansão hierarchical ao pipeline principal para que a LLM receba contexto suficiente em perguntas explicativas.

Arquivos alvo:
- src/core/rag/pipeline.py

Detalhamento:
- Substituir o retorno atual do fluxo hierarchical por resultados parent expandido.
- Registrar métricas antes/depois da expansão.

Critérios de aceite:
- Perguntas em modo hierarchical chegam à montagem de contexto com blocks parent.
- Métricas mostram child count e parent count.

Métricas afetadas:
- Recall@5 em explicativas
- Respostas incompletas por falta de contexto

Dependências:
- US-RAG-012.

### US-RAG-014 - Criar testes de regressão do retrieval hierárquico

Como time de engenharia, quero testes específicos do fluxo hierarchical para evitar regressões na expansão child para parent.

Arquivos alvo:
- tests/test_hierarchical_retrieval_pipeline.py

Detalhamento:
- Cobrir hit simples.
- Cobrir múltiplos children do mesmo pai.
- Cobrir ausência de parent.
- Cobrir ordenação por melhor child.

Critérios de aceite:
- Testes passam com o novo fluxo.
- Casos de deduplicação ficam cobertos.

Métricas afetadas:
- Confiabilidade do fluxo hierarchical

Dependências:
- US-RAG-013.

---

## Fase 2 - Query Expansion no Fluxo Principal

### US-RAG-015 - Ativar implementação real de query expansion na estratégia de retrieval

Como time de engenharia, quero substituir o placeholder atual por um fluxo real de query expansion para elevar recall sem depender de Self-RAG.

Arquivos alvo:
- src/core/rag/strategies/retrieval_strategy.py

Detalhamento:
- Gerar variações.
- Buscar por variação.
- Fundir por RRF.
- Seguir para MMR e rerank.

Critérios de aceite:
- O placeholder deixa de existir.
- Query expansion participa do fluxo principal quando habilitado.

Métricas afetadas:
- Recall@10
- MRR

Dependências:
- US-RAG-006.

### US-RAG-016 - Fortalecer parser de variações geradas pelo LLM

Como time de engenharia, quero parsear de forma robusta as variações da query para evitar lixo, duplicatas ou variações vazias.

Arquivos alvo:
- src/core/query_expansion.py

Detalhamento:
- Limpar bullets e numeração.
- Filtrar linhas vazias.
- Deduplicar texto normalizado.

Critérios de aceite:
- Parser remove duplicatas exatas.
- Parser ignora linhas vazias ou inválidas.
- A query original permanece sempre presente.

Métricas afetadas:
- Expansion quality
- Effective query count

Dependências:
- US-RAG-015.

### US-RAG-017 - Limitar variações por tipo de pergunta

Como time de engenharia, quero modular a quantidade de variações por tipo de pergunta para equilibrar recall e latência.

Arquivos alvo:
- src/core/query_expansion.py
- src/core/rag/pipeline.py
- src/config.py

Detalhamento:
- Definir política por factual, procedure e explicativa.
- Restringir variações em queries já muito específicas.

Critérios de aceite:
- A política por tipo é configurável.
- Queries factuais curtas não explodem em variações sem ganho justificável.

Métricas afetadas:
- P95 latency
- Recall por tipo de pergunta

Dependências:
- US-RAG-016.

### US-RAG-018 - Adicionar configuração fina de query expansion

Como time de engenharia, quero expor flags e limites de query expansion para rollout controlado e tuning posterior.

Arquivos alvo:
- src/config.py

Detalhamento:
- Adicionar flags e limites.
- Definir defaults seguros.

Critérios de aceite:
- Configuração fica disponível via settings.
- O sistema continua compatível com comportamento anterior quando desabilitado.

Métricas afetadas:
- Rollout control
- A/B capability

Dependências:
- US-RAG-017.

### US-RAG-019 - Registrar métricas de expansão e fusão

Como time de engenharia, quero medir o efeito da expansão da query e da fusão dos resultados para validar ganho real.

Arquivos alvo:
- src/core/rag/pipeline.py
- src/core/rag/strategies/retrieval_strategy.py

Detalhamento:
- Logar quantidade de variações.
- Logar documentos retornados por variação.
- Logar ganho de cobertura após RRF.

Critérios de aceite:
- Métricas deixam visível o custo e o ganho da expansão.
- É possível comparar query normal versus expandida.

Métricas afetadas:
- Query expansion gain
- Coverage delta

Dependências:
- US-RAG-015.

### US-RAG-020 - Atualizar testes de query expansion para o novo fluxo

Como time de engenharia, quero ampliar os testes de query expansion para cobrir o parser e o fluxo principal.

Arquivos alvo:
- tests/test_query_expansion.py

Detalhamento:
- Cobrir duplicatas.
- Cobrir linhas inválidas.
- Cobrir queries factuais curtas e queries longas.

Critérios de aceite:
- Testes passam no novo fluxo.
- Casos de borda ficam documentados por teste.

Métricas afetadas:
- Robustez do parser

Dependências:
- US-RAG-016
- US-RAG-017.

---

## Fase 3 - Montagem de Contexto por Blocos de Evidência

### US-RAG-021 - Definir modelo lógico de bloco de evidência

Como time de engenharia, quero padronizar o formato de bloco de evidência para que o builder e o prompt trabalhem com a mesma estrutura.

Arquivos alvo:
- src/core/rag/services/context_service.py
- docs/

Detalhamento:
- Definir campos obrigatórios e opcionais.
- Padronizar nomes como source, relevance, chunk_type, section_title e excerpt.

Critérios de aceite:
- O formato está documentado e refletido no código.
- O builder consegue montar blocos homogêneos a partir de resultados heterogeneous.

Métricas afetadas:
- Auditabilidade do contexto

Dependências:
- US-RAG-004.

### US-RAG-022 - Refatorar build_context para trabalhar com evidências em vez de concatenação simples

Como time de engenharia, quero que o contexto final seja composto por blocos de evidência estruturados, e não apenas por concatenação sequencial de conteúdo.

Arquivos alvo:
- src/core/rag/services/context_service.py

Detalhamento:
- Transformar cada documento recuperado em bloco.
- Incluir cabeçalho de evidência, fonte, tipo, score e trecho.

Critérios de aceite:
- O contexto final fica estruturado por evidências.
- O builder mantém compatibilidade com o prompt atual ou adapta o prompt em follow-up controlado.

Métricas afetadas:
- Context readability
- Citation supportability

Dependências:
- US-RAG-021.

### US-RAG-023 - Implementar orçamento de contexto por bloco e por fonte

Como time de engenharia, quero limitar o contexto por bloco e por fonte para evitar que um único documento domine a resposta final.

Arquivos alvo:
- src/core/rag/services/context_service.py
- src/config.py

Detalhamento:
- Definir max blocks total.
- Definir max blocks por source.
- Definir max chars por bloco.

Critérios de aceite:
- Builder respeita os limites configurados.
- Cenários com uma única fonte dominante mantêm diversidade mínima quando possível.

Métricas afetadas:
- Unique sources per response
- Context redundancy

Dependências:
- US-RAG-022.

### US-RAG-024 - Integrar metadados contextuais ao contexto final

Como time de engenharia, quero usar section_title e resumos de vizinhança para tornar cada evidência mais informativa sem inflar demais o contexto.

Arquivos alvo:
- src/core/rag/services/context_service.py
- src/data/chunking.py
- src/data/ingestion.py

Detalhamento:
- Incluir metadata relevante no bloco quando disponível.
- Omitir campos vazios para não poluir o prompt.

Critérios de aceite:
- Section title aparece em blocos quando existir.
- Prev/next summaries são usados apenas quando habilitados.

Métricas afetadas:
- Context utility
- Groundedness em perguntas explicativas

Dependências:
- US-RAG-022.

### US-RAG-025 - Expor configuração do builder de contexto

Como time de engenharia, quero controlar orçamento e comportamento do builder via configuração para rollout gradual e tuning posterior.

Arquivos alvo:
- src/config.py

Detalhamento:
- Adicionar parâmetros do builder.
- Publicar defaults seguros.

Critérios de aceite:
- Todos os limites usados pelo builder são configuráveis.
- Defaults preservam comportamento estável quando o modo novo estiver desligado.

Métricas afetadas:
- Rollout control

Dependências:
- US-RAG-023.

### US-RAG-026 - Criar testes do builder de evidências

Como time de engenharia, quero testes específicos do novo builder para validar ordenação, truncamento e preservação de metadados.

Arquivos alvo:
- tests/test_context_builder_quality.py
- tests/ novos casos se necessário

Detalhamento:
- Cobrir ordem dos blocos.
- Cobrir limites por fonte.
- Cobrir campos opcionais.

Critérios de aceite:
- Casos principais do builder ficam testados.
- Falhas de regressão ficam fáceis de localizar.

Métricas afetadas:
- Robustez do contexto estruturado

Dependências:
- US-RAG-024
- US-RAG-025.

---

## Fase 4 - Ingestão com Preservação de Estrutura Documental

### US-RAG-027 - Separar pipeline de ingestão em etapas explícitas

Como time de engenharia, quero separar extração, limpeza, normalização, chunking e enrichment para facilitar evolução da ingestão sem aumentar acoplamento.

Arquivos alvo:
- src/data/ingestion.py

Detalhamento:
- Organizar o fluxo em funções internas ou componentes claros.
- Evitar monolito de processamento por documento.

Critérios de aceite:
- O código de ingestão fica modularizado.
- A execução atual continua funcionando após refatoração.

Métricas afetadas:
- Maintainability
- Extensibilidade da ingestão

Dependências:
- Nenhuma.

### US-RAG-028 - Enriquecer chunks hierarchical com section_title e vizinhança

Como time de engenharia, quero que chunks hierarchical saiam da ingestão com metadados contextuais úteis para retrieval e contexto final.

Arquivos alvo:
- src/data/ingestion.py
- src/data/chunking.py

Detalhamento:
- Aplicar add_contextual_metadata ao fluxo hierarchical.
- Manter section_title, prev_summary, next_summary, total_chunks.

Critérios de aceite:
- Chunks hierarchical persistidos carregam os novos metadados quando disponíveis.
- Não há quebra em documentos antigos ou sem metadados ricos.

Métricas afetadas:
- Metadata coverage
- Context utility

Dependências:
- US-RAG-027.

### US-RAG-029 - Enriquecer chunks sentence com metadados estruturais compatíveis

Como time de engenharia, quero que sentence chunks também tragam metadados consistentes de posição e seção para permitir uso homogêneo no contexto final.

Arquivos alvo:
- src/data/ingestion.py
- src/data/sentence_window.py

Detalhamento:
- Incluir section_title quando detectável.
- Preservar sentence_index, total_sentences e page range.

Critérios de aceite:
- Sentence chunks ficam compatíveis com o builder de evidência.
- Metadados de posição continuam corretos.

Métricas afetadas:
- Sentence metadata coverage

Dependências:
- US-RAG-027.

### US-RAG-030 - Melhorar heurísticas de preservação de listas, títulos e blocos estruturais

Como time de engenharia, quero evitar chunk boundaries ruins em listas, títulos e blocos especiais para que o retrieval recupere contexto mais coeso.

Arquivos alvo:
- src/data/chunking.py

Detalhamento:
- Evitar quebra no meio de listas.
- Preservar cabeçalhos adjacentes.
- Melhorar agrupamento de sentenças com números e referências.

Critérios de aceite:
- Benchmark sintético mostra queda de cortes ruins.
- Chunking continua performático.

Métricas afetadas:
- Chunk boundary error rate
- Coesão semântica dos chunks

Dependências:
- US-RAG-027.

### US-RAG-031 - Introduzir metadata de proveniência estrutural adicional

Como time de engenharia, quero armazenar page_start, page_end, heading_path e content_type para melhorar citação, filtragem e explicabilidade.

Arquivos alvo:
- src/data/ingestion.py
- src/data/repositories/document_repository.py

Detalhamento:
- Acrescentar novos campos ao metadata JSON.
- Garantir leitura consistente no retrieval.

Critérios de aceite:
- Novos documentos persistem os campos extras quando disponíveis.
- Retrieval e builder não quebram se campos estiverem ausentes.

Métricas afetadas:
- Citation quality
- Provenance coverage

Dependências:
- US-RAG-028
- US-RAG-029.

### US-RAG-032 - Criar testes de ingestão estruturada

Como time de engenharia, quero testes da nova ingestão estruturada para garantir estabilidade dos metadados e da qualidade de chunking.

Arquivos alvo:
- tests/test_structured_ingestion_metadata.py
- tests/test_chunking_comparison.py

Detalhamento:
- Cobrir hierarchical e sentence.
- Cobrir section_title.
- Cobrir prev/next summaries.

Critérios de aceite:
- Testes passam em cenários representativos.
- Diferenças de chunking ficam visíveis em asserts claros.

Métricas afetadas:
- Metadata coverage
- Chunk quality regression

Dependências:
- US-RAG-031.

---

## Fase 5 - Reranking Real e Política de Fusão

### US-RAG-033 - Priorizar cross-encoder dedicado no reranking

Como time de engenharia, quero usar um reranker dedicado para melhorar a ordenação final com mais consistência que LLM-as-reranker.

Arquivos alvo:
- src/core/reranker.py
- src/config.py

Detalhamento:
- Tornar API de rerank o caminho preferencial.
- Preservar fallback quando indisponível.

Critérios de aceite:
- Quando endpoint dedicado estiver configurado, ele é usado como padrão.
- Falhas no serviço de rerank não derrubam a query principal.

Métricas afetadas:
- nDCG@10
- Precision@3

Dependências:
- US-RAG-015.

### US-RAG-034 - Registrar score original e rerank_score separadamente

Como time de engenharia, quero preservar score semântico original e rerank_score para análise de qualidade e tuning do ranking.

Arquivos alvo:
- src/core/reranker.py
- src/core/rag/strategies/retrieval_strategy.py

Detalhamento:
- Não sobrescrever similarity original.
- Tornar visível a contribuição do rerank.

Critérios de aceite:
- Resultado final inclui ambos os scores quando reranking estiver ativo.
- Logs deixam claro quando houve reorder real.

Métricas afetadas:
- Rerank impact analysis

Dependências:
- US-RAG-033.

### US-RAG-035 - Formalizar ordem da política de fusão e refinamento

Como time de engenharia, quero padronizar a ordem RRF -> MMR -> rerank para evitar pipelines inconsistentes entre modos de busca.

Arquivos alvo:
- src/core/rag/strategies/retrieval_strategy.py

Detalhamento:
- Definir ordem única no código.
- Tornar cada etapa observável por métrica.

Critérios de aceite:
- Pipeline de refinamento fica explícito.
- Ordem é a mesma para os casos em que as etapas estiverem habilitadas.

Métricas afetadas:
- Ranking consistency
- nDCG@10

Dependências:
- US-RAG-015
- US-RAG-033.

### US-RAG-036 - Cobrir reranking com testes de regressão mínimos

Como time de engenharia, quero validar o reranking por testes mínimos para evitar perda silenciosa de ordenação.

Arquivos alvo:
- tests/test_reranking_pipeline.py

Detalhamento:
- Cobrir cenário com reorder.
- Cobrir fallback sem endpoint.
- Cobrir preservação de scores.

Critérios de aceite:
- Testes passam em modo mockado.
- Reorder esperado fica verificável.

Métricas afetadas:
- Confiabilidade do reranking

Dependências:
- US-RAG-034
- US-RAG-035.

---

## Fase 6 - Compressão de Contexto e Prompt Final

### US-RAG-037 - Corrigir compatibilidade entre context service e context compression

Como time de engenharia, quero alinhar a interface entre o serviço de contexto e a compressão para evitar falhas e comportamento ambíguo.

Arquivos alvo:
- src/core/rag/services/context_service.py
- src/core/context_compression.py

Detalhamento:
- Revisar assinatura da função.
- Revisar retorno esperado.
- Garantir consistência entre chamador e implementador.

Critérios de aceite:
- A compressão pode ser chamada pelo serviço sem erro de interface.
- O retorno possui contrato estável.

Métricas afetadas:
- Compression success rate

Dependências:
- US-RAG-022.

### US-RAG-038 - Implementar compressão por bloco de evidência

Como time de engenharia, quero comprimir contexto em nível de bloco para preservar evidências importantes sem resumir tudo como texto achatado.

Arquivos alvo:
- src/core/context_compression.py

Detalhamento:
- Permitir compressão seletiva por bloco.
- Preservar cabeçalho de fonte e relevância.

Critérios de aceite:
- A compressão não destrói a estrutura de evidência.
- Blocos relevantes continuam rastreáveis após compressão.

Métricas afetadas:
- Compression ratio
- Groundedness after compression

Dependências:
- US-RAG-037.

### US-RAG-039 - Implementar fallback heurístico de compressão sem LLM

Como time de engenharia, quero uma estratégia heurística de compressão para reduzir risco operacional quando a LLM de compressão falhar ou estiver indisponível.

Arquivos alvo:
- src/core/context_compression.py

Detalhamento:
- Reusar ou melhorar extração de sentenças-chave.
- Permitir seleção determinística por relevância local.

Critérios de aceite:
- Existe fallback sem LLM.
- O fallback é acionável por configuração ou indisponibilidade do modo principal.

Métricas afetadas:
- Compression availability
- Fallback quality

Dependências:
- US-RAG-037.

### US-RAG-040 - Ajustar prompt para consumir contexto estruturado e conflitos de evidência

Como time de engenharia, quero adaptar o prompt final para interpretar blocos de evidência, priorizar fontes fortes e mencionar conflitos documentais quando existirem.

Arquivos alvo:
- src/core/rag/services/prompt_service.py
- src/config.py

Detalhamento:
- Instruir a LLM a usar blocos e citações.
- Instruir a explicitar divergências entre fontes.

Critérios de aceite:
- Prompt final consome o novo formato sem ambiguidade.
- Respostas continuam exigindo fidelidade ao contexto.

Métricas afetadas:
- Citation correctness
- Conflict handling quality

Dependências:
- US-RAG-022
- US-RAG-038.

### US-RAG-041 - Criar testes de regressão para compressão e prompt final

Como time de engenharia, quero validar que compressão e prompt estruturado não degradam o comportamento em cenários básicos.

Arquivos alvo:
- tests/test_context_compression_v2.py
- tests/ conforme necessário

Detalhamento:
- Cobrir contrato de retorno.
- Cobrir fallback heurístico.
- Cobrir preservação de cabeçalhos de evidência.

Critérios de aceite:
- Testes passam nos dois modos de compressão.
- Casos básicos de contexto estruturado seguem íntegros.

Métricas afetadas:
- Compression regression safety

Dependências:
- US-RAG-039
- US-RAG-040.

---

## Fase 7 - Avaliação Contínua e Operação

### US-RAG-042 - Estender avaliação para retrieval e contexto além da resposta final

Como time de engenharia, quero avaliar retrieval e contexto separadamente da resposta final para localizar falhas na etapa certa do pipeline.

Arquivos alvo:
- src/core/evaluation.py
- src/data/repositories/evaluation_repository.py

Detalhamento:
- Avaliar cobertura de evidência.
- Avaliar diversidade e redundância do contexto.
- Separar qualidade de retrieval de qualidade de resposta.

Critérios de aceite:
- Modelo de avaliação diferencia as etapas.
- Resultado persistido permite análise por camada.

Métricas afetadas:
- Retrieval quality trend
- Context quality trend

Dependências:
- US-RAG-005
- US-RAG-026.

### US-RAG-043 - Expor evidências e métricas no modo debug do frontend

Como time de engenharia e operação, quero visualizar candidatos, evidências finais e contexto enviado à LLM para acelerar tuning e troubleshooting.

Arquivos alvo:
- frontend/src/
- endpoints da API se necessário

Detalhamento:
- Exibir top candidatos.
- Exibir evidências finais usadas.
- Exibir fontes únicas e contexto final.

Critérios de aceite:
- Modo debug mostra dados suficientes para análise.
- Dados não aparecem para usuário comum fora do modo debug.

Métricas afetadas:
- Tempo de troubleshooting
- Operabilidade do sistema

Dependências:
- US-RAG-003
- US-RAG-004
- US-RAG-042.

### US-RAG-044 - Documentar playbook de tuning operacional

Como time de engenharia, quero documentar como ajustar top_k, alpha, chunk sizes, query expansion e reranking para manter evolução previsível do sistema.

Arquivos alvo:
- docs/

Detalhamento:
- Documentar parâmetros-chave.
- Relacionar sintomas a possíveis ajustes.
- Incluir sequência recomendada de tuning.

Critérios de aceite:
- Existe playbook técnico no repositório.
- Time consegue usar o documento para tuning sem depender de conhecimento oral.

Métricas afetadas:
- Tempo de ajuste
- Reprodutibilidade de tuning

Dependências:
- US-RAG-042.

### US-RAG-045 - Criar relatório consolidado de baseline versus pós-implementação

Como time de engenharia, quero um relatório comparando baseline e nova arquitetura para comprovar ganho e orientar próximos investimentos.

Arquivos alvo:
- docs/
- scripts/ se necessário

Detalhamento:
- Consolidar métricas de retrieval.
- Consolidar métricas de contexto.
- Destacar ganhos e regressões.

Critérios de aceite:
- Existe relatório reproduzível usando benchmark versionado.
- O relatório diferencia ganho por fase e por tipo de pergunta.

Métricas afetadas:
- All program KPIs

Dependências:
- US-RAG-042.

---

## Ordem Recomendada de Execução das USs

### Onda 1 - Baseline e segurança de mudança

1. US-RAG-001
2. US-RAG-002
3. US-RAG-003
4. US-RAG-004
5. US-RAG-006
6. US-RAG-007
7. US-RAG-005

### Onda 2 - Maior impacto funcional imediato

1. US-RAG-008
2. US-RAG-009
3. US-RAG-010
4. US-RAG-011
5. US-RAG-012
6. US-RAG-013
7. US-RAG-014

### Onda 3 - Recall adicional

1. US-RAG-015
2. US-RAG-016
3. US-RAG-017
4. US-RAG-018
5. US-RAG-019
6. US-RAG-020

### Onda 4 - Melhorar o material enviado à LLM

1. US-RAG-021
2. US-RAG-022
3. US-RAG-023
4. US-RAG-024
5. US-RAG-025
6. US-RAG-026

### Onda 5 - Melhorar a origem dos chunks

1. US-RAG-027
2. US-RAG-028
3. US-RAG-029
4. US-RAG-030
5. US-RAG-031
6. US-RAG-032

### Onda 6 - Refinamento de ranking e compressão

1. US-RAG-033
2. US-RAG-034
3. US-RAG-035
4. US-RAG-036
5. US-RAG-037
6. US-RAG-038
7. US-RAG-039
8. US-RAG-040
9. US-RAG-041

### Onda 7 - Operação contínua

1. US-RAG-042
2. US-RAG-043
3. US-RAG-044
4. US-RAG-045

---

## Priorização por Valor

### Valor Muito Alto

- US-RAG-013
- US-RAG-015
- US-RAG-022
- US-RAG-023
- US-RAG-037

### Valor Alto

- US-RAG-011
- US-RAG-024
- US-RAG-028
- US-RAG-029
- US-RAG-033

### Valor Médio

- US-RAG-030
- US-RAG-031
- US-RAG-039
- US-RAG-043
- US-RAG-044

## Observação Final

Se for necessário reduzir risco de rollout, a divisão mínima recomendada para os primeiros incrementos é:

1. Baseline e testes.
2. Retrieval hierarchical real.
3. Builder de contexto por evidência.
4. Query expansion principal.

Essa sequência tende a maximizar ganho na qualidade do contexto enviado à LLM antes de partir para refinamentos mais sofisticados.