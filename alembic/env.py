"""Alembic migrations configuration for PT Tax Intelligence Layer."""

import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine

# Alembic Config object
config = context.config

# Import models for autogenerate
from app.database.models import Base
from app.data.memory.graph.models import Base as GraphBase
target_metadata = Base.metadata

# Merge graph models into target_metadata
GraphBase.metadata.tables  # force load
for table in GraphBase.metadata.tables.values():
    if table.name not in target_metadata.tables:
        table.tometadata(target_metadata)


def get_url():
    """Get database URL from environment or config."""
    # Use sync URL for migrations
    url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tax_intelligence")
    return url


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    url = get_url()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()