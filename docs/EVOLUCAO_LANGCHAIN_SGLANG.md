# Evolução com LangChain e sglang

## Contexto atual
- Stack: Flask, LM Studio (endpoint compatível OpenAI), spaCy chunking, pgvector, chamadas HTTP diretas para LLM.
- Pipelines escritos à mão para ingest, retrieval e prompt orchestration.

## Por que considerar LangChain
- Blocos prontos: loaders de documentos, splitters, embeddings, retrievers (PGVector), re-rankers, tool-calling/agents, memórias.
- Observabilidade: callbacks/tracing (LangSmith) e streaming nativos.
- Composição: chains/runnables permitem trocar LLM, retriever ou parser com pouca mudança de código.

## Por que considerar sglang
- Servidor de inferência otimizado (HTTP/WebSocket) com batching, speculative decoding e cache KV para reduzir latência/custo.
- Mantém sua lógica de ingest/retrieval; troca apenas a etapa de geração.
- Pode rodar em container apontando para modelos locais (HF/LM Studio) ou remotos.

## Caminho de migração sugerido
1) **LLM**: expor LM Studio em modo OpenAI-like e trocar o cliente por `ChatOpenAI` (ou similar) no LangChain; opcionalmente, servir via sglang para ganho de performance.
2) **Retrieval**: usar `PGVector` retriever em vez de SQL manual; opcionalmente, adicionar re-ranking.
3) **Orquestração**: reescrever o prompt builder como `Runnable` (prompt template | retriever | llm | parser), com streaming e callbacks.
4) **Ingest**: loaders + splitters do LangChain; embeddings plugáveis; reuse do PGVector para indexação.
5) **Extras**: memória de conversa (`RunnableWithMessageHistory`), tool-calling/agents, tracing.

## Cenários recomendados
- **Produtividade/lego pronto**: LangChain para ingest/retrieval/orquestração; LLM local via LM Studio ou sglang como backend.
- **Performance de geração**: manter pipelines custom ou LangChain, mas servir o LLM via sglang (batching + speculative + cache KV).
- **Qualidade máxima**: speculative decoding com proposer menor (ex.: Phi 3.5 Mini) e verifier maior; re-ranking após retrieval.

## Próximos passos práticos
- Subir sglang em container apontando para o modelo local; validar latência e custo.
- Adaptar cliente LLM para endpoint OpenAI-like e testar uma chain simples no LangChain.
- Medir ganho com re-ranking e memória de conversação em diálogos longos.
