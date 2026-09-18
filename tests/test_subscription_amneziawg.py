import io
import zipfile

from app.models.subscription import SubscriptionInboundData, TCPTransportConfig, TLSConfig
from app.subscription.amneziawg import AmneziaWGConfiguration
from app.utils.crypto import generate_wireguard_keypair


def test_native_awg_renderer_preserves_zero_and_false() -> None:
    client_private, _ = generate_wireguard_keypair()
    _, server_public = generate_wireguard_keypair()
    inbound = SubscriptionInboundData(
        remark="M2 AWG",
        inbound_tag="awgm2",
        protocol="wireguard",
        address=["203.0.113.10"],
        port=[51820],
        network="udp",
        tls_config=TLSConfig(),
        transport_config=TCPTransportConfig(),
        wireguard_public_key=server_public,
        wireguard_local_address=["10.70.0.1/24"],
        wireguard_allowed_ips=["0.0.0.0/0", "::/0"],
        wireguard_keepalive=0,
        backend_type="gamerkhaan_amneziawg",
        renderer="amneziawg-native-v1",
        amneziawg_schema_version=1,
        amneziawg_implementation="GamerKhaan/pasarguard-awg31-patch",
        amneziawg_parameters={"jc": 0, "random_trailers": False, "disable_cookies": False},
    )
    renderer = AmneziaWGConfiguration()
    renderer.add("M2 AWG", "203.0.113.10", inbound, {"private_key": client_private, "peer_ips": ["10.70.0.2/32"]})
    with zipfile.ZipFile(io.BytesIO(renderer.render())) as archive:
        text = archive.read("M2_AWG.conf").decode()
        assert archive.read("RENDERER") == b"amneziawg-native-v1\n"
    assert "Jc = 0" in text
    assert "RandomTrailers = off" in text
    assert "DisableCookies = off" in text
    assert "Address = 10.70.0.2/32" in text


def test_awg_renderer_excludes_ordinary_wireguard_host() -> None:
    renderer = AmneziaWGConfiguration()
    inbound = SubscriptionInboundData(
        remark="ordinary WG", inbound_tag="wg0", protocol="wireguard", address=["203.0.113.10"],
        port=[51820], network="udp", tls_config=TLSConfig(), transport_config=TCPTransportConfig(),
    )
    renderer.add("ordinary WG", "203.0.113.10", inbound, {})
    with zipfile.ZipFile(io.BytesIO(renderer.render())) as archive:
        assert archive.namelist() == ["RENDERER"]
