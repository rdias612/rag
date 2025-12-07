# 🚀 Novas Sugestões de Melhorias - RAG v2

Após implementação das Fases 1-4 (12 módulos), novas melhorias identificadas:

---

## 1. 📁 Multi-tenancy (Coleções Separadas)

### O Problema Atual
Hoje, todos os documentos ingeridos vão para a **mesma tabela** no banco de dados. Isso significa que:
- Se você tiver 2 projetos diferentes (ex: "Documentação Técnica" e "Manuais de RH"), as buscas misturam resultados dos dois
- Não há isolamento - uma pergunta sobre RH pode retornar chunks de documentação técnica
- Difícil de gerenciar permissões ou limpar documentos de um projeto específico

### A Solução
Adicionar um campo `collection_id` aos documentos:
```sql
ALTER TABLE documents ADD COLUMN collection_id VARCHAR(100);
CREATE INDEX idx_collection ON documents(collection_id);
```

A API passaria a aceitar:
```json
{
  "question": "Como solicitar férias?",
  "collection": "rh_docs"  // Busca só nessa coleção
}
```

### Por que Melhora
- **Isolamento**: Cada projeto/cliente tem sua própria "base de conhecimento"
- **Precisão**: Buscas não misturam contextos diferentes
- **Gerenciamento**: Fácil deletar/atualizar docs de uma coleção
- **Escalabilidade**: Preparado para múltiplos usuários/projetos

---

## 2. 🖼️ Suporte Multi-modal (Imagens + Texto)

### O Problema Atual
Seus documentos podem ter **imagens importantes**:
- Diagramas explicativos
- Gráficos com dados
- Screenshots de interfaces
- Fluxogramas

Atualmente, o sistema **ignora completamente** essas imagens. Se uma pergunta só pode ser respondida olhando um diagrama, o RAG não consegue ajudar.

### A Solução
1. **Extrair imagens** dos PDFs/DOCX durante ingestão
2. **Gerar descrições** usando modelo de visão (ex: LLaVA, GPT-4V)
3. **Indexar descrições** como chunks adicionais

```python
# Exemplo de descrição gerada
{
  "content": "Diagrama mostrando fluxo de aprovação: 
              Solicitação → Gerente → RH → Aprovado",
  "metadata": {
    "type": "image_description",
    "original_image": "page_5_fig_1.png"
  }
}
```

### Por que Melhora
- **Conhecimento completo**: Informações visuais ficam acessíveis
- **Respostas melhores**: "Veja o diagrama na página 5" com contexto real
- **Diferencial**: Poucos sistemas RAG fazem isso

---

## 3. 💾 Persistência do Cache (Redis)

### O Problema Atual
O `embedding_cache.py` atual é **in-memory** (usa `OrderedDict`). Isso significa:
- Cache é **perdido** quando a API reinicia
- Cada instância tem seu **próprio cache** (não compartilhado)
- Não há **persistência** entre deploys

### A Solução
Migrar o cache para **Redis**:
```python
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_embedding(text_hash):
    cached = cache.get(f"emb:{text_hash}")
    if cached:
        return json.loads(cached)
    return None

def set_cached_embedding(text_hash, embedding, ttl=86400):
    cache.setex(f"emb:{text_hash}", ttl, json.dumps(embedding))
```

### Por que Melhora
- **Persistência**: Cache sobrevive a reinícios
- **Compartilhado**: Múltiplas instâncias usam mesmo cache
- **TTL configurável**: Embeddings expiram automaticamente
- **Escalável**: Redis suporta milhões de entries

---

## 5. 🎯 Fine-tuning do Modelo de Embeddings

### O Problema Atual
O modelo `nomic-embed-text-v1.5` é **genérico** - treinado em textos gerais da internet. Ele pode não entender bem:
- Siglas específicas do seu domínio (ex: "GWPRP")
- Jargão técnico da sua área
- Relações semânticas específicas dos seus documentos

### A Solução
**Fine-tune** do modelo de embeddings usando seus próprios dados:

1. **Coletar pares de treinamento**:
```python
# (query, documento_relevante)
("O que é GWPRP?", "GWPRP é um protocolo de roteamento...")
("Como configurar timeout?", "Para ajustar o timeout, edite...")
```

2. **Treinar modelo** usando Sentence Transformers:
```python
from sentence_transformers import SentenceTransformer, InputExample

model = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5')
train_examples = [InputExample(texts=[query, doc]) for query, doc in pairs]
model.fit(train_examples)
```

3. **Usar modelo fine-tuned** no lugar do genérico

### Por que Melhora
- **Precisão**: +10-30% em métricas de similaridade
- **Domínio**: Modelo entende seu vocabulário específico
- **Diferencial**: Resultados muito melhores que embeddings genéricos

---

## Priorização

| # | Melhoria | Impacto | Complexidade | Dependências |
|---|----------|---------|--------------|--------------|
| 1 | Multi-tenancy | ⭐⭐⭐⭐ | Alta | Migração DB |
| 2 | Multi-modal | ⭐⭐⭐ | Alta | Modelo de visão |
| 3 | Re-ingestão | ⭐⭐⭐ | Média | Nenhuma |
| 4 | Redis Cache | ⭐⭐ | Baixa | Redis server |
| 5 | Fine-tuning | ⭐⭐⭐⭐ | Alta | Dataset de treino |

---

## Recomendação

**Ordem sugerida de implementação:**

1. **Re-ingestão Incremental** - Ganho rápido, sem dependências
2. **Redis Cache** - Simples se já usa Docker
3. **Multi-tenancy** - Se precisa isolar projetos
4. **Fine-tuning** - Se precisão é crítica
5. **Multi-modal** - Se documentos têm muitas imagens

---

*Documento gerado em: Dezembro 2025*
