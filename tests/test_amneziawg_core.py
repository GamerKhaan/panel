import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PasarGuardNodeBridge.controller import NodeAPIError

from app.core.amneziawg import AWG_IMPLEMENTATION, AmneziaWGConfig
from app.db.models import CoreType
from app.operation.node import NodeOperation
from app.utils.crypto import generate_wireguard_keypair


def valid_config() -> dict:
    private_key, _ = generate_wireguard_keypair()
    return {
        "schema_version": 1,
        "implementation": AWG_IMPLEMENTATION,
        "interface_name": "awgm2",
        "private_key": private_key,
        "listen_port": 51820,
        "address": ["10.70.0.1/24"],
        "awg": {
            "jc": 0,
            "jmin": 0,
            "jmax": 0,
            "s1": 16,
            "s2": 20,
            "s3": 12,
            "s4": 24,
            "h1": "10001-10010",
            "h2": "20001-20010",
            "h3": "30001-30010",
            "h4": "40001-40010",
            "content_padding_addition": "0-16",
            "random_trailers": False,
            "disable_cookies": False,
        },
        "portable_extension": {"owner": "preserved"},
    }


def test_awg_envelope_cache_roundtrip_and_node_projection() -> None:
    config = AmneziaWGConfig(valid_config())
    assert config.type is CoreType.gamerkhaan_amneziawg
    assert config["portable_extension"] == {"owner": "preserved"}
    cached = AmneziaWGConfig.from_json(config.to_json())
    assert dict(cached) == dict(config)

    node_payload = json.loads(config.to_str())
    assert "schema_version" not in node_payload
    assert "implementation" not in node_payload
    assert "portable_extension" not in node_payload
    assert node_payload["awg"]["jc"] == 0
    assert node_payload["awg"]["random_trailers"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    (("schema_version", 2), ("implementation", "stock/amneziawg")),
)
def test_unsupported_identity_is_refused(field: str, value: object) -> None:
    payload = valid_config()
    payload[field] = value
    with pytest.raises(ValueError, match="unsupported AmneziaWG"):
        AmneziaWGConfig(payload)


def test_unknown_awg_device_field_is_refused() -> None:
    payload = valid_config()
    payload["awg"]["future_unsafe_device_field"] = 1
    with pytest.raises(ValueError, match="unsupported AWG field"):
        AmneziaWGConfig(payload)


def attested_node(**overrides):
    values = {
        "name": "isolated-attested",
        "address": "192.0.2.10",
        "port": 62050,
        "api_port": 62051,
        "connection_type": "grpc",
        "server_ca": "test-ca",
        "api_key": "test-api-key",
        "proxy_url": None,
        "keep_alive": 60,
        "awg_provenance_fingerprint": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_awg_provenance_normalizes_absent_proxy_like_managed_receipt() -> None:
    absent = NodeOperation._awg_provenance_fingerprint(attested_node(proxy_url=None))
    empty = NodeOperation._awg_provenance_fingerprint(attested_node(proxy_url=""))
    configured = NodeOperation._awg_provenance_fingerprint(
        attested_node(proxy_url="http://192.0.2.1:8080")
    )

    assert absent == empty
    assert configured != absent


@pytest.mark.asyncio
async def test_stopped_awg_restarts_only_with_matching_control_identity_attestation() -> None:
    db_node = attested_node()
    db_node.awg_provenance_fingerprint = NodeOperation._awg_provenance_fingerprint(db_node)
    started = SimpleNamespace(
        started=True,
        core_version="amneziawg-go v3.1.20260814 in-process (1b86b2ae0e493e7ea93f8c1a0f0cb6735b1551f1; exact)",
        node_version="0.5.4",
    )
    pg_node = SimpleNamespace(
        get_lifecycle_state=AsyncMock(return_value=None),
        info=AsyncMock(return_value=SimpleNamespace(started=False, core_version="", node_version="0.5.4")),
        start=AsyncMock(return_value=started),
    )
    core = SimpleNamespace(type=CoreType.gamerkhaan_amneziawg, to_str=lambda: "{}")

    result = await NodeOperation._start_or_attach_node(pg_node, db_node, core, [], backend_type=2)

    assert result is started
    pg_node.start.assert_awaited_once()


@pytest.mark.parametrize("field,value", [
    ("address", "192.0.2.11"), ("port", 63050), ("api_port", 63051),
    ("connection_type", "rest"), ("server_ca", "other-ca"),
    ("api_key", "other-test-key"), ("proxy_url", "http://192.0.2.1:8080"),
])
@pytest.mark.asyncio
async def test_awg_attestation_is_invalid_after_control_identity_change(field, value) -> None:
    db_node = attested_node()
    db_node.awg_provenance_fingerprint = NodeOperation._awg_provenance_fingerprint(db_node)
    setattr(db_node, field, value)
    pg_node = SimpleNamespace(
        get_lifecycle_state=AsyncMock(return_value=None),
        info=AsyncMock(return_value=SimpleNamespace(started=False, core_version="", node_version="0.5.4")),
        start=AsyncMock(),
    )
    core = SimpleNamespace(type=CoreType.gamerkhaan_amneziawg, to_str=lambda: "{}")

    with pytest.raises(NodeAPIError, match="provenance is absent or incompatible"):
        await NodeOperation._start_or_attach_node(pg_node, db_node, core, [], backend_type=2)

    pg_node.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_incompatible_node_is_refused_before_stop_or_start() -> None:
    pg_node = SimpleNamespace(
        info=AsyncMock(return_value=SimpleNamespace(started=True, core_version="wireguard-go", node_version="1")),
        stop=AsyncMock(),
        start=AsyncMock(),
    )
    core = SimpleNamespace(type=CoreType.gamerkhaan_amneziawg, to_str=lambda: "{}")
    db_node = SimpleNamespace(name="isolated-incompatible", keep_alive=0)

    with pytest.raises(NodeAPIError, match="provenance is absent or incompatible"):
        await NodeOperation._start_or_attach_node(
            pg_node,
            db_node,
            core,
            [],
            backend_type=2,
            force_start=True,
        )

    pg_node.stop.assert_not_awaited()
    pg_node.start.assert_not_awaited()


@pytest.mark.parametrize("stored", [False, True])
@pytest.mark.asyncio
async def test_running_incompatible_backend_overrides_stored_attestation(stored) -> None:
    db_node = attested_node()
    if stored:
        db_node.awg_provenance_fingerprint = NodeOperation._awg_provenance_fingerprint(db_node)
    pg_node = SimpleNamespace(
        info=AsyncMock(return_value=SimpleNamespace(started=True, core_version="wireguard-go")),
        stop=AsyncMock(), start=AsyncMock(),
    )
    core = SimpleNamespace(type=CoreType.gamerkhaan_amneziawg, to_str=lambda: "{}")
    with pytest.raises(NodeAPIError, match="provenance is absent or incompatible"):
        await NodeOperation._start_or_attach_node(pg_node, db_node, core, [], 2, force_start=True)
    pg_node.stop.assert_not_awaited()
    pg_node.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_stopped_awg_is_refused_without_mutation() -> None:
    db_node = attested_node()
    pg_node = SimpleNamespace(
        info=AsyncMock(return_value=SimpleNamespace(started=False, core_version="")),
        stop=AsyncMock(), start=AsyncMock(),
    )
    core = SimpleNamespace(type=CoreType.gamerkhaan_amneziawg, to_str=lambda: "{}")
    with pytest.raises(NodeAPIError, match="provenance is absent or incompatible"):
        await NodeOperation._start_or_attach_node(pg_node, db_node, core, [], 2, force_start=True)
    pg_node.stop.assert_not_awaited()
    pg_node.start.assert_not_awaited()
