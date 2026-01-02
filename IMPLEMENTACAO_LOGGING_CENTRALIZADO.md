# Implementação de Logging Centralizado

## Visão Geral

Sistema de logging centralizado implementado para o projeto RAG, consolidando todos os logs em apenas 2 arquivos:
- `server.log` - Todos os logs do backend
- `webserver.log` - Todos os logs do frontend (enviados via API)

## Estrutura Final de Logs

```
logs/
├── server.log         ← Backend (rag.api, rag.llm, rag.database, rag.pipeline, etc.)
└── webserver.log      ← Frontend (App, UploadModal, DocumentsPanel, etc.)
```

## Backend (Python)

### Modificações em `src/core/logger.py`

1. **Função `setup_logger` atualizada**:
   - Novo parâmetro `log_file` para especificar o arquivo de destino
   - Todos os loggers do backend agora usam `server.log`

2. **Novo logger `webserver_logger`**:
   - Configurado para escrever em `webserver.log`
   - Recebe logs enviados pelo frontend

3. **Formato de log simplificado**:
   - Antes: `timestamp level logger message | data={...}`
   - Depois: `timestamp level logger message {...}`

### Loggers Backend (todos em server.log)

- `rag` - Logger genérico
- `rag.llm` - Interações com LLM
- `rag.database` - Operações de banco de dados
- `rag.embeddings` - Geração de embeddings
- `rag.api` - Requisições da API
- `rag.pipeline` - Pipeline RAG
- `rag.ingestion` - Ingestão de documentos
- `rag.security` - Operações de segurança

## Frontend (TypeScript)

### Novo Arquivo: `frontend/src/logger.ts`

**Sistema de logging com as seguintes características:**

1. **Níveis de log**: DEBUG, INFO, WARNING, ERROR
2. **Buffer automático**: Logs são enfileirados e enviados em batch
3. **Flush periódico**: Envia logs a cada 5 segundos
4. **Flush imediato**: Envia quando a fila atinge 50 logs
5. **Flush no beforeunload**: Usa `sendBeacon` para enviar ao fechar página
6. **Console logging**: Mantém logs no console do navegador para debug

**Funções disponíveis:**
- `logger.debug(message, data?)`
- `logger.info(message, data?)`
- `logger.warning(message, data?)`
- `logger.error(message, error?)`

### Componentes Atualizados

Todos os componentes que usavam `console.*` foram atualizados:

1. **App.tsx** - Logger: "App"
2. **UploadModal.tsx** - Logger: "UploadModal"
3. **EvaluationModal.tsx** - Logger: "EvaluationModal"
4. **SystemOverview.tsx** - Logger: "SystemOverview"
5. **SessionsPanel.tsx** - Logger: "SessionsPanel"
6. **QualityMetricsPanel.tsx** - Logger: "QualityMetricsPanel"
7. **PromptsManagement.tsx** - Logger: "PromptsManagement"
8. **DocumentsPanel.tsx** - Logger: "DocumentsPanel"

## Backend API - Endpoint de Logs

### Novo Arquivo: `src/api/routes/logs.py`

**Endpoint: `POST /api/logs`**

Recebe um array de logs do frontend e escreve em `webserver.log`.

**Formato do payload:**
```json
{
  "logs": [
    {
      "timestamp": "2026-01-02T16:00:00.000Z",
      "level": "INFO",
      "component": "App",
      "message": "User clicked button",
      "data": {...}
    }
  ]
}
```

### Integração

A rota foi registrada em `src/api/routes/__init__.py`:
```python
from src.api.routes.logs import init_logs_routes

# Registrar rota de logs (recebe logs do frontend)
init_logs_routes(api)
```

## Formato dos Logs

### Backend (server.log)
```
2026-01-02T16:00:00.000Z INFO rag.api API Request endpoint=/api/query method=POST body_preview={...}
2026-01-02T16:00:01.000Z INFO rag.llm LLM Request model=gpt-4 prompt_length=100 prompt_full="..." parameters={...}
2026-01-02T16:00:02.000Z DEBUG rag.database DB SELECT query="SELECT * FROM documents" params_count=0
```

### Frontend (webserver.log)
```
2026-01-02T16:00:00.000Z INFO App Failed to load sessions {...}
2026-01-02T16:00:01.000Z ERROR UploadModal Upload failed {...}
2026-01-02T16:00:02.000Z INFO DocumentsPanel Error starting ingestion {...}
```

## Vantagens da Implementação

### Backend
1. **Centralização**: Todos os logs em um único arquivo facilita análise
2. **Identificação**: Nome do logger permite filtrar por componente (grep "rag.llm")
3. **Formato limpo**: Remove redundância de `data=`
4. **Flush garantido**: Função `flush_loggers()` garante que logs não se percam

### Frontend
1. **Persistência**: Logs do navegador são salvos no backend
2. **Performance**: Batch e buffer reduzem número de requisições
3. **Resiliência**: Logs são reenfileirados se a requisição falhar
4. **Debug**: Continua usando console para desenvolvimento
5. **No data loss**: sendBeacon garante envio antes de fechar página

## Como Usar

### Em componentes frontend:

```typescript
import { createLogger } from './logger';

const logger = createLogger('NomeDoComponente');

// Usar
logger.info('Operação realizada', { details: '...' });
logger.error('Erro ocorreu', error);
```

### Em código backend:

```python
from src.core.logger import api_logger, llm_logger, db_logger

# Usar
api_logger.info('API Request received')
llm_logger.info('LLM request sent', {'model': 'gpt-4'})
db_logger.debug('Query executed')
```

## Arquivos Antigos (a serem removidos)

O sistema criava anteriormente 8 arquivos de log separados:
- `rag.log`
- `rag_api.log`
- `rag_database.log`
- `rag_embeddings.log`
- `rag_ingestion.log`
- `rag_llm.log`
- `rag_pipeline.log`
- `rag_security.log`

Agora todos esses logs estão consolidados em `server.log`.

## Comandos Úteis

### Ver logs do backend em tempo real:
```bash
tail -f logs/server.log
```

### Ver logs do frontend em tempo real:
```bash
tail -f logs/webserver.log
```

### Filtrar logs por componente:
```bash
# Apenas logs de API
grep "rag.api" logs/server.log

# Apenas erros
grep "ERROR" logs/server.log

# Apenas logs de um componente frontend
grep "DocumentsPanel" logs/webserver.log
```

### Contar erros:
```bash
grep -c "ERROR" logs/server.log
grep -c "ERROR" logs/webserver.log
```

## Considerações

### Rotação de Logs

Atualmente não implementada. Para futuro:
- Usar `RotatingFileHandler` do Python
- Configurar tamanho máximo (ex: 10MB)
- Manter N backups
- Compressão de logs antigos

### Performance

- Frontend usa batch de até 50 logs
- Flush automático a cada 5 segundos
- Requisições falhadas são reenfileiradas
- Não impacta significativamente a performance da aplicação

### Segurança

- Logs podem conter dados sensíveis
- Considerar remover ou mascarar dados de usuários em produção
- Implementar autenticação para endpoint `/api/logs` se necessário

## Testes Realizados

1. ✅ Backend logger configurado corretamente
2. ✅ Frontend logger criado e integrado
3. ✅ Endpoint de logs funcionando
4. ✅ Todos os componentes frontend atualizados
5. ✅ TypeScript sem erros de compilação
6. ✅ Formato de log simplificado implementado

## Próximos Passos (Opcionais)

1. Implementar rotação automática de logs
2. Adicionar métricas de volume de logs
3. Criar dashboard para visualização de logs
4. Implementar alerts automáticos baseados em logs
5. Considerar logging estruturado (JSON) para melhor parse
