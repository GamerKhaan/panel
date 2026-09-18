from __future__ import annotations

import json
import re
from copy import deepcopy
from ipaddress import ip_interface
from pathlib import PosixPath

import commentjson

from app.models.core import CoreType
from app.models.protocol import ProxyProtocol
from app.utils.crypto import get_wireguard_public_key, validate_wireguard_key

AWG_SCHEMA_VERSION = 1
AWG_IMPLEMENTATION = "GamerKhaan/pasarguard-awg31-patch"
_AWG_PROTOCOLS = frozenset((ProxyProtocol.wireguard,))
_INTERFACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,14}$")
_RANGE_RE = re.compile(r"^[0-9]+(?:-[0-9]+)?$")
_INTEGER_FIELDS = frozenset(("jc", "jmin", "jmax", "s1", "s2", "s3", "s4"))
_RANGE_FIELDS = {
    "h1": 4294967295,
    "h2": 4294967295,
    "h3": 4294967295,
    "h4": 4294967295,
    "content_padding_addition": 65535,
    "rekey_after_time": 65535,
    "rekey_timeout": 65535,
    "reject_after_time": 65535,
    "keepalive_timeout": 65535,
    "max_handshake_attempts": 65535,
}
_BOOLEAN_FIELDS = frozenset(("random_trailers", "disable_cookies"))
_DEVICE_FIELDS = frozenset(
    ("interface_name", "private_key", "pre_shared_key", "listen_port", "address", "awg")
)


def _validate_range(name: str, value: object, maximum: int) -> str:
    if not isinstance(value, str) or not _RANGE_RE.fullmatch(value):
        raise ValueError(f"AWG {name} requires a decimal value or ascending range string")
    bounds = [int(part) for part in value.split("-")]
    if bounds[0] > maximum or (len(bounds) == 2 and (bounds[1] > maximum or bounds[1] < bounds[0])):
        raise ValueError(f"AWG {name} has invalid range bounds")
    return value


class AmneziaWGConfig(dict):
    """Versioned panel envelope for the distinct patched AmneziaWG backend.

    Unknown envelope members are retained for compatible export/round-trip. Only
    the explicit device subset is sent to the M1 node implementation.
    """

    def __init__(
        self,
        config: dict | str | PosixPath | None = None,
        exclude_inbound_tags: set[str] | None = None,
        fallbacks_inbound_tags: set[str] | None = None,
        skip_validation: bool = False,
    ):
        if config is None:
            config = {}
        if isinstance(config, str):
            config = commentjson.loads(config)
        if isinstance(config, dict):
            config = deepcopy(config)
        super().__init__(config)
        self._type = CoreType.gamerkhaan_amneziawg
        self.exclude_inbound_tags = set(exclude_inbound_tags or set())
        self.fallbacks_inbound_tags = set(fallbacks_inbound_tags or set())
        self._inbounds: list[str] = []
        self._inbounds_by_tag: dict[str, dict] = {}
        if skip_validation:
            return
        self._validate()
        self._resolve_inbounds()

    @property
    def type(self) -> str:
        return self._type

    def _validate(self) -> None:
        if self.exclude_inbound_tags or self.fallbacks_inbound_tags:
            raise ValueError("inbound exclusion and fallbacks are only supported for xray cores")
        if self.get("schema_version") != AWG_SCHEMA_VERSION:
            raise ValueError(f"unsupported AmneziaWG schema_version; expected {AWG_SCHEMA_VERSION}")
        if self.get("implementation") != AWG_IMPLEMENTATION:
            raise ValueError(f"unsupported AmneziaWG implementation; expected {AWG_IMPLEMENTATION}")

        interface_name = self.get("interface_name")
        if not isinstance(interface_name, str) or not _INTERFACE_RE.fullmatch(interface_name):
            raise ValueError("AmneziaWG requires a safe interface_name of at most 15 characters")
        self["private_key"] = validate_wireguard_key(str(self.get("private_key") or ""), "private_key")
        self["public_key"] = get_wireguard_public_key(self["private_key"])
        psk = self.get("pre_shared_key")
        if psk:
            self["pre_shared_key"] = validate_wireguard_key(str(psk), "pre_shared_key")

        port = self.get("listen_port")
        if not isinstance(port, int) or isinstance(port, bool) or port < 0 or port > 65535:
            raise ValueError("listen_port must be an integer between 0 and 65535")
        addresses = self.get("address")
        if not isinstance(addresses, list) or not 1 <= len(addresses) <= 8:
            raise ValueError("address must contain between one and eight interface prefixes")
        self["address"] = [str(ip_interface(value)) for value in addresses]

        awg = self.get("awg")
        if not isinstance(awg, dict):
            raise ValueError("awg must be an object")
        normalized: dict[str, object] = {}
        for name, value in awg.items():
            if name in _INTEGER_FIELDS:
                if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 65535:
                    raise ValueError(f"AWG {name} requires an unsigned 16-bit integer")
            elif name in _RANGE_FIELDS:
                value = _validate_range(name, value, _RANGE_FIELDS[name])
            elif name == "header_protection_key":
                value = validate_wireguard_key(str(value), "header_protection_key")
            elif name in _BOOLEAN_FIELDS:
                if not isinstance(value, bool):
                    raise ValueError(f"AWG {name} requires a boolean")
            else:
                raise ValueError(f"unsupported AWG field {name!r}")
            normalized[name] = value
        if normalized.get("header_protection_key"):
            if any(normalized.get(name, 0) < 12 for name in ("s1", "s2", "s3", "s4")):
                raise ValueError("header protection requires S1-S4 >= 12")
        if int(normalized.get("jmin", 0)) > int(normalized.get("jmax", 0)):
            raise ValueError("jmin must not exceed jmax")
        ranges = [_validate_range(name, normalized.get(name, str(i + 1)), 4294967295) for i, name in enumerate(("h1", "h2", "h3", "h4"))]
        parsed = [tuple(int(part) for part in value.split("-")) for value in ranges]
        parsed = [(value[0], value[-1]) for value in parsed]
        for i, current in enumerate(parsed):
            if any(current[0] <= prior[1] and prior[0] <= current[1] for prior in parsed[:i]):
                raise ValueError("AWG header ranges must not overlap")
        self["awg"] = normalized

    def _resolve_inbounds(self) -> None:
        tag = self["interface_name"]
        metadata = {
            "tag": tag,
            "protocol": "wireguard",
            "renderer": "amneziawg-native-v1",
            "backend_type": CoreType.gamerkhaan_amneziawg.value,
            "network": "udp",
            "tls": "none",
            "interface_name": tag,
            "listen_port": self["listen_port"],
            "address": list(self["address"]),
            "public_key": self["public_key"],
            "pre_shared_key": self.get("pre_shared_key"),
            "awg": deepcopy(self["awg"]),
            "schema_version": self["schema_version"],
            "implementation": self["implementation"],
        }
        self._inbounds = [tag]
        self._inbounds_by_tag = {tag: metadata}

    def to_str(self, **json_kwargs) -> str:
        payload = {name: deepcopy(self[name]) for name in _DEVICE_FIELDS if name in self}
        return json.dumps(payload, **json_kwargs)

    @property
    def inbounds_by_tag(self) -> dict:
        return self._inbounds_by_tag

    @property
    def inbounds(self) -> list[str]:
        return self._inbounds

    @property
    def protocols(self) -> frozenset[ProxyProtocol]:
        return _AWG_PROTOCOLS

    def to_json(self) -> dict:
        return {
            "type": self.type,
            "config": deepcopy(dict(self)),
            "exclude_inbound_tags": [],
            "fallbacks_inbound_tags": [],
            "inbounds": list(self.inbounds),
            "inbounds_by_tag": deepcopy(self.inbounds_by_tag),
        }

    @classmethod
    def from_json(cls, data: dict) -> "AmneziaWGConfig":
        instance = cls(config=data.get("config", {}))
        return instance

    def copy(self):
        return deepcopy(self)
