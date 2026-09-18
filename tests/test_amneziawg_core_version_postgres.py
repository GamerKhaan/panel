import asyncio
import os
from uuid import uuid4

import pytest
from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.crud.node import update_node_status
from app.db.models import Node, NodeStatus

AWG_CORE_VERSION = (
    "amneziawg-go v3.1.20260814 in-process "
    "(1b86b2ae0e493e7ea93f8c1a0f0cb6735b1551f1; "
    "h1:l2AhBD+sFycU8Im81n/bZORMxW7fWtlZJEuJ4Hh0+z0=)"
)
NODE_VERSION = "0.5.4"


def _postgres_urls() -> tuple[str, str]:
    async_url = os.environ.get("SQLALCHEMY_DATABASE_URL", "")
    if not async_url.startswith("postgresql+asyncpg://"):
        pytest.skip("requires the isolated PostgreSQL migration gate")
    return async_url, async_url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)


def _alembic_config(sync_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", sync_url)
    return config


def _column_contract(sync_url: str) -> tuple[str, int | None]:
    engine = create_engine(sync_url)
    try:
        column = next(column for column in inspect(engine).get_columns("nodes") if column["name"] == "xray_version")
        return str(column["type"]), getattr(column["type"], "length", None)
    finally:
        engine.dispose()


def _migration_head(sync_url: str) -> str:
    engine = create_engine(sync_url)
    try:
        with engine.connect() as connection:
            return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()


def _migrate(sync_url: str, action, revision: str) -> None:
    engine = create_engine(sync_url)
    try:
        with engine.begin() as connection:
            config = _alembic_config(sync_url)
            config.attributes["connection"] = connection
            action(config, revision)
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_connected_status_preserves_complete_awg_version_and_downgrade_is_safe() -> None:
    async_url, sync_url = _postgres_urls()
    engine = create_async_engine(async_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    node_id: int

    async with sessions() as session:
        node = Node(
            name=f"m2-version-{uuid4().hex[:10]}",
            address="127.0.0.1",
            port=62050,
            api_port=62051,
            server_ca="isolated-test-ca",
            api_key=None,
            core_config_id=None,
        )
        session.add(node)
        await session.commit()
        await session.refresh(node)
        node_id = node.id
        await update_node_status(
            db=session,
            db_node=node,
            status=NodeStatus.connected,
            xray_version=AWG_CORE_VERSION,
            node_version=NODE_VERSION,
        )

    async with sessions() as session:
        persisted = (await session.execute(select(Node).where(Node.id == node_id))).scalar_one()
        assert persisted.status is NodeStatus.connected
        assert persisted.xray_version == AWG_CORE_VERSION
        assert persisted.node_version == NODE_VERSION

    await engine.dispose()
    assert len(AWG_CORE_VERSION) > 32
    assert _column_contract(sync_url) == ("TEXT", None)

    with pytest.raises(
        RuntimeError,
        match="Refusing to narrow nodes.xray_version to 32 characters while longer values exist",
    ):
        await asyncio.to_thread(_migrate, sync_url, downgrade, "pgawg0001")
    assert _migration_head(sync_url) == "pgawg0002"

    engine = create_async_engine(async_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        persisted = (await session.execute(select(Node).where(Node.id == node_id))).scalar_one()
        assert persisted.status is NodeStatus.connected
        assert persisted.xray_version == AWG_CORE_VERSION
        await session.delete(persisted)
        await session.commit()
    await engine.dispose()

    await asyncio.to_thread(_migrate, sync_url, downgrade, "pgawg0001")
    assert _migration_head(sync_url) == "pgawg0001"
    assert _column_contract(sync_url) == ("VARCHAR(32)", 32)

    await asyncio.to_thread(_migrate, sync_url, upgrade, "head")
    assert _migration_head(sync_url) == "pgawg0002"
    assert _column_contract(sync_url) == ("TEXT", None)
