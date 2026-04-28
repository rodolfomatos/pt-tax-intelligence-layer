"""Alembic migrations configuration for PT Tax Intelligence Layer."""

import os
from alembic import context
from alembic.env import include_object
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

# Alembic Config object
config = context.config

# Import models for autogenerate
from app.database.models import Base
from app.data.memory.graph.models import Base as GraphBase
target_metadata = Base.metadata

# Add graph models
for table in GraphBase.metadata.tables.values():
    if table not in target_metadata.tables.values():
        target_metadata.append_table(table)


def get_url():
    """Get database URL from environment or config."""
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tax_intelligence")


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
    
    connectable = create_async_engine(
        url.replace("postgresql://", "postgresql+asyncpg://"),
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