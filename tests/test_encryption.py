"""
Testes para o módulo de criptografia.

Este arquivo contém testes unitários para verificar o funcionamento
correto da criptografia de dados em repouso.

Executar:
    python -m pytest tests/test_encryption.py -v
"""
import pytest
import json
from src.core.encryption import (
    EncryptionManager,
    encrypt_data,
    decrypt_data,
    encrypt_metadata,
    decrypt_metadata,
    is_encryption_enabled
)


class TestEncryptionManager:
    """Testes da classe EncryptionManager."""
    
    def setup_method(self):
        """Configuração antes de cada teste."""
        # Gerar chave de teste
        self.key = EncryptionManager.generate_key()
        self.manager = EncryptionManager(self.key.encode())
    
    def test_encrypt_decrypt_string(self):
        """Testa criptografia e descriptografia de string."""
        original = "Este é um texto sensível para teste"
        
        # Criptografar
        encrypted = self.manager.encrypt(original)
        
        # Verificar que encrypted é diferente do original
        assert encrypted != original
        assert len(encrypted) > 0
        
        # Descriptografar
        decrypted = self.manager.decrypt(encrypted)
        
        # Verificar que decrypted é igual ao original
        assert decrypted == original
    
    def test_encrypt_dict(self):
        """Testa criptografia de dicionário."""
        original = {
            "source": "documento.pdf",
            "page": 10,
            "author": "John Doe"
        }
        
        # Criptografar
        encrypted = self.manager.encrypt_dict(original)
        
        # Verificar que encrypted é uma string
        assert isinstance(encrypted, str)
        
        # Descriptografar
        decrypted = self.manager.decrypt_dict(encrypted)
        
        # Verificar que decrypted é igual ao original
        assert decrypted == original
    
    def test_encrypt_empty_string_raises_error(self):
        """Testa que string vazia levanta ValueError."""
        with pytest.raises(ValueError, match="Cannot encrypt empty data"):
            self.manager.encrypt("")
    
    def test_decrypt_invalid_token_raises_error(self):
        """Testa que token inválido levanta InvalidToken."""
        from cryptography.fernet import InvalidToken
        
        invalid_token = "gAAAAABinvalid_token_data"
        
        with pytest.raises(InvalidToken):
            self.manager.decrypt(invalid_token)
    
    def test_encrypt_if_sensitive_true(self):
        """Testa criptografia condicional (sensível=True)."""
        original = "dados sensíveis"
        
        encrypted = self.manager.encrypt_if_sensitive(original, is_sensitive=True)
        
        # Deve estar criptografado
        assert encrypted != original
    
    def test_encrypt_if_sensitive_false(self):
        """Testa criptografia condicional (sensível=False)."""
        original = "dados públicos"
        
        encrypted = self.manager.encrypt_if_sensitive(original, is_sensitive=False)
        
        # NÃO deve estar criptografado
        assert encrypted == original
    
    def test_decrypt_if_encrypted_true(self):
        """Testa descriptografia condicional (criptografado=True)."""
        original = "teste"
        encrypted = self.manager.encrypt(original)
        
        decrypted = self.manager.decrypt_if_encrypted(encrypted, is_encrypted=True)
        
        # Deve estar descriptografado
        assert decrypted == original
    
    def test_decrypt_if_encrypted_false(self):
        """Testa descriptografia condicional (criptografado=False)."""
        original = "não criptografado"
        
        decrypted = self.manager.decrypt_if_encrypted(original, is_encrypted=False)
        
        # Deve retornar como está
        assert decrypted == original


class TestEncryptionFunctions:
    """Testes das funções globais de criptografia."""
    
    def test_generate_key(self):
        """Testa geração de chave."""
        key = EncryptionManager.generate_key()
        
        # Verificar formato base64
        assert len(key) > 0
        # Chave Fernet tem 44 caracteres base64
        assert len(key) == 44
    
    def test_encrypt_data_without_key(self):
        """Testa criptografia sem chave configurada."""
        # Se criptografia não estiver habilitada, retorna como está
        result = encrypt_data("teste")
        
        # Quando sem chave, retorna o original
        assert result == "teste"
    
    def test_decrypt_data_without_key(self):
        """Testa descriptografia sem chave configurada."""
        data = "dados não criptografados"
        
        result = decrypt_data(data)
        
        # Quando sem chave, retorna como está
        assert result == data
    
    def test_encrypt_metadata(self):
        """Testa criptografia de metadados."""
        metadata = {
            "source": "documento.pdf",
            "page": 5,
            "chunk_index": 10
        }
        
        encrypted = encrypt_metadata(metadata)
        
        # Verificar que é uma string
        assert isinstance(encrypted, str)
    
    def test_decrypt_metadata(self):
        """Testa descriptografia de metadados."""
        metadata = {"key": "value", "number": 123}
        
        # Criptografar e depois descriptografar
        encrypted = encrypt_metadata(metadata)
        decrypted = decrypt_metadata(encrypted)
        
        assert decrypted == metadata


class TestEncryptionIntegration:
    """Testes de integração simulando uso real."""
    
    def setup_method(self):
        """Configuração antes de cada teste."""
        self.key = EncryptionManager.generate_key()
        self.manager = EncryptionManager(self.key.encode())
    
    def test_full_document_workflow(self):
        """Testa fluxo completo de documento."""
        document = {
            "content": "Este é o conteúdo do documento",
            "metadata": {
                "source": "manual.pdf",
                "page": 15,
                "section": "Introdução"
            }
        }
        
        # Criptografar conteúdo
        encrypted_content = self.manager.encrypt(document["content"])
        
        # Criptografar metadados
        encrypted_metadata = self.manager.encrypt_dict(document["metadata"])
        
        # Verificar que ambos estão criptografados
        assert encrypted_content != document["content"]
        assert encrypted_metadata != json.dumps(document["metadata"])
        
        # Descriptografar conteúdo
        decrypted_content = self.manager.decrypt(encrypted_content)
        
        # Descriptografar metadados
        decrypted_metadata = self.manager.decrypt_dict(encrypted_metadata)
        
        # Verificar integridade
        assert decrypted_content == document["content"]
        assert decrypted_metadata == document["metadata"]
    
    def test_multiple_encryptions(self):
        """Testa múltiplas criptografagens do mesmo dado."""
        original = "dado para testar"
        
        # Criptografar múltiplas vezes
        encrypted1 = self.manager.encrypt(original)
        encrypted2 = self.manager.encrypt(original)
        encrypted3 = self.manager.encrypt(original)
        
        # Todas devem ser diferentes (por causa do IV/salt)
        assert encrypted1 != encrypted2
        assert encrypted2 != encrypted3
        
        # Mas todas devem descriptografar para o mesmo valor
        assert self.manager.decrypt(encrypted1) == original
        assert self.manager.decrypt(encrypted2) == original
        assert self.manager.decrypt(encrypted3) == original
    
    def test_large_text(self):
        """Testa criptografia de texto grande."""
        # Texto grande (10KB)
        large_text = "x" * 10240
        
        encrypted = self.manager.encrypt(large_text)
        decrypted = self.manager.decrypt(encrypted)
        
        assert decrypted == large_text
    
    def test_unicode_and_special_chars(self):
        """Testa criptografia de caracteres unicode e especiais."""
        texts = [
            "Texto com acentuação: áéíóú",
            "Emojis: 😀🎉🚀",
            "Caracteres especiais: @#$%^&*()",
            "Multilíngue: English, Español, Français, 中文, 日本語",
            "RTL: مرحبا بالعالم"
        ]
        
        for text in texts:
            encrypted = self.manager.encrypt(text)
            decrypted = self.manager.decrypt(encrypted)
            assert decrypted == text, f"Falha para texto: {text}"


class TestEncryptionPerformance:
    """Testes básicos de performance."""
    
    def setup_method(self):
        """Configuração antes de cada teste."""
        self.key = EncryptionManager.generate_key()
        self.manager = EncryptionManager(self.key.encode())
    
    def test_encrypt_performance(self, benchmark):
        """Testa performance de criptografia."""
        data = "Texto de teste para performance " * 100  # ~2KB
        
        # Benchmark
        result = self.manager.encrypt(data)
        
        # Verificar resultado
        assert result != data
    
    def test_decrypt_performance(self, benchmark):
        """Testa performance de descriptografia."""
        data = "Texto de teste para performance " * 100
        encrypted = self.manager.encrypt(data)
        
        # Benchmark
        result = self.manager.decrypt(encrypted)
        
        # Verificar resultado
        assert result == data


if __name__ == "__main__":
    # Executar testes
    pytest.main([__file__, "-v", "--tb=short"])
