import io
import zipfile

from app.models.subscription import SubscriptionInboundData

from .base import BaseSubscription

_AWG_KEYS = {
    "jc": "Jc",
    "jmin": "Jmin",
    "jmax": "Jmax",
    "s1": "S1",
    "s2": "S2",
    "s3": "S3",
    "s4": "S4",
    "h1": "H1",
    "h2": "H2",
    "h3": "H3",
    "h4": "H4",
    "header_protection_key": "HeaderProtectionKey",
    "content_padding_addition": "ContentPaddingAddition",
    "random_trailers": "RandomTrailers",
    "disable_cookies": "DisableCookies",
    "rekey_after_time": "RekeyAfterTime",
    "rekey_timeout": "RekeyTimeout",
    "reject_after_time": "RejectAfterTime",
    "keepalive_timeout": "KeepaliveTimeout",
    "max_handshake_attempts": "MaxHandshakeAttempts",
}


def _render_value(value: object) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value)


class AmneziaWGConfiguration(BaseSubscription):
    renderer_identity = "amneziawg-native-v1"

    def __init__(self):
        self.proxy_remarks = []
        self.configs: list[tuple[str, str]] = []

    def add(self, remark: str, address: str, inbound: SubscriptionInboundData, settings: dict):
        if inbound.backend_type != "gamerkhaan_amneziawg":
            return
        components = self._build_wireguard_components(remark, address, inbound, settings)
        if not components:
            return
        payload = components["payload"]
        interface = [
            "[Interface]",
            f"PrivateKey = {components['private_key']}",
            f"Address = {', '.join(components['peer_ips'])}",
        ]
        if inbound.wireguard_mtu is not None:
            interface.append(f"MTU = {inbound.wireguard_mtu}")
        if inbound.wireguard_dns:
            interface.append(f"DNS = {', '.join(inbound.wireguard_dns)}")
        for name, value in inbound.amneziawg_parameters.items():
            # Presence, not truthiness, controls rendering: 0 and false are protocol data.
            interface.append(f"{_AWG_KEYS[name]} = {_render_value(value)}")

        peer = [
            "[Peer]",
            f"PublicKey = {payload['publickey']}",
            f"AllowedIPs = {payload['allowedips'].replace(',', ', ')}",
            f"Endpoint = {address}:{inbound.port}",
        ]
        if "presharedkey" in payload:
            peer.append(f"PresharedKey = {payload['presharedkey']}")
        if "keepalive" in payload:
            peer.append(f"PersistentKeepalive = {payload['keepalive']}")
        self.configs.append((components["remark"], "\n".join((*interface, "", *peer, ""))))

    def render(self) -> bytes:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for remark, config in self.configs:
                filename = remark.replace(" ", "_").replace("/", "_") + ".conf"
                archive.writestr(filename, config)
            archive.writestr("RENDERER", self.renderer_identity + "\n")
        return output.getvalue()
