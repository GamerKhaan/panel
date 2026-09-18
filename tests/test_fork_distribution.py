from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = "919b71dfea60ff4c95e53b1c9232c5ee9921e20d"


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


if __name__ == "__main__":
    unittest.main()
