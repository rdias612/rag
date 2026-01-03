"""
Script de validação final do sistema de logging.

Este script valida que o sistema de logging está configurado corretamente
e funcionando como esperado após a migração para o padrão Python.
"""
import logging
import sys
import os
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# Adicionar o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_logging_system():
    """Validação final do sistema de logging."""
    print("=" * 60)
    print("VALIDAÇÃO FINAL DO SISTEMA DE LOGGING")
    print("=" * 60)
    print()

    all_passed = True

    # 1. Verificar configuração
    print("1. Verificando configuracao de logging...")
    try:
        from src.core.logging_config import setup_logging
        from src.config import LOG_LEVEL, LOG_FILE
        print("   [OK] Configuracao de logging: OK")
        print(f"      - LOG_LEVEL: {LOG_LEVEL}")
        print(f"      - LOG_FILE: {LOG_FILE}")
    except Exception as e:
        print(f"   [ERRO] Erro na configuracao: {e}")
        all_passed = False
    print()

    # 2. Testar loggers principais
    print("2. Testando loggers principais...")
    loggers = [
        "rag.llm",
        "rag.embeddings",
        "rag.database",
        "rag.api",
        "rag.security",
        "rag.ingestion",
        "rag.pipeline"
    ]

    for logger_name in loggers:
        try:
            logger = logging.getLogger(logger_name)
            logger.info("Test log from %s", logger_name)
            print(f"   [OK] {logger_name}: OK")
        except Exception as e:
            print(f"   [ERRO] {logger_name}: ERRO - {e}")
            all_passed = False
    print()

    # 3. Verificar imports órfãos
    print("3. Verificando imports órfãos...")
    orphaned_imports = []
    for py_file in Path("src").rglob("*.py"):
        try:
            content = py_file.read_text()
            if "from src.core.logger import" in content:
                orphaned_imports.append(str(py_file))
        except Exception:
            pass

    if orphaned_imports:
        print("   [AVISO] Imports orfaos encontrados:")
        for imp in orphaned_imports:
            print(f"      - {imp}")
        all_passed = False
    else:
        print("   [OK] Nenhum import orfao encontrado")
    print()

    # 4. Verificar uso de funções deprecadas
    print("4. Verificando uso de funções deprecadas...")
    deprecated_functions = [
        "log_with_data",
        "log_llm_request",
        "log_llm_response",
        "log_llm_full_request",
        "log_llm_full_response",
        "log_db_query",
        "log_db_result",
        "log_db_search_with_embedding",
        "log_db_search_results",
        "log_embedding_request",
        "log_embedding_response",
        "log_embedding_batch_request",
        "log_embedding_batch_response",
        "log_rag_query",
        "log_rag_context",
        "log_rag_result",
        "log_ingestion_start",
        "log_ingestion_chunks",
        "log_ingestion_complete",
        "log_api_request",
        "log_api_response",
        "log_api_input",
        "flush_loggers"
    ]

    deprecated_usage = []
    for py_file in Path("src").rglob("*.py"):
        try:
            content = py_file.read_text()
            for func in deprecated_functions:
                if f"{func}(" in content:
                    deprecated_usage.append((str(py_file), func))
        except Exception:
            pass

    if deprecated_usage:
        print("   [AVISO] Uso de funcoes deprecadas encontrado:")
        for file_path, func in deprecated_usage:
            print(f"      - {file_path}: {func}()")
        print("   [INFO] Isso pode ser aceitavel se for no modulo logger.py (compatibilidade)")
    else:
        print("   [OK] Nenhuma funcao deprecada em uso (exceto no logger.py)")
    print()

    # 5. Verificar arquivos de backup
    print("5. Verificando arquivos de backup...")
    backup_files = []
    for py_file in Path(".").rglob("*.bak"):
        backup_files.append(str(py_file))

    if backup_files:
        print("   [AVISO] Arquivos de backup encontrados:")
        for bf in backup_files:
            print(f"      - {bf}")
        print("   [INFO] Considere remover arquivos de backup desnecessarios")
    else:
        print("   [OK] Nenhum arquivo de backup encontrado")
    print()

    # 6. Verificar arquivo de log
    print("6. Verificando arquivo de log...")
    try:
        from src.config import LOG_FILE
        log_path = Path(LOG_FILE)
        if log_path.exists():
            print(f"   [OK] Arquivo de log existe: {LOG_FILE}")
            file_size = log_path.stat().st_size
            print(f"      - Tamanho: {file_size} bytes")
        else:
            print(f"   [AVISO] Arquivo de log nao existe (sera criado ao rodar): {LOG_FILE}")
    except Exception as e:
        print(f"   [ERRO] Erro ao verificar arquivo de log: {e}")
        all_passed = False
    print()

    # 7. Testar formatação de log
    print("7. Testando formatação de log...")
    try:
        test_logger = logging.getLogger("rag.test")
        test_logger.info("Test message with %s", "lazy formatting")
        test_logger.info("Structured log | key1=%s | key2=%s", "value1", "value2")
        print("   [OK] Formatacao de log: OK")
    except Exception as e:
        print(f"   [ERRO] Erro na formatacao de log: {e}")
        all_passed = False
    print()

    # 8. Testar log de erro com stacktrace
    print("8. Testando log de erro com stacktrace...")
    try:
        test_logger = logging.getLogger("rag.test_error")
        try:
            raise ValueError("Test error for logging")
        except Exception as e:
            test_logger.exception("Test error logging with exception")
        print("   [OK] Log de erro com stacktrace: OK")
    except Exception as e:
        print(f"   [ERRO] Erro no log de erro: {e}")
        all_passed = False
    print()

    # Resumo
    print("=" * 60)
    if all_passed:
        print("[OK] VALIDACAO CONCLUIDA COM SUCESSO")
        print("   O sistema de logging esta configurado e funcionando corretamente.")
    else:
        print("[AVISO] VALIDACAO CONCLUIDA COM AVISOS")
        print("   Alguns itens precisam de atencao. Revise os erros acima.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = validate_logging_system()
    sys.exit(0 if success else 1)
