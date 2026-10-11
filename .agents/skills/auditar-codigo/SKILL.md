---
name: auditar-codigo
description: Investiga e analisa código do repo racha em busca de bugs latentes, código duplicado/slop e divergências do padrão do projeto, entregando um relatório de achados com evidências arquivo:linha — sem alterar código. Use sempre que o usuário pedir para investigar, analisar ou auditar código, procurar bugs, encontrar duplicação/slop/código morto, verificar se algo segue o padrão do projeto ou revisar qualidade de um módulo/arquivo/diff com olhar crítico (ex. "investigue o módulo X", "procure bugs em Y", "tem código duplicado aí?", "isso segue o padrão?"). NÃO use para implementar ou corrigir (→ implementar-requisito ou correção direta) nem para depurar um defeito específico já observado em uso.
---

# Auditar Código — Investigação Read-Only

Você é o investigador. O entregável é um **relatório de achados**, não código: nada de editar, criar arquivo ou commitar — correção só acontece depois, se o dono pedir. A auditoria olha por três lentes, e o escopo do pedido define quais aplicam:

- **Bugs**: lógica incorreta ou casos de borda mal tratados — null/undefined, lista vazia, corrida/estado obsoleto, erro engolido silenciosamente, dependência errada em `useEffect`, chave de cache desatualizada, SQL/RLS que vaza ou bloqueia além do previsto.
- **Duplicação/slop**: repetição verificável por grep, código morto, dependência não usada, abstração de uso único, comentário narrando o óbvio, cópia que derivou de um componente/helper compartilhado que já existe.
- **Divergência de padrão**: o que foge do padrão dominante do módulo e das diretrizes do `AGENTS.md` — ex. fetch manual onde `useCache` é o padrão, `<button>` cru onde existe `Botao`, camada errada (DTO com regra de negócio, service acumulando responsabilidades).

## 1. Delimitar o escopo

- Identifique o alvo: arquivo, módulo, área (`src/`, `supabase/`, `scripts/`) ou diff. Se o pedido ficou ambíguo, escolha a menor área que o contém e diga qual foi.
- Auditoria de diff (ex. "revise o que mudou"): anote o BASE `git rev-parse --short HEAD` e o range a auditar. Auditoria de árvore: liste os arquivos alvo antes de investigar.
- Lentes: aplique as três, salvo se o dono restringiu (ex. "só bugs").

## 2. Estabelecer o padrão (baseline)

Divergência precisa de referência. Leia o `AGENTS.md` da raiz (obrigatório) e o `DESIGN.md` quando o alvo for UI. Depois identifique o padrão dominante do módulo com contagens concretas (grep), no estilo de `docs/rank-melhorias-reuso-codigo.md`: "`Botao` usado em 37 arquivos, 90 `<button>` crus em 44". Divergência é a cópia minoritária que deveria usar o dominante — não é "eu faria diferente". Em escopo grande, esta etapa é delegada ao Mapeador (3.1).

## 3. Investigar

- Escopo pequeno (1-2 arquivos, uma lente): investigue direto, sem subagente — a orquestração existe para breadth, não para cerimônia.
- Escopo maior: orquestre subagentes **read-only** (ferramenta Agent) nos papéis abaixo, na ordem Mapeador → Investigador → Caçador de slop. Nunca despache agente de implementação para investigar.
- Escopo multiárea (ex. `src/` + `supabase/`): um Investigador e um Caçador por área, em paralelo, com o mesmo baseline do Mapeador; consolide depois.

Todo prompt de subagente contém, além do papel: arquivos do escopo, aviso de que o `AGENTS.md` da raiz é obrigatório, exigência de evidência (`arquivo:linha` + trecho; alegação precisa ser verificável por grep/leitura) e "relatar, não editar". Use os tipos de agente abaixo ou o equivalente read-only disponível no momento.

### 3.1 Mapeador — `Explore`

- **Função**: delimitar a superfície do escopo e estabelecer o padrão dominante do módulo — a base da lente de divergência.
- **Prompt**: escopo + lentes aplicáveis + pedido de contagens grep (componentes/helpers compartilhados vs. uso cru, no estilo do rank de reuso).
- **Saída esperada**: mapa dos arquivos do escopo + baseline (padrão dominante com contagem e 2-3 exemplos `arquivo:linha`) + pontos quentes suspeitos para os próximos agentes priorizarem.

### 3.2 Investigador — `code-reviewer`

- **Função**: lentes de bugs e divergência de padrão, com rubrica de severidade.
- **Prompt**: escopo + baseline do Mapeador + definição das duas lentes + severidade obrigatória.
- **Saída esperada**: lista de achados, cada um com título, evidência `arquivo:linha` + trecho, risco concreto e severidade **Critical / Important / Minor**. Sem achados numa região, declara isso — não inventa.

### 3.3 Caçador de slop — `anti-slop`

- **Função**: lente de duplicação/slop — código morto, dependência não usada, abstração de uso único, duplicação verificável por grep.
- **Cuidado**: este agente carrega ferramentas de edição; o prompt deve travá-lo em somente leitura ("apenas relatar, não alterar nada").
- **Saída esperada**: lista de achados com evidência e, para duplicação, contagem de cópias (`arquivo:linha` de cada ocorrência).

## 4. Verificar e consolidar

- Confira pessoalmente cada achado Critical/Important lendo as linhas citadas antes de aceitá-lo. Achado sem evidência verificável é descartado — relatório sem fundamento pior que nenhum relatório.
- Dedupe: mesma causa raiz = um achado só. Ordene por severidade: bug ativo > divergência de risco > minor.

## 5. Relatório

- **No chat por padrão.** Abra com uma linha de resumo (achados por lente/severidade); depois cada achado com: título, evidência `arquivo:linha`, por que importa (o risco concreto) e direção proposta em 1-2 linhas — sem implementar.
- Feche deixando claro: corrigir é fora de escopo; se o dono quiser, requisito simples corrige direto, requisito complexo vai para `implementar-requisito`.
- **Não crie doc de auditoria por conta própria** — o repositório tem histórico de limpeza de docs lixo. Persista em `docs/` só sob pedido do dono, seguindo o estilo de `docs/rank-melhorias-reuso-codigo.md` (critério + tabela + itens com evidência grep-verificável).

## Regras invariantes

- Read-only: nenhum agente edita, cria arquivo ou commita durante a auditoria.
- Toda evidência é `arquivo:linha` e verificada pelo orquestrador antes de virar achado.
- Divergência de padrão exige padrão dominante demonstrado com contagem/exemplo — nunca gosto pessoal.
- Sem push, sem testes novos, sem misturar auditoria com correção na mesma passada.
- Siga as diretrizes de qualidade do `AGENTS.md` como régua, mas não proponha refatoração ampla fora do escopo auditado.
