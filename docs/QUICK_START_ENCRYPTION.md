# ⚡ Quick Start: Criptografia (Melhoria 5.4)

**Tempo estimado de configuração:** 10 minutos

---

## 🚀 Setup Rápido

### 1. Instalar Dependência
```bash
pip install -r requirements.txt
```

### 2. Gerar Chave de Criptografia
```bash
python scripts/generate_encryption_key.py
```

### 3. Adicionar ao `.env`
```bash
# Criptografia em Repouso
ENABLE_ENCRYPTION=true
ENCRYPTION_KEY=your-generated-key-here

# Criptografia em Trânsito (HTTPS) - Opcional
ENABLE_HTTPS=true
SSL_CERT_PATH=./certs/cert.pem
SSL_KEY_PATH=./certs/key.pem
```

### 4. Gerar Certificado SSL (Se HTTPS)
```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -days 365 \
  -nodes
```

### 5. Reiniciar Aplicação
```bash
python run_app.py
```

---

## ✅ Verificação

### Verificar Criptografia
```python
from src.core.encryption import is_encryption_enabled, encrypt_data, decrypt_data

print(f"Criptografia habilitada: {is_encryption_enabled()}")

# Testar criptografia
test_data = "dados sensíveis"
encrypted = encrypt_data(test_data)
decrypted = decrypt_data(encrypted)

print(f"Original: {test_data}")
print(f"Criptografado: {encrypted[:50]}...")
print(f"Descriptografado: {decrypted}")
```

### Verificar HTTPS
```bash
curl -v https://localhost:5000/api/health
# Deve mostrar "SSL certificate verify ok"
```

---

## ⚠️ Importante

- Habilitar criptografia **NÃO** criptografa dados existentes automaticamente
- Para criptografar dados existentes, faça backup e re-ingera documentos
- **NUNCA** commit a chave de criptografia no Git
- Mantenha backup da chave em local seguro

---

## 📚 Documentação Completa

- `docs/IMPLEMENTACAO_5.4_CRIPTOGRAFIA.md` - Documentação técnica completa
- `docs/RESUMO_IMPLEMENTACAO_5.4.md` - Resumo da implementação

---

**Status:** ✅ Implementado e pronto para uso
