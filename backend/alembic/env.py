"""Alembic env — lit l'URL depuis la config applicative."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from meoxa_secretary.config import get_settings
from meoxa_secretary.models import Base  # noqa: F401 — peuple Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Par défaut Alembic crée `alembic_version.version_num` en VARCHAR(32),
    # ce qui coupe les revisions à noms descriptifs > 32 car. On élargit
    # préemptivement sur une connexion dédiée pour ne pas contaminer la
    # transaction de migration en cas d'erreur (table inexistante au 1er run).
    try:
        with connectable.connect() as prep:
            prep.execute(
                text(
                    "ALTER TABLE alembic_version "
                    "ALTER COLUMN version_num TYPE varchar(128)"
                )
            )
            prep.commit()
    except Exception:
        pass  # table pas encore créée (1re install) — no-op

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
