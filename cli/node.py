import asyncio
import errno
import json
import os
import stat
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.db.base import GetDB
from app.db.crud.node import get_node_by_id, modify_node as crud_modify_node
from app.models.node import NodeModify
from app.operation import OperatorType
from app.operation.node import NodeOperation


class NodePairingBundle(BaseModel):
    api_key: str
    server_ca: str

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_node_credentials(self):
        NodeModify(api_key=self.api_key, server_ca=self.server_ca)
        return self


def _read_pairing_file(pairing_file: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(pairing_file, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError("Pairing path must be a regular file") from None
        raise

    try:
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("Pairing path must be a regular file")
        if metadata.st_size > 16_384:
            raise ValueError("Pairing file is too large")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError("Pairing file permissions must not allow group or other access")

        with os.fdopen(file_descriptor, encoding="utf-8") as pairing_stream:
            file_descriptor = -1
            return pairing_stream.read()
    except UnicodeDecodeError:
        raise ValueError("Invalid pairing file encoding") from None
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)


def _load_pairing_bundle(pairing_file: Path) -> NodePairingBundle:
    try:
        payload = json.loads(_read_pairing_file(pairing_file))
    except json.JSONDecodeError:
        raise ValueError("Invalid pairing JSON") from None

    try:
        return NodePairingBundle.model_validate(payload)
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
        field_list = ", ".join(fields) if fields else "credentials"
        raise ValueError(f"Invalid pairing file fields: {field_list}") from None


async def _wait_for_reconnect(db, node_id: int):
    refreshed = None
    for attempt in range(30):
        refreshed = await get_node_by_id(db, node_id, load_usage_logs=False)
        if refreshed is None:
            raise ValueError(f"Node {node_id} not found after pairing")
        if refreshed.status.value in {"connected", "error", "disabled", "limited"}:
            return refreshed
        if attempt < 29:
            await asyncio.sleep(1)
    return refreshed


async def _restore_pairing(db, node_id: int, db_node, original: NodeModify, operation: NodeOperation) -> bool:
    try:
        await crud_modify_node(db, db_node, original)
        await operation.connect_single_node(db, node_id, force_start=True)
    except Exception:
        return False
    return True


async def _pair_node(node_id: int, pairing_file: Path) -> str:
    bundle = _load_pairing_bundle(pairing_file)
    async with GetDB() as db:
        db_node = await get_node_by_id(db, node_id, load_usage_logs=False)
        if db_node is None:
            raise ValueError(f"Node {node_id} not found")

        original = NodeModify(api_key=db_node.api_key, server_ca=db_node.server_ca)
        modify = NodeModify(api_key=bundle.api_key, server_ca=bundle.server_ca)
        await crud_modify_node(db, db_node, modify)

        operation = NodeOperation(OperatorType.CLI)
        try:
            await operation.connect_single_node(db, node_id, force_start=True)
            refreshed = await _wait_for_reconnect(db, node_id)
        except Exception:
            rollback_ok = await _restore_pairing(db, node_id, db_node, original, operation)
            if not rollback_ok:
                raise ValueError(f"Node {node_id} pairing reconnect failed and rollback failed") from None
            raise ValueError(f"Node {node_id} pairing updated but reconnect failed") from None

        if refreshed.status.value == "connected":
            return refreshed.status.value

        rollback_ok = await _restore_pairing(db, node_id, refreshed, original, operation)
        if not rollback_ok:
            raise ValueError(f"Node {node_id} pairing reconnect failed and rollback failed")
        raise ValueError(f"Node {node_id} pairing updated but reconnect failed")


def pair_node(node_id: int, pairing_file: Path) -> str:
    if os.geteuid() != 0:
        raise PermissionError("pair-node must be run as root")
    return asyncio.run(_pair_node(node_id, pairing_file))
