from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = "919b71dfea60ff4c95e53b1c9232c5ee9921e20d"
CORE_KIT = "95677b42c599ebc2da02d2a8f0c2511695a07e14"
XRAY_KIT = "fc238d5306a31fb8d6b95d9c774bbf1ba66a25d2"
WG_KIT = "f68b93cfe006e865b2eb7a429339796e234b4703"


class ForkDistributionTests(unittest.TestCase):
    def test_release_workflow_uses_owned_image_and_pinned_bridge(self):
        workflow = (ROOT / ".github/workflows/build.yml").read_text()
        self.assertIn("IMAGE_NAME: ghcr.io/gamerkhaan/panel", workflow)
        self.assertIn("repository: GamerKhaan/node_bridge_py", workflow)
        self.assertIn(f"ref: {BRIDGE}", workflow)
        self.assertIn("path: m2-bridge-source", workflow)
        self.assertIn("m2bridge=./m2-bridge-source", workflow)
        self.assertNotIn("DOCKERHUB_", workflow)
        self.assertNotIn("pasarguard/${{ github.event.repository.name }}", workflow)
        self.assertNotIn("ghcr.io/pasarguard/", workflow)

    def test_dev_workflow_never_pushes_upstream_namespace(self):
        workflow = (ROOT / ".github/workflows/build-dev.yml").read_text()
        self.assertIn("IMAGE_NAME: ghcr.io/gamerkhaan/panel", workflow)
        self.assertIn("repository: GamerKhaan/node_bridge_py", workflow)
        self.assertIn(f"ref: {BRIDGE}", workflow)
        self.assertIn("m2bridge=./m2-bridge-source", workflow)
        self.assertNotIn("DOCKERHUB_", workflow)
        self.assertNotIn("ghcr.io/pasarguard/", workflow)

    def test_bridge_dependency_stays_exact(self):
        project = (ROOT / "pyproject.toml").read_text()
        self.assertIn('"pasarguard-node-bridge==0.9.1+awg31.m2"', project)
        self.assertIn('pasarguard-node-bridge = { path = "../m2-bridge-source" }', project)

    def test_default_compose_uses_owned_panel_image(self):
        compose = (ROOT / "docker-compose.yml").read_text()
        self.assertIn("image: ghcr.io/gamerkhaan/panel:latest", compose)
        self.assertNotIn("image: pasarguard/panel", compose)

    def test_dashboard_pins_owned_config_kits(self):
        package = (ROOT / "dashboard/package.json").read_text()
        self.assertIn(
            f'"@pasarguard/core-kit": "https://codeload.github.com/GamerKhaan/core-kit/tar.gz/{CORE_KIT}"',
            package,
        )
        self.assertIn(
            f'"@pasarguard/xray-config-kit": "https://codeload.github.com/GamerKhaan/xray-config-kit/tar.gz/{XRAY_KIT}"',
            package,
        )
        self.assertIn(
            f'"@pasarguard/wireguard-config-kit": "https://codeload.github.com/GamerKhaan/wireguard-config-kit/tar.gz/{WG_KIT}"',
            package,
        )

    def test_dashboard_runtime_has_no_pasarguard_github_control_plane(self):
        forbidden = (
            "https://github.com/PasarGuard",
            "https://github.com/pasarguard",
            "https://api.github.com/repos/PasarGuard",
            "https://api.github.com/repos/pasarguard",
        )
        for path in (ROOT / "dashboard/src").rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(errors="ignore")
            for needle in forbidden:
                self.assertNotIn(needle, text, f"{path.relative_to(ROOT)} still references upstream: {needle}")
        service = (ROOT / "install_service.sh").read_text()
        self.assertNotIn("github.com/pasarguard/panel", service.lower())
        self.assertIn("github.com/GamerKhaan/panel", service)


if __name__ == "__main__":
    unittest.main()
