import json
import re
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from typer.testing import CliRunner

from cli import node as node_cli
from cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _run_pairing_tests_as_root(monkeypatch):
    monkeypatch.setattr(node_cli.os, "geteuid", lambda: 0)


def make_certificate() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pairing.test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_pair_node_command_exposes_file_only_interface():
    result = runner.invoke(app, ["pair-node", "--help"])

    assert result.exit_code == 0, result.output
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--file" in output
    assert "API key" not in output
    assert "server-ca" not in output


def test_pair_node_rejects_group_or_world_readable_pairing_file(tmp_path):
    pairing_file = tmp_path / "pairing.json"
    pairing_file.write_text(
        json.dumps(
            {
                "api_key": "123e4567-e89b-12d3-a456-426614174000",
                "server_ca": "not-read-because-permissions-fail-first",
            }
        )
    )
    pairing_file.chmod(0o644)

    with pytest.raises(ValueError, match="permissions"):
        node_cli.pair_node(1, pairing_file)


def test_pair_node_requires_root_execution(monkeypatch, tmp_path):
    pairing_file = tmp_path / "pairing.json"
    pairing_file.write_text("{}")
    pairing_file.chmod(0o600)
    monkeypatch.setattr(node_cli.os, "geteuid", lambda: 1000)

    with pytest.raises(PermissionError, match="root"):
        node_cli.pair_node(1, pairing_file)


def test_pair_node_rejects_invalid_certificate_before_db_access(tmp_path):
    pairing_file = tmp_path / "pairing.json"
    pairing_file.write_text(
        json.dumps(
            {
                "api_key": "123e4567-e89b-12d3-a456-426614174000",
                "server_ca": "not-a-certificate",
            }
        )
    )
    pairing_file.chmod(0o600)

    with pytest.raises(ValueError, match="server_ca"):
        node_cli.pair_node(1, pairing_file)


@pytest.mark.asyncio
async def test_pair_node_updates_credentials_and_force_reconnects(monkeypatch, tmp_path):
    async_pair = getattr(node_cli, "_pair_node", None)
    assert async_pair is not None

    bundle = type(
        "Bundle",
        (),
        {"api_key": "123e4567-e89b-12d3-a456-426614174000", "server_ca": make_certificate()},
    )()
    monkeypatch.setattr(node_cli, "_load_pairing_bundle", lambda _: bundle)

    db = object()
    db_node = type(
        "Node",
        (),
        {
            "id": 7,
            "status": type("Status", (), {"value": "connected"})(),
            "api_key": "223e4567-e89b-12d3-a456-426614174001",
            "server_ca": make_certificate(),
        },
    )()
    calls = {}

    class FakeDB:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *_):
            return False

    async def fake_get_node(_db, node_id, **_kwargs):
        assert _db is db
        return db_node if node_id == 7 else None

    async def fake_modify(_db, node, modify):
        calls["modify"] = (_db, node, modify)
        return node

    class FakeNodeOperation:
        def __init__(self, operator_type):
            calls["operator_type"] = operator_type

        async def connect_single_node(self, _db, node_id, *, force_start=False):
            calls["connect"] = (_db, node_id, force_start)

    monkeypatch.setattr(node_cli, "GetDB", FakeDB, raising=False)
    monkeypatch.setattr(node_cli, "get_node_by_id", fake_get_node, raising=False)
    monkeypatch.setattr(node_cli, "crud_modify_node", fake_modify, raising=False)
    monkeypatch.setattr(node_cli, "NodeOperation", FakeNodeOperation, raising=False)

    status = await async_pair(7, tmp_path / "unused.json")

    _, _, modify = calls["modify"]
    assert modify.api_key == bundle.api_key
    assert modify.server_ca == bundle.server_ca.strip()
    assert calls["connect"] == (db, 7, True)
    assert status == "connected"


@pytest.mark.asyncio
async def test_pair_node_waits_for_async_reconnect(monkeypatch, tmp_path):
    bundle = type(
        "Bundle",
        (),
        {"api_key": "123e4567-e89b-12d3-a456-426614174000", "server_ca": make_certificate()},
    )()
    monkeypatch.setattr(node_cli, "_load_pairing_bundle", lambda _: bundle)

    db = object()
    states = iter(["error", "connecting", "connected"])

    class FakeDB:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *_):
            return False

    async def fake_get_node(_db, node_id, **_kwargs):
        status = type("Status", (), {"value": next(states)})()
        return type(
            "Node",
            (),
            {
                "id": node_id,
                "status": status,
                "api_key": "223e4567-e89b-12d3-a456-426614174001",
                "server_ca": make_certificate(),
            },
        )()

    async def fake_modify(_db, node, modify):
        return node

    class FakeNodeOperation:
        def __init__(self, operator_type):
            pass

        async def connect_single_node(self, _db, node_id, *, force_start=False):
            return None

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(node_cli, "GetDB", FakeDB)
    monkeypatch.setattr(node_cli, "get_node_by_id", fake_get_node)
    monkeypatch.setattr(node_cli, "crud_modify_node", fake_modify)
    monkeypatch.setattr(node_cli, "NodeOperation", FakeNodeOperation)
    monkeypatch.setattr(node_cli.asyncio, "sleep", no_sleep)

    status = await node_cli._pair_node(7, tmp_path / "unused.json")

    assert status == "connected"


@pytest.mark.asyncio
async def test_pair_node_polls_fresh_sessions_until_connected(monkeypatch, tmp_path):
    bundle = type(
        "Bundle",
        (),
        {"api_key": "123e4567-e89b-12d3-a456-426614174000", "server_ca": make_certificate()},
    )()
    monkeypatch.setattr(node_cli, "_load_pairing_bundle", lambda _: bundle)

    write_db = object()
    poll_error_db = object()
    poll_connected_db = object()
    db_contexts = iter([write_db, poll_error_db, poll_connected_db])
    db_node = type(
        "Node",
        (),
        {
            "id": 7,
            "status": type("Status", (), {"value": "error"})(),
            "api_key": "223e4567-e89b-12d3-a456-426614174001",
            "server_ca": make_certificate(),
        },
    )()
    modifies = []

    class FakeDB:
        def __init__(self):
            self.db = next(db_contexts)

        async def __aenter__(self):
            return self.db

        async def __aexit__(self, *_):
            return False

    async def fake_get_node(_db, node_id, **_kwargs):
        assert node_id == 7
        if _db is write_db:
            return db_node
        state = "error" if _db is poll_error_db else "connected"
        return type("Node", (), {"status": type("Status", (), {"value": state})()})()

    async def fake_modify(_db, node, modify):
        modifies.append(modify.api_key)
        node.api_key = modify.api_key
        node.server_ca = modify.server_ca
        node.status = type("Status", (), {"value": "connecting"})()
        return node

    class FakeNodeOperation:
        def __init__(self, operator_type):
            pass

        async def connect_single_node(self, _db, node_id, *, force_start=False):
            assert _db is write_db
            assert node_id == 7
            assert force_start is True

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(node_cli, "GetDB", FakeDB)
    monkeypatch.setattr(node_cli, "get_node_by_id", fake_get_node)
    monkeypatch.setattr(node_cli, "crud_modify_node", fake_modify)
    monkeypatch.setattr(node_cli, "NodeOperation", FakeNodeOperation)
    monkeypatch.setattr(node_cli.asyncio, "sleep", no_sleep)

    status = await node_cli._pair_node(7, tmp_path / "unused.json")

    assert status == "connected"
    assert modifies == [bundle.api_key]


@pytest.mark.asyncio
async def test_pair_node_restores_previous_credentials_when_reconnect_fails(monkeypatch, tmp_path):
    new_certificate = make_certificate()
    old_certificate = make_certificate()
    bundle = type(
        "Bundle",
        (),
        {"api_key": "123e4567-e89b-12d3-a456-426614174000", "server_ca": new_certificate},
    )()
    monkeypatch.setattr(node_cli, "_load_pairing_bundle", lambda _: bundle)

    db = object()
    db_node = type(
        "Node",
        (),
        {
            "id": 7,
            "status": type("Status", (), {"value": "error"})(),
            "api_key": "223e4567-e89b-12d3-a456-426614174001",
            "server_ca": old_certificate,
        },
    )()
    modifies = []
    reconnects = []

    class FakeDB:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *_):
            return False

    async def fake_get_node(_db, node_id, **_kwargs):
        return db_node

    async def fake_modify(_db, node, modify):
        modifies.append((modify.api_key, modify.server_ca))
        node.api_key = modify.api_key
        node.server_ca = modify.server_ca
        return node

    class FakeNodeOperation:
        def __init__(self, operator_type):
            pass

        async def connect_single_node(self, _db, node_id, *, force_start=False):
            reconnects.append((node_id, force_start))

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(node_cli, "GetDB", FakeDB)
    monkeypatch.setattr(node_cli, "get_node_by_id", fake_get_node)
    monkeypatch.setattr(node_cli, "crud_modify_node", fake_modify)
    monkeypatch.setattr(node_cli, "NodeOperation", FakeNodeOperation)
    monkeypatch.setattr(node_cli.asyncio, "sleep", no_sleep)

    with pytest.raises(ValueError, match="reconnect failed"):
        await node_cli._pair_node(7, tmp_path / "unused.json")

    assert modifies == [
        (bundle.api_key, bundle.server_ca.strip()),
        ("223e4567-e89b-12d3-a456-426614174001", old_certificate.strip()),
    ]
    assert reconnects == [(7, True), (7, True)]


@pytest.mark.asyncio
async def test_pair_node_reports_rollback_failure_without_exposing_secrets(monkeypatch, tmp_path):
    bundle = type(
        "Bundle",
        (),
        {"api_key": "123e4567-e89b-12d3-a456-426614174000", "server_ca": make_certificate()},
    )()
    monkeypatch.setattr(node_cli, "_load_pairing_bundle", lambda _: bundle)

    db = object()
    old_api_key = "223e4567-e89b-12d3-a456-426614174001"
    old_certificate = make_certificate()
    db_node = type(
        "Node",
        (),
        {
            "id": 7,
            "status": type("Status", (), {"value": "error"})(),
            "api_key": old_api_key,
            "server_ca": old_certificate,
        },
    )()
    modify_count = 0

    class FakeDB:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *_):
            return False

    async def fake_get_node(_db, node_id, **_kwargs):
        return db_node

    async def fake_modify(_db, node, modify):
        nonlocal modify_count
        modify_count += 1
        if modify_count == 2:
            raise RuntimeError("synthetic rollback failure containing " + old_api_key)
        return node

    class FakeNodeOperation:
        def __init__(self, operator_type):
            pass

        async def connect_single_node(self, _db, node_id, *, force_start=False):
            return None

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(node_cli, "GetDB", FakeDB)
    monkeypatch.setattr(node_cli, "get_node_by_id", fake_get_node)
    monkeypatch.setattr(node_cli, "crud_modify_node", fake_modify)
    monkeypatch.setattr(node_cli, "NodeOperation", FakeNodeOperation)
    monkeypatch.setattr(node_cli.asyncio, "sleep", no_sleep)

    with pytest.raises(ValueError) as error:
        await node_cli._pair_node(7, tmp_path / "unused.json")

    message = str(error.value)
    assert "rollback failed" in message
    assert old_api_key not in message
    assert bundle.api_key not in message
    assert "BEGIN CERTIFICATE" not in message


def test_pair_node_rejects_symlink_even_when_target_is_private(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(
        json.dumps(
            {
                "api_key": "123e4567-e89b-12d3-a456-426614174000",
                "server_ca": "not-a-certificate",
            }
        )
    )
    target.chmod(0o600)
    pairing_file = tmp_path / "pairing.json"
    pairing_file.symlink_to(target)

    with pytest.raises(ValueError, match="regular file"):
        node_cli.pair_node(1, pairing_file)


def test_pair_node_rejects_oversized_pairing_file_before_parsing(tmp_path):
    pairing_file = tmp_path / "pairing.json"
    pairing_file.write_text("x" * 20_000)
    pairing_file.chmod(0o600)

    with pytest.raises(ValueError, match="too large"):
        node_cli.pair_node(1, pairing_file)


def test_pairing_bundle_accepts_valid_credentials(tmp_path):
    pairing_file = tmp_path / "pairing.json"
    certificate = make_certificate()
    api_key = "123e4567-e89b-12d3-a456-426614174000"
    pairing_file.write_text(json.dumps({"api_key": api_key, "server_ca": certificate}))
    pairing_file.chmod(0o600)

    bundle = node_cli._load_pairing_bundle(pairing_file)

    assert bundle.api_key == api_key
    assert bundle.server_ca == certificate


def test_pairing_bundle_rejects_unknown_fields(tmp_path):
    pairing_file = tmp_path / "pairing.json"
    pairing_file.write_text(
        json.dumps(
            {
                "api_key": "123e4567-e89b-12d3-a456-426614174000",
                "server_ca": make_certificate(),
                "unexpected": "value",
            }
        )
    )
    pairing_file.chmod(0o600)

    with pytest.raises(ValueError):
        node_cli._load_pairing_bundle(pairing_file)


def test_pair_node_runtime_output_does_not_echo_pairing_secrets(monkeypatch, tmp_path):
    pairing_file = tmp_path / "pairing.json"
    api_key = "123e4567-e89b-12d3-a456-426614174000"
    certificate = make_certificate()
    pairing_file.write_text(json.dumps({"api_key": api_key, "server_ca": certificate}))
    pairing_file.chmod(0o600)
    monkeypatch.setattr("cli.main.pair_node", lambda _node_id, _file: "connected")

    result = runner.invoke(app, ["pair-node", "7", "--file", str(pairing_file)])

    assert result.exit_code == 0, result.output
    assert "Node 7 pairing updated" in result.output
    assert "connected" in result.output
    assert api_key not in result.output
    assert "BEGIN CERTIFICATE" not in result.output


def test_pairing_validation_error_does_not_expose_secret_values(tmp_path):
    pairing_file = tmp_path / "pairing.json"
    secret_api_key = "SECRET-API-KEY-MUST-NOT-LEAK"
    secret_certificate = "SECRET-CERTIFICATE-MUST-NOT-LEAK"
    pairing_file.write_text(
        json.dumps({"api_key": secret_api_key, "server_ca": secret_certificate})
    )
    pairing_file.chmod(0o600)

    with pytest.raises(ValueError) as error:
        node_cli._load_pairing_bundle(pairing_file)

    message = str(error.value)
    assert secret_api_key not in message
    assert secret_certificate not in message


@pytest.mark.asyncio
async def test_pair_node_fails_when_reconnect_does_not_connect(monkeypatch, tmp_path):
    bundle = type(
        "Bundle",
        (),
        {"api_key": "123e4567-e89b-12d3-a456-426614174000", "server_ca": make_certificate()},
    )()
    monkeypatch.setattr(node_cli, "_load_pairing_bundle", lambda _: bundle)
    db = object()
    states = iter(["connected", "error"])

    class FakeDB:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *_):
            return False

    async def fake_get_node(_db, node_id, **_kwargs):
        status = type("Status", (), {"value": next(states)})()
        return type(
            "Node",
            (),
            {
                "id": node_id,
                "status": status,
                "api_key": "223e4567-e89b-12d3-a456-426614174001",
                "server_ca": make_certificate(),
            },
        )()

    async def fake_modify(_db, node, modify):
        return node

    class FakeNodeOperation:
        def __init__(self, operator_type):
            pass

        async def connect_single_node(self, _db, node_id, *, force_start=False):
            return None

    monkeypatch.setattr(node_cli, "GetDB", FakeDB)
    monkeypatch.setattr(node_cli, "get_node_by_id", fake_get_node)
    monkeypatch.setattr(node_cli, "crud_modify_node", fake_modify)
    monkeypatch.setattr(node_cli, "NodeOperation", FakeNodeOperation)

    with pytest.raises(ValueError, match="reconnect failed"):
        await node_cli._pair_node(7, tmp_path / "unused.json")
