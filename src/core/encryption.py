"""
Módulo de criptografia para proteção de dados sensíveis em repouso.

Implementa criptografia simétrica usando Fernet (AES-128 com HMAC)
do pacote cryptography.
"""
import os
import base64
import json
import logging
from typing import Any, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from src.config import get_env


security_logger = logging.getLogger("rag.security")


class EncryptionManager:
    """
    Gerenciador de criptografia usando Fernet (AES-128).
    
    Fernet fornece:
    - Criptografia simétrica (mesma chave para encriptar e decriptar)
    - Autenticação via HMAC
    - Garantia de integridade
    - Prevenção de ataques de replay
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Inicializa o gerenciador de criptografia.
        
        Args:
            encryption_key: Chave de criptografia (32 bytes base64-encoded).
                          Se None, tenta carregar da variável de ambiente.
        """
        if encryption_key is None:
            encryption_key = self._load_key_from_env()
        
        if not encryption_key:
            raise ValueError(
                "Encryption key not provided. Set ENCRYPTION_KEY environment variable "
                "or pass it explicitly. Generate a key with: "
                "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        self.cipher = Fernet(encryption_key)
        self._key = encryption_key
        security_logger.info("EncryptionManager initialized successfully")
    
    @staticmethod
    def _load_key_from_env() -> Optional[bytes]:
        """
        Carrega chave de criptografia da variável de ambiente.
        
        Returns:
            Chave de criptografia ou None se não encontrada
        """
        key_str = get_env("ENCRYPTION_KEY")
        if not key_str:
            return None
        
        # Decodificar de base64 se necessário
        try:
            return base64.urlsafe_b64decode(key_str.encode())
        except Exception as e:
            security_logger.warning("Failed to decode encryption key from env: %s", str(e))
            # Tentar usar como string direta
            try:
                return key_str.encode()
            except:
                return None
    
    @staticmethod
    def generate_key() -> str:
        """
        Gera uma nova chave de criptografia.
        
        Returns:
            Chave codificada em base64 para uso em variáveis de ambiente
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()
    
    @staticmethod
    def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> str:
        """
        Gera chave de criptografia a partir de uma senha usando PBKDF2.
        
        Args:
            password: Senha para gerar a chave
            salt: Salt para PBKDF2. Se None, gera novo salt.
            
        Returns:
            Chave codificada em base64
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode()
    
    def encrypt(self, data: str) -> str:
        """
        Criptografa uma string.
        
        Args:
            data: Dados em texto plano
            
        Returns:
            Dados criptografados (base64-encoded)
            
        Raises:
            ValueError: Se data estiver vazio
        """
        if not data:
            raise ValueError("Cannot encrypt empty data")
        
        try:
            encrypted = self.cipher.encrypt(data.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            security_logger.error("Encryption failed: %s", str(e))
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Descriptografa uma string criptografada.
        
        Args:
            encrypted_data: Dados criptografados
            
        Returns:
            Dados em texto plano
            
        Raises:
            InvalidToken: Se a chave estiver incorreta ou dados corrompidos
        """
        if not encrypted_data:
            raise ValueError("Cannot decrypt empty data")
        
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken as e:
            security_logger.error("Decryption failed: Invalid token (wrong key or corrupted data)")
            raise
        except Exception as e:
            security_logger.error("Decryption failed: %s", str(e))
            raise
    
    def encrypt_dict(self, data: dict) -> str:
        """
        Criptografa um dicionário serializando-o como JSON.
        
        Args:
            data: Dicionário a ser criptografado
            
        Returns:
            JSON criptografado (base64-encoded)
        """
        json_data = json.dumps(data, ensure_ascii=False)
        return self.encrypt(json_data)
    
    def decrypt_dict(self, encrypted_data: str) -> dict:
        """
        Descriptografa dados de um dicionário criptografado.
        
        Args:
            encrypted_data: JSON criptografado
            
        Returns:
            Dicionário descriptografado
        """
        json_data = self.decrypt(encrypted_data)
        return json.loads(json_data)
    
    def encrypt_if_sensitive(self, data: Any, is_sensitive: bool = True) -> Any:
        """
        Criptografa dados se marcados como sensíveis.
        
        Args:
            data: Dados a serem processados
            is_sensitive: Se True, criptografa; se False, retorna como está
            
        Returns:
            Dados criptografados ou dados originais
        """
        if not is_sensitive:
            return data
        
        if isinstance(data, str):
            return self.encrypt(data)
        elif isinstance(data, dict):
            return self.encrypt_dict(data)
        elif data is None:
            return None
        else:
            # Tentar converter para string
            return self.encrypt(str(data))
    
    def decrypt_if_encrypted(self, data: Any, is_encrypted: bool = True) -> Any:
        """
        Descriptografa dados se marcados como criptografados.
        
        Args:
            data: Dados a serem processados
            is_encrypted: Se True, descriptografa; se False, retorna como está
            
        Returns:
            Dados descriptografados ou dados originais
        """
        if not is_encrypted:
            return data
        
        if data is None:
            return None
        
        try:
            return self.decrypt(data)
        except (InvalidToken, ValueError):
            # Se não for criptografado, retorna como está
            return data

# Instância global do gerenciador de criptografia
_encryption_manager = None


def get_encryption_manager() -> EncryptionManager:
    """
    Retorna a instância global do gerenciador de criptografia.
    
    Returns:
        Instância de EncryptionManager
    """
    global _encryption_manager
    
    if _encryption_manager is None:
        # Verificar se criptografia está habilitada
        enable_encryption = get_env("ENABLE_ENCRYPTION", "false").lower() == "true"
        
        if enable_encryption:
            encryption_key = get_env("ENCRYPTION_KEY")
            if encryption_key:
                _encryption_manager = EncryptionManager(encryption_key.encode())
            else:
                security_logger.warning(
                    "ENCRYPTION_KEY not set, encryption will be disabled. "
                    "To enable encryption, set ENCRYPTION_KEY environment variable."
                )
                _encryption_manager = None
        else:
            security_logger.info("Encryption is disabled (ENABLE_ENCRYPTION=false)")
            _encryption_manager = None
    
    return _encryption_manager


def encrypt_data(data: str) -> Optional[str]:
    """
    Criptografa dados usando o gerenciador global.
    
    Args:
        data: Dados a serem criptografados
        
    Returns:
        Dados criptografados ou None se criptografia estiver desabilitada
    """
    manager = get_encryption_manager()
    if manager is None:
        return data
    
    try:
        return manager.encrypt(data)
    except Exception as e:
        security_logger.error("Failed to encrypt data: %s", str(e))
        return data


def decrypt_data(encrypted_data: str) -> Optional[str]:
    """
    Descriptografa dados usando o gerenciador global.
    
    Args:
        encrypted_data: Dados criptografados
        
    Returns:
        Dados descriptografados ou None se criptografia estiver desabilitada
    """
    manager = get_encryption_manager()
    if manager is None:
        return encrypted_data
    
    try:
        return manager.decrypt(encrypted_data)
    except InvalidToken:
        # Dados não criptografados, retornar como está
        return encrypted_data
    except Exception as e:
        security_logger.error("Failed to decrypt data: %s", str(e))
        return encrypted_data


def encrypt_metadata(metadata: dict) -> str:
    """
    Criptografa metadados (JSON) usando o gerenciador global.
    
    Args:
        metadata: Dicionário de metadados
        
    Returns:
        JSON criptografado ou string JSON normal se criptografia desabilitada
    """
    manager = get_encryption_manager()
    if manager is None:
        return json.dumps(metadata)
    
    try:
        return manager.encrypt_dict(metadata)
    except Exception as e:
        security_logger.error("Failed to encrypt metadata: %s", str(e))
        return json.dumps(metadata)


def decrypt_metadata(encrypted_metadata: str) -> dict:
    """
    Descriptografa metadados usando o gerenciador global.
    
    Args:
        encrypted_metadata: JSON criptografado
        
    Returns:
        Dicionário de metadados
    """
    manager = get_encryption_manager()
    if manager is None:
        return json.loads(encrypted_metadata)
    
    try:
        return manager.decrypt_dict(encrypted_metadata)
    except (InvalidToken, json.JSONDecodeError):
        # Dados não criptografados ou corrompidos, tentar parse direto
        try:
            return json.loads(encrypted_metadata)
        except:
            return {}
    except Exception as e:
        security_logger.error("Failed to decrypt metadata: %s", str(e))
        return {}


def is_encryption_enabled() -> bool:
    """
    Verifica se a criptografia está habilitada.
    
    Returns:
        True se criptografia estiver habilitada
    """
    return get_encryption_manager() is not None
