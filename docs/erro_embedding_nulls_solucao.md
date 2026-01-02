# Solução para Erro de Embedding com NULLs

## Problema Identificado

Durante a ingestão de documentos, o sistema estava retornando o erro:
```
[BACKEND] [13:59:03] WARNING  | rag.embeddings       | Embedding inválido no batch (index 332). Tentando recuperação individual...
[BACKEND] [13:59:04] ERROR    | rag.embeddings       | ERRO: Embedding inválido retornado após retry: contains NULLs
[BACKEND] [13:59:04] WARNING  | rag.embeddings       | CHUNK IGNORADO (Falha persistente no modelo) no index 332: 'ry scope elements implemented in the
```

## Causa Raiz

O modelo de embeddings (text-encoding-bge-m3 via LM Studio) estava retornando vetores com valores `None/NULL` em algumas posições. Isso ocorreu devido a:

1. **Textos muito pequenos ou fragmentados** (ex: `'ry scope elements implemented in the'` estava incompleto)
2. **Caracteres especiais** que passaram pela limpeza anterior
3. **Instabilidade do modelo/LM Studio** em casos de edge cases

## Soluções Implementadas

### 1. Limpeza Robusta de Texto (`get_embedding`)

**Antes:**
```python
text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
text = text.strip()
```

**Depois:**
```python
# 1. Remover caracteres não imprimíveis e de controle (exceto \n, \r, \t)
text = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
# 2. Normalizar espaços (múltiplos espaços viram um único)
text = re.sub(r'\s+', ' ', text)
text = text.strip()

# 3. Validar tamanho mínimo do texto (chunks muito pequenos causam problemas)
if len(text) < 10:
    embedding_logger.warning(f"Texto muito pequeno ({len(text)} chars) após limpeza. Retornando None.")
    return None

# 4. Validar conteúdo do texto (evitar chunks só com caracteres especiais)
if len(text.strip(' \n\r\t.,!?;:()[]{}<>"/\'-=+*&^%$#@|~`_')) < 5:
    embedding_logger.warning("Texto composto principalmente de caracteres especiais. Retornando None.")
    return None
```

### 2. Validação Detalhada de Embeddings

**Antes:**
```python
is_valid = (
    embedding is not None and 
    isinstance(embedding, list) and 
    len(embedding) > 0 and 
    not any(v is None for v in embedding)
)
```

**Depois:**
```python
# Validar embedding de forma mais detalhada
null_count = sum(1 for v in embedding if v is None)
nan_count = sum(1 for v in embedding if isinstance(v, float) and (v != v))  # NaN check
inf_count = sum(1 for v in embedding if isinstance(v, float) and (v == float('inf') or v == float('-inf')))

is_valid = (
    embedding is not None and 
    isinstance(embedding, list) and 
    len(embedding) > 0 and 
    null_count == 0 and
    nan_count == 0 and
    inf_count == 0
)
```

### 3. Logs Mais Informativos

**Antes:**
```python
embedding_logger.warning(f"Embedding inválido retornado para '{text_sample}'. Tentando retry único... Razão: {error_reason}")
```

**Depois:**
```python
embedding_logger.warning(
    f"Embedding inválido retornado para '{text_sample}'. "
    f"Texto: {len(text)} chars, Embedding: {len(embedding) if embedding else 0} dims. "
    f"Erro: {error_reason}. Tentando retry único..."
)
```

### 4. Validação Consistente em Batch Processing

A mesma validação robusta foi aplicada ao processamento em batch (`get_embeddings_batch`) para garantir consistência.

## Benefícios da Solução

1. **Prevenção de Erros**: Textos muito pequenos ou com muitos caracteres especiais são rejeitados antes de serem enviados ao modelo
2. **Debugging Melhor**: Logs detalhados informam:
   - Tamanho do texto original
   - Dimensões do embedding
   - Tipos específicos de erros (NULLs, NaNs, Infs)
   - Conteúdo do texto problemático
3. **Resiliência**: O sistema agora trata casos edge de forma mais robusta
4. **Consistência**: Validação uniforme entre processamento individual e em batch

## Próximos Passos Recomendados

1. **Monitoramento**: Acompanhar os logs para ver se ainda há chunks sendo rejeitados
2. **Análise de Documentos Problema**: Se muitos chunks forem rejeitados, investigar os documentos fonte
3. **Ajuste de Parâmetros**: Se necessário, ajustar os limites de tamanho mínimo (atualmente 10 caracteres)
4. **Verificação do LM Studio**: Garantir que o modelo está funcionando corretamente

## Como Testar

Após aplicar as mudanças:

1. Reinicie a aplicação
2. Execute a ingestão novamente
3. Monitore os logs para verificar se há avisos de chunks pequenos sendo rejeitados
4. Verifique se há logs de sucesso na recuperação de embeddings individuais

Se chunks ainda forem rejeitados, o log mostrará claramente qual foi o motivo (tamanho, caracteres especiais, etc.), permitindo ajustes específicos.
