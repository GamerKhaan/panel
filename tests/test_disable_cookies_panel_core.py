import json

from app.core.amneziawg import AWG_IMPLEMENTATION, AmneziaWGConfig
from app.utils.crypto import generate_wireguard_keypair


def test_panel_core_accepts_disable_cookies_true_and_preserves_node_payload() -> None:
    private_key, _ = generate_wireguard_keypair()
    payload = {
        "schema_version": 1,
        "implementation": AWG_IMPLEMENTATION,
        "interface_name": "awgdc",
        "private_key": private_key,
        "listen_port": 51820,
        "address": ["10.71.0.1/24"],
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
            "disable_cookies": True,
        },
    }

    config = AmneziaWGConfig(payload)
    assert config["awg"]["disable_cookies"] is True

    node_payload = json.loads(config.to_str())
    assert node_payload["awg"]["disable_cookies"] is True


if __name__ == "__main__":
    test_panel_core_accepts_disable_cookies_true_and_preserves_node_payload()
