import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Configuração do Alembic
config = context.config

# Interpretar o arquivo de log se presente
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Determinar URL do banco: primeiro DATABASE_URL, senão src.config
_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    ROOT_DIR = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT_DIR))
    from src.config import DATABASE_URL as _CONFIG_URL

    _db_url = _CONFIG_URL

config.set_main_option("sqlalchemy.url", _db_url)

# Não usamos metadata/autogenerate por ora
target_metadata = None


def run_migrations_offline():
    """
    Executa migrações em modo offline.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Executa migrações em modo online.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
