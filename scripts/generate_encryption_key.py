#!/usr/bin/env python3
"""
Script para gerar chave de criptografia para o sistema RAG.

Este script gera uma nova chave de criptografia usando Fernet (AES-128)
e exibe instruções para configurá-la no ambiente.

Uso:
    python scripts/generate_encryption_key.py

A chave gerada deve ser armazenada com segurança e NUNCA deve ser
compartilhada ou versionada no Git.
"""
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.core.encryption import EncryptionManager


def main():
    """Função principal."""
    print("=" * 80)
    print("🔐 Gerador de Chave de Criptografia - Sistema RAG")
    print("=" * 80)
    print()
    
    # Gerar nova chave
    print("📝 Gerando nova chave de criptografia...")
    encryption_key = EncryptionManager.generate_key()
    
    print(f"✅ Chave gerada com sucesso!")
    print()
    print("⚠️  IMPORTANTE: Salve esta chave em um local seguro!")
    print("   - NÃO compartilhe esta chave")
    print("   - NÃO faça commit no Git")
    print("   - NÃO a inclua em arquivos de configuração públicos")
    print()
    
    # Exibir chave
    print("=" * 80)
    print("CHAVE DE CRIPTOGRAFIA:")
    print("=" * 80)
    print(encryption_key)
    print("=" * 80)
    print()
    
    # Instruções de configuração
    print("📋 INSTRUÇÕES DE CONFIGURAÇÃO:")
    print("-" * 80)
    print()
    print("1. Adicione a chave ao seu arquivo .env:")
    print(f"   ENCRYPTION_KEY={encryption_key}")
    print()
    print("2. Habilite a criptografia:")
    print("   ENABLE_ENCRYPTION=true")
    print()
    print("3. Especifique quais campos criptografar (opcional, defaults: true):")
    print("   ENCRYPT_DOCUMENT_CONTENT=true")
    print("   ENCRYPT_METADATA=true")
    print("   ENCRYPT_FEEDBACK_COMMENTS=true")
    print()
    print("4. Reinicie a aplicação:")
    print("   python run_app.py")
    print()
    
    # Informações sobre segurança
    print("=" * 80)
    print("🔒 INFORMAÇÕES DE SEGURANÇA")
    print("=" * 80)
    print()
    print("✓ Chave gerada usando Fernet (AES-128 com HMAC)")
    print("✓ Criptografia simétrica (mesma chave para criptografar/descriptografar)")
    print("✓ Autenticação via HMAC garante integridade dos dados")
    print("✓ Prevenção de ataques de replay")
    print()
    
    # Aviso sobre perda de chave
    print("⚠️  AVISO CRÍTICO:")
    print("-" * 80)
    print("Se você PERDER esta chave, NÃO será possível recuperar os dados")
    print("criptografados. Faça backup em um local seguro!")
    print()
    
    # Opção de salvar em arquivo
    save_to_file = input("Deseja salvar a chave em um arquivo seguro? (s/n): ").lower()
    if save_to_file == 's':
        filename = input("Nome do arquivo (default: encryption_key.txt): ") or "encryption_key.txt"
        filepath = root_dir / filename
        
        # Verificar se arquivo já existe
        if filepath.exists():
            overwrite = input(f"Arquivo {filename} já existe. Sobrescrever? (s/n): ").lower()
            if overwrite != 's':
                print("❌ Operação cancelada.")
                return
        
        # Salvar chave
        with open(filepath, 'w') as f:
            f.write(f"# Chave de Criptografia - Sistema RAG\n")
            f.write(f"# GERADA EM: {os.popen('date').read().strip()}\n")
            f.write(f"# NÃO COMPARTILHE ESTA CHAVE!\n")
            f.write(f"# NÃO FAZER COMMIT NO GIT!\n")
            f.write(f"\nENCRYPTION_KEY={encryption_key}\n")
        
        print(f"✅ Chave salva em: {filepath}")
        print(f"⚠️  Lembre-se de adicionar {filename} ao .gitignore!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        sys.exit(1)
