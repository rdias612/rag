# Especificação de UX: Botões de Sugestão (Quick Actions)

## 1. Visão Geral
Os Botões de Sugestão, implementados na tela inicial ("Empty State") da interface de chat, representam **pontos de entrada rápida** para as funcionalidades principais do assistente RAG. Visualmente, apresentam-se como "cards" interativos situados centralmente abaixo da mensagem de boas-vindas.

## 2. Objetivos
*   **Eliminar a "Tela em Branco":** Usuários frequentemente sentem paralisia de análise ao se deparar com um chat vazio. Os botões oferecem um "caminho feliz" imediato.
*   **Descoberta de Funcionalidades (Feature Discovery):** Educar o usuário sobre as capacidades do sistema (Análise vs. Síntese) sem a necessidade de tutoriais ou manuais.
*   **Eficiência:** Reduzir o tempo entre a abertura da ferramenta e o primeiro valor entregue (Time-to-Value).

## 3. Motivação e Design
A inclusão destes elementos responde a uma necessidade crítica de UX identificada na versão anterior da interface (que era vazia e escura).

*   **Affordance:** Os botões sinalizam que a interface é interativa e está pronta para processar comandos complexos, não apenas "conversar".
*   **Estética Profissional:** O design utiliza *glassmorphism* (bordas translúcidas, fundos escuros com blur) e ícones semânticos (`Zap` para energia/rapidez/profundidade, `BookOpen` para leitura/resumo) para transmitir modernidade e robustez.

## 4. Análise Funcional dos Elementos

### ⚡ Deep Dive (Análise Profunda)
*   **Descrição:** Focado em exploração e complexidade.
*   **Ganho Funcional Previsto:**
    *   Serve como gatilho para prompts de **Chain-of-Thought** (Cadeia de Pensamento).
    *   Ao ser ativado, instrui o RAG a varrer todos os documentos em busca de conexões não óbvias, contradições ou detalhes técnicos.
    *   Pupa o usuário de digitar prompts complexos como: *"Analise todos os documentos e encontre correlações estruturais..."*

### 📖 Summarize (Resumir)
*   **Descrição:** Focado em síntese e rapidez.
*   **Ganho Funcional Previsto:**
    *   Serve como gatilho para algoritmos de **Summarization** (Map-Reduce ou Refine).
    *   Permite que um usuário entenda o conteúdo de uma "coleção" inteira em segundos.
    *   Ideal para triagem rápida de documentos: "Vale a pena ler isso?"

## 5. Implementação Técnica (Front-end)
Atualmente localizados em `src/components/MessageList.tsx`, estes componentes são renderizados condicionalmente apenas quando `messages.length === 0`. Isso garante que eles não poluam a interface após o início da conversa, mantendo o foco no conteúdo gerado.
