import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
from copy import deepcopy
from html.parser import HTMLParser
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from pydantic import ValidationError

from app.core.amneziawg import AWG_IMPLEMENTATION
from app.core.hosts import _prepare_subscription_inbound_data
from app.core.manager import core_manager
from app.models.host import BaseHost
from app.utils.crypto import generate_wireguard_keypair
from tests.api import client
from tests.api.helpers import (
    auth_headers,
    create_group,
    create_user,
    delete_core,
    delete_group,
    delete_user,
    unique_name,
)


_OMITTED = object()


class _NativeConfigHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.configs: list[str] = []
        self._current: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "textarea" and "native-config-input" in classes:
            self._current = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "textarea" and self._current is not None:
            self.configs.append("".join(self._current))
            self._current = None


def _awg_config(pre_shared_key: object = _OMITTED) -> dict:
    private_key, _ = generate_wireguard_keypair()
    config = {
        "schema_version": 1,
        "implementation": AWG_IMPLEMENTATION,
        "interface_name": unique_name("awgm2")[:15],
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
    }
    if pre_shared_key is not _OMITTED:
        config["pre_shared_key"] = pre_shared_key
    return config


def _host(inbound_tag: str) -> BaseHost:
    return BaseHost(
        remark="M2 AWG {USERNAME}",
        address={"198.51.100.10"},
        inbound_tag=inbound_tag,
        port=51820,
        priority=1,
    )


def _inbound(config: dict) -> dict:
    _, public_key = generate_wireguard_keypair()
    return {
        "protocol": "wireguard",
        "network": "udp",
        "listen_port": config["listen_port"],
        "address": config["address"],
        "public_key": public_key,
        "pre_shared_key": config.get("pre_shared_key"),
        "backend_type": "gamerkhaan_amneziawg",
        "renderer": "amneziawg-native-v1",
        "schema_version": 1,
        "implementation": AWG_IMPLEMENTATION,
        "awg": deepcopy(config["awg"]),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("pre_shared_key", (_OMITTED, None, ""))
async def test_awg_subscription_boundary_normalizes_absent_psk(monkeypatch, pre_shared_key: object) -> None:
    config = _awg_config(pre_shared_key)
    inbound = _inbound(config)
    if pre_shared_key is _OMITTED:
        inbound.pop("pre_shared_key")
    monkeypatch.setattr(core_manager, "get_inbound_by_tag", AsyncMock(return_value=inbound))

    prepared = await _prepare_subscription_inbound_data(_host(config["interface_name"]))

    assert prepared.wireguard_pre_shared_key == ""


@pytest.mark.asyncio
async def test_awg_subscription_boundary_preserves_supplied_psk(monkeypatch) -> None:
    supplied_psk, _ = generate_wireguard_keypair()
    config = _awg_config(supplied_psk)
    monkeypatch.setattr(core_manager, "get_inbound_by_tag", AsyncMock(return_value=_inbound(config)))

    prepared = await _prepare_subscription_inbound_data(_host(config["interface_name"]))

    assert prepared.wireguard_pre_shared_key == supplied_psk


@pytest.mark.asyncio
async def test_awg_subscription_boundary_still_rejects_invalid_psk_type(monkeypatch) -> None:
    config = _awg_config()
    inbound = _inbound(config)
    inbound["pre_shared_key"] = 123
    monkeypatch.setattr(core_manager, "get_inbound_by_tag", AsyncMock(return_value=inbound))

    with pytest.raises(ValidationError):
        await _prepare_subscription_inbound_data(_host(config["interface_name"]))


def test_awg_host_without_psk_has_authenticated_native_subscription(access_token: str) -> None:
    config = _awg_config()
    core_response = client.post(
        "/api/core",
        headers=auth_headers(access_token),
        json={
            "name": unique_name("awg_no_psk_core"),
            "config": config,
            "type": "gamerkhaan_amneziawg",
            "exclude_inbound_tags": [],
            "fallbacks_inbound_tags": [],
        },
    )
    assert core_response.status_code == status.HTTP_201_CREATED
    core = core_response.json()
    host_id = None
    group = None
    user = None
    try:
        host_response = client.post(
            "/api/host/",
            headers=auth_headers(access_token),
            json={
                "remark": "M2 AWG {USERNAME}",
                "address": ["198.51.100.10"],
                "port": 51820,
                "inbound_tag": config["interface_name"],
                "priority": 1,
            },
        )
        assert host_response.status_code == status.HTTP_201_CREATED
        host_id = host_response.json()["id"]

        group = create_group(
            access_token,
            name=unique_name("awg_no_psk_group"),
            inbound_tags=[config["interface_name"]],
        )
        user = create_user(
            access_token,
            group_ids=[group["id"]],
            payload={"username": unique_name("awg_no_psk_user")},
        )

        subscription = client.get(f"{user['subscription_url']}/amneziawg")
        assert subscription.status_code == status.HTTP_200_OK
        with zipfile.ZipFile(io.BytesIO(subscription.content)) as archive:
            assert archive.read("RENDERER") == b"amneziawg-native-v1\n"
            configs = [name for name in archive.namelist() if name.endswith(".conf")]
            assert len(configs) == 1
            profile = archive.read(configs[0]).decode()

        modal_response = client.get(
            f"/api/user/{user['id']}/subscription/amneziawg-configs",
            headers=auth_headers(access_token),
        )
        assert modal_response.status_code == status.HTTP_200_OK
        modal_configs = modal_response.json()["configs"]
        assert len(modal_configs) == 1
        assert modal_configs[0]["name"] == configs[0]
        assert modal_configs[0]["config"] == profile

        public_page = client.get(user["subscription_url"], headers={"Accept": "text/html"})
        assert public_page.status_code == status.HTTP_200_OK
        parser = _NativeConfigHTMLParser()
        parser.feed(public_page.text)
        assert parser.configs == [profile]
        assert "AmneziaWG Native Configs" in public_page.text
        assert 'showQr(nativeConfigParts(button).config)' in public_page.text
        assert 'new Blob([native.config]' in public_page.text
        assert 'tempInput.value = config' in public_page.text

        node = shutil.which("node")
        zbarimg = shutil.which("zbarimg")
        assert node is not None, "RC.3 public QR regression requires the isolated Node.js test prerequisite"
        assert zbarimg is not None, "RC.3 public QR regression requires the isolated zbarimg test prerequisite"
        with tempfile.TemporaryDirectory(prefix="rc3-public-qr-") as directory:
            root = Path(directory)
            profile_path = root / "profile.conf"
            qr_path = root / "profile.pbm"
            copy_path = root / "copy.conf"
            download_path = root / "download.conf"
            profile_path.write_text(profile, encoding="utf-8")
            helper = Path(__file__).with_name("rc3_subscription_actions.js").resolve()
            template = Path("app/templates/subscription/index.html").resolve()
            subprocess.run(
                [node, str(helper), str(template), str(profile_path), str(qr_path), str(copy_path), str(download_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            decoded = subprocess.run(
                [zbarimg, "--quiet", "--raw", str(qr_path)],
                check=True,
                capture_output=True,
            ).stdout
            decoded_profile = decoded[:-1] if decoded.endswith(b"\n") else decoded
            assert decoded_profile == profile.encode()
            assert copy_path.read_text(encoding="utf-8") == profile
            assert download_path.read_text(encoding="utf-8") == profile

        raw_response = client.get(f"{user['subscription_url']}/raw")
        assert raw_response.status_code == status.HTTP_200_OK
        native_configs = raw_response.json()["body"]["native_configs"]
        assert native_configs == [{"name": configs[0], "config": profile}]

        invalid = client.get("/sub/rc3-invalid-token", headers={"Accept": "text/html"})
        assert invalid.status_code == status.HTTP_404_NOT_FOUND
        disabled = client.put(
            f"/api/user/by-id/{user['id']}",
            headers=auth_headers(access_token),
            json={"status": "disabled"},
        )
        assert disabled.status_code == status.HTTP_200_OK
        disabled_page = client.get(user["subscription_url"], headers={"Accept": "text/html"})
        assert disabled_page.status_code == status.HTTP_200_OK
        disabled_parser = _NativeConfigHTMLParser()
        disabled_parser.feed(disabled_page.text)
        assert disabled_parser.configs == []

        expired = client.put(
            f"/api/user/by-id/{user['id']}",
            headers=auth_headers(access_token),
            json={"status": "active", "expire": "2000-01-01T00:00:00+00:00"},
        )
        assert expired.status_code == status.HTTP_200_OK
        expired_page = client.get(user["subscription_url"], headers={"Accept": "text/html"})
        assert expired_page.status_code == status.HTTP_200_OK
        expired_parser = _NativeConfigHTMLParser()
        expired_parser.feed(expired_page.text)
        assert expired_parser.configs == []

        assert "PresharedKey =" not in profile
        assert " = None" not in profile
        assert " = null" not in profile
        assert "Jc = 0" in profile
        assert "RandomTrailers = off" in profile
    finally:
        if user is not None:
            delete_user(access_token, user["username"])
        if group is not None:
            delete_group(access_token, group["id"])
        if host_id is not None:
            client.delete(f"/api/host/{host_id}", headers=auth_headers(access_token))
        delete_core(access_token, core["id"])
