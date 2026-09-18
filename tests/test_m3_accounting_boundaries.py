"""Bounded inherited reset/reply and DB-write loss-boundary regressions."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PasarGuardNodeBridge import NodeAPIError

from app.jobs import record_usages as jobs


class ResettingNode:
    def __init__(self, reply_lost=False):
        self.pending = 713
        self.reply_lost = reply_lost

    async def get_stats(self, *, stat_type, reset, timeout):
        assert reset is True
        value, self.pending = self.pending, 0
        if self.reply_lost:
            self.reply_lost = False
            raise NodeAPIError(-1, "injected reply lost after reset")
        return SimpleNamespace(stats=[SimpleNamespace(name="7", value=value)])


@pytest.mark.asyncio
async def test_inherited_reset_reply_loss_is_not_durable_or_replayed():
    node = ResettingNode(reply_lost=True)
    assert await jobs.get_users_stats(node, 1) == []
    assert node.pending == 0
    assert await jobs.get_users_stats(node, 1) == []


@pytest.mark.asyncio
async def test_inherited_db_failure_after_reset_has_no_durable_replay(monkeypatch):
    node = ResettingNode()
    monkeypatch.setattr(jobs.node_manager, "get_healthy_nodes", AsyncMock(return_value=[(1, node)]))
    async def collect(node, node_id):
        return node_id, 1.0, await jobs.get_users_stats(node, node_id)
    monkeypatch.setattr(jobs, "_collect_node_user_usage", collect)
    monkeypatch.setattr(jobs, "calculate_admin_usage", AsyncMock(return_value=({}, {7})))
    monkeypatch.setattr(jobs, "get_dialect", AsyncMock(return_value="postgresql"))
    write = AsyncMock(side_effect=RuntimeError("injected DB failure before commit"))
    monkeypatch.setattr(jobs, "safe_execute", write)
    with pytest.raises(RuntimeError, match="injected DB failure"):
        await jobs._record_user_usages_impl()
    write.assert_awaited_once()
    assert node.pending == 0
    write.reset_mock()
    await jobs._record_user_usages_impl()
    write.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_reset_is_folded_once():
    node = ResettingNode()
    assert await jobs.get_users_stats(node, 1) == [{"uid": 7, "value": 713}]
    assert await jobs.get_users_stats(node, 1) == []
