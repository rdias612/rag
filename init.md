# Projeto: Sudoku Mobile Game 📱
**Objetivo:** Criar um jogo de Sudoku para Android (Play Store) com 5 níveis de dificuldade e monetização via anúncios recompensados.

---

## 1. Stack Tecnológica Recomendada
Considerando que Sudoku é um jogo baseado em UI (Interface) e Lógica, e não em física complexa, o uso de uma Game Engine pesada é desnecessário.

* **Framework:** **Flutter** (Google).
    * *Motivo:* Leve, gera código nativo rápido, excelente para lidar com grids e interfaces responsivas em várias telas, fácil integração com AdMob.
* **Linguagem:** **Dart**.
* **IDE:** Visual Studio Code ou Android Studio.
* **Gerenciamento de Estado:** `Provider` ou `Riverpod` (para atualizar a tela quando um número muda).
* **Persistência de Dados:** `Hive` (Banco NoSQL super rápido) ou `SharedPreferences`.

---

## 2. Arquitetura do Projeto (MVVM)
O padrão **Model-View-ViewModel** separa a lógica matemática da interface visual.

1.  **MODEL (Dados):**
    * Matriz 9x9 de Inteiros (o tabuleiro lógico).
    * Classe `Cell` (contém: valor, bool isEditable, bool isError).
2.  **VIEW (Tela):**
    * Widgets do Flutter desenhando o Grid.
    * Inputs do usuário (Teclado numérico na tela).
3.  **VIEWMODEL (Lógica):**
    * Contém o algoritmo de validação.
    * Gerencia o Timer.
    * Gerencia o estado dos Anúncios (Créditos de Dica).

---

## 3. O Algoritmo Core: Backtracking
O coração do Sudoku é o algoritmo de **Backtracking**. Ele funciona por "tentativa e erro" recursiva. Ele é usado tanto para **criar** um tabuleiro válido quanto para **resolver** (dar a dica).

### Lógica Explicada:
1.  Encontre uma célula vazia (valor 0).
2.  Tente colocar um número de 1 a 9.
3.  Verifique se é válido (não repete na linha, coluna ou quadrado 3x3).
4.  Se válido, passe para a próxima célula (recursão).
5.  Se chegar num beco sem saída, volte para a célula anterior, apague o número e tente o próximo (Backtrack).

### Exemplo de Implementação (Dart):

```dart
class SudokuSolver {
  
  // Função principal para resolver o grid
  bool solveSudoku(List<List<int>> board) {
    for (int row = 0; row < 9; row++) {
      for (int col = 0; col < 9; col++) {
        // Se a célula está vazia (0)
        if (board[row][col] == 0) {
          // Tenta números de 1 a 9
          for (int num = 1; num <= 9; num++) {
            if (isValid(board, row, col, num)) {
              // Se for válido, atribui o número
              board[row][col] = num;

              // RECURSÃO: Tenta resolver o restante do tabuleiro
              if (solveSudoku(board)) {
                return true;
              }

              // BACKTRACK: Se a recursão falhou, zera a célula e tenta o próximo número
              board[row][col] = 0;
            }
          }
          // Se nenhum número de 1-9 serviu, este caminho não tem solução
          return false;
        }
      }
    }
    // Se não há mais zeros, o tabuleiro está resolvido
    return true;
  }

  // Função auxiliar para validar as regras do Sudoku
  bool isValid(List<List<int>> board, int row, int col, int num) {
    // 1. Verifica a Linha
    for (int i = 0; i < 9; i++) {
      if (board[row][i] == num) return false;
    }

    // 2. Verifica a Coluna
    for (int i = 0; i < 9; i++) {
      if (board[i][col] == num) return false;
    }

    // 3. Verifica o Sub-quadrado 3x3
    int startRow = row - row % 3;
    int startCol = col - col % 3;
    for (int i = 0; i < 3; i++) {
      for (int j = 0; j < 3; j++) {
        if (board[i + startRow][j + startCol] == num) return false;
      }
    }

    return true;
  }
}

---

## 4. Implementação dos Níveis de Dificuldade
Para criar os níveis, gere um tabuleiro completo e depois remova números ("fure" o tabuleiro).

* **Nível 1 (Iniciante):** Remover ~30 números.
* **Nível 2 (Fácil):** Remover ~40 números.
* **Nível 3 (Médio):** Remover ~48 números.
* **Nível 4 (Difícil):** Remover ~52 números.
* **Nível 5 (Expert):** Remover ~56+ números.

> **Importante:** Sempre que remover um número, garanta que o tabuleiro ainda tenha solução única.

---

## 5. Monetização (Google AdMob)
**Estratégia:** Rewarded Video Ads (Anúncio de Vídeo Recompensado).

### Fluxo da Feature "Dica":
1. Usuário clica no ícone 💡 (Dica).
2. **Verificação:** `if (dicasDisponiveis > 0)`
    * **SIM:** Revela número. `dicasDisponiveis--`.
    * **NÃO:** Popup "Assista vídeo para ganhar +3 dicas".
3. **Ação:** Usuário aceita.
4. **AdMob SDK:** Exibe vídeo.
5. **Callback:** `onUserEarnedReward` -> `dicasDisponiveis += 3` -> Salva no disco.

---

## 6. Checklist de Publicação (Play Store)
* **Ícone do App:** 512x512px (Design limpo).
* **Screenshots:** Prints dos 5 níveis.
* **Google Play Console:**
    * Criar conta ($25 USD).
    * Classificação indicativa (Livre).
    * Política de privacidade (obrigatório por usar Ads).
* **Build:** Gerar arquivo `.aab`.

---

## 7. Próximos Passos
- [ ] Instalar Flutter SDK.
- [ ] Criar projeto `flutter create sudoku_game`.
- [ ] Implementar UI básica (Grid 9x9).
- [ ] Integrar classe `SudokuSolver`.
- [ ] Adicionar pacote `google_mobile_ads`.