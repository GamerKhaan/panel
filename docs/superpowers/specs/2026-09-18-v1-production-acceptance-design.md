# GamerKhaan Distribution v1 Production Acceptance Design

## Goal

Prove that the public GamerKhaan fork-integrated distribution can migrate an existing official PasarGuard installation, survive a destructive clean reinstall on both real VPSes, operate Xray/WireGuard/AmneziaWG end-to-end with user/subscription/accounting lifecycle controls, survive reboot, and update/rollback only through GamerKhaan-controlled release paths.

## Control-plane ownership

- Source/build/install/update: GamerKhaan GitHub repositories and ghcr.io/gamerkhaan/*.
- Website/documentation/support/donation/ad destinations: https://amooserver.com until dedicated pages exist.
- GitHub source links: GamerKhaan repositories.
- Upstream PasarGuard references are permitted only for license/attribution/provenance and migration detection of official stock installations.
- Runtime, update, GUI-update, ads, docs/support buttons, and install/download paths must never fetch/control from PasarGuard upstream.

## Production hosts

- Core/Panel: 185.254.199.207.
- Node: 185.254.199.206.
- Warsaw is observability/control relay only.
- Build host 195.160.222.195 is test/client/release automation.

## Destructive execution gates

1. Capture read-only baseline and create root-private recovery backups/fingerprints.
2. Validate official-stock -> GamerKhaan v1 adoption on Node and Panel.
3. Verify service/data invariance after adoption.
4. Only then remove owned Panel/Node application artifacts for a true fresh install.
5. Preserve unrelated external services unless ownership is proven.
6. Fresh-install Node first, then Panel, then reconnect Node.
7. Run full functional matrix, reboot both VPSes, rerun critical tests.
8. Create a temporary higher QA release, test GUI/CLI update and rollback, then restore v1.0.0 as stable latest.

## Functional acceptance matrix

- Xray, WireGuard and AmneziaWG: core start/sync, real client traffic where a compatible client is available, online state and accounting.
- User lifecycle: create, subscription/config, connect, disable/enable, traffic-limit change, usage reset, expiry extension, revoke/regenerate.
- Panel smoke: nodes, cores, logs, hosts, groups, templates, backup, health/resources.
- CLI smoke: help/status/logs/restart/service-status/update/version-safe commands.
- Reboot: MCP, Panel DB/PgBouncer, Node/node-serviced, node reconnect, active traffic and subscription.
- Update/rollback: temporary QA release above v1.0.0, compare state before/after, rollback to v1.0.0, verify traffic/state again.

## Evidence and secrets

- Never expose credentials, API keys, private keys, subscription tokens, raw user URLs, cookies or private URLs in chat/tmux/Mem/Git.
- Secret-bearing evidence, if required, stays in root-private files on the target host.
- Final report uses hashes/counts/status and explicit PASS/FAIL/limitation evidence.

## Completion criteria

- All relevant CI green and final worktrees clean.
- Migration and fresh install verified on real Core/Node.
- Xray/WireGuard/AmneziaWG matrix completed with explicit evidence.
- Reboot and update/rollback completed.
- Final upstream operational-link scan is zero except explicit stock-migration detection.
- Production health and unresolved risks are recorded.
