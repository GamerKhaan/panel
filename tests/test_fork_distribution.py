import unittest
from pathlib import Path

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

    def test_database_migration_workflow_materializes_pinned_bridge(self):
        workflow = (ROOT / ".github/workflows/test-database-migrations.yml").read_text()
        self.assertGreaterEqual(workflow.count("GamerKhaan/node_bridge_py.git"), 5)
        self.assertGreaterEqual(workflow.count(BRIDGE), 5)
        self.assertGreaterEqual(workflow.count("../m2-bridge-source"), 5)

    def test_awg_core_type_migration_covers_all_supported_database_families(self):
        migration = (ROOT / "app/db/migrations/versions/pgawg0001_add_coretype.py").read_text()
        self.assertIn('dialect == "postgresql"', migration)
        self.assertIn('dialect in {"mysql", "mariadb"}', migration)
        self.assertIn('dialect == "sqlite"', migration)
        self.assertIn("batch_alter_table", migration)

    def test_public_website_support_and_ads_links_are_owned(self):
        project = (ROOT / "dashboard/src/constants/Project.ts").read_text()
        donation_popup = (ROOT / "dashboard/src/components/common/donation-popup.tsx").read_text()
        goal_progress = (ROOT / "dashboard/src/components/layout/goal-progress.tsx").read_text()

        self.assertIn("export const DONATION_URL = 'https://amooserver.com'", project)
        self.assertIn("export const DISCUSSION_GROUP = 'https://amooserver.com'", project)
        self.assertIn("export const DOCUMENTATION = 'https://amooserver.com'", project)
        self.assertNotIn("donate.pasarguard.org", donation_popup)
        self.assertNotIn("t.me/Pasar_Guard", goal_progress)
        self.assertNotIn("donate.pasarguard.org", goal_progress)

    def test_node_release_badge_is_not_suppressed_for_wireguard_backends(self):
        for relative_path in (
            "dashboard/src/features/nodes/components/node.tsx",
            "dashboard/src/features/nodes/components/use-node-list-columns.tsx",
        ):
            source = (ROOT / relative_path).read_text()
            self.assertNotIn("hasNodeVersionUpdate = !isWireGuardCore", source)
            self.assertNotIn("{!isWireGuardCore && latestNodeVersion", source)

    def test_dashboard_layout_keeps_upstream_advertising_structure(self):
        layout = (ROOT / "dashboard/src/pages/_dashboard.tsx").read_text()
        self.assertIn("import DonationPopup from '@/components/common/donation-popup'", layout)
        self.assertIn("<DonationPopup />", layout)
        self.assertIn("<TopbarAd />", layout)

    def test_dashboard_build_retires_legacy_service_worker_with_minimal_upstream_diff(self):
        vite = (ROOT / "dashboard/vite.config.mts").read_text()
        self.assertIn("emptyOutDir: false", vite)
        self.assertIn("selfDestroying: true", vite)
        self.assertIn("injectRegister: false", vite)
        self.assertNotIn("cleanupOutdatedCaches: false", vite)
        self.assertNotIn("skipWaiting: false", vite)
        self.assertNotIn("clientsClaim: false", vite)

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
