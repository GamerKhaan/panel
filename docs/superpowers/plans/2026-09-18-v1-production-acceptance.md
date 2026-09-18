# GamerKhaan Distribution v1 Production Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Execute source hardening plus complete destructive production acceptance QA for the GamerKhaan v1 fork-integrated Panel/Node distribution.

**Architecture:** Code/update/install remain on GamerKhaan GitHub/GHCR; website/docs/support/ads route to amooserver.com. Validate stock adoption before destructive reset, then fresh-install and exercise three cores, user/subscription/accounting lifecycle, reboot, update and rollback.

**Tech Stack:** Bash, Docker Compose, FastAPI/Python, React/Bun, Go, TimescaleDB/PostgreSQL, Xray, WireGuard, AmneziaWG, GitHub Actions/GHCR, systemd.

**Spec:** docs/superpowers/specs/2026-09-18-v1-production-acceptance-design.md

## Global Constraints

- Core 185.254.199.207; Node 185.254.199.206; stable baseline v1.0.0.
- Website/support/ads placeholder: https://amooserver.com.
- Never log secrets.
- No destructive wipe before backup/fingerprint and successful adoption QA.
- Preserve unrelated external services unless ownership is proven.
- Evidence before claims.

### Task 1: External-link/control-plane hardening
- [ ] Add failing guards for Project URLs, donation/support/docs, ads destination and zero operational upstream fetch/update/build paths.
- [ ] Verify RED; route website/docs/support/donation/ads to amooserver.com, source/update/install to GamerKhaan.
- [ ] Run frontend/distribution tests/build; commit/push; require CI green.

### Task 2: Production baseline and recovery package
- [ ] Capture Core/Node network, firewall, listeners, containers, services, disk, app images, compose hashes, DB schema/counts and WireGuard state.
- [ ] Create root-private backups/fingerprints and verify recovery readability/commands.

### Task 3: Real stock-adoption install QA
- [ ] Run v1 installer on existing Node first; verify invariance/coexistence.
- [ ] Run v1 installer on existing Panel; verify DB/config/template invariance and existing Xray/WireGuard records.
- [ ] Any failure: root-cause, regression test, minimal fix, CI, retry.

### Task 4: Destructive clean reset
- [ ] Remove owned Panel/Node containers, systemd helpers, compose/config/data and owned Docker resources.
- [ ] Verify no owned application artifacts remain and unrelated services/MCP are healthy.

### Task 5: Fresh Node and Panel install
- [ ] Fresh Node v1.0.0 + node-serviced.
- [ ] Fresh Panel v1.0.0.
- [ ] Create owner/admin through supported flow and connect Node to Panel.
- [ ] Verify health/CLI/log/status.

### Task 6: Core/user/subscription traffic harness
- [ ] Xray: create core/group/host/user, subscription, disposable client traffic, online/accounting, lock/unlock, limit/reset, expiry, revoke/regenerate.
- [ ] Repeat equivalent lifecycle for WireGuard.
- [ ] Repeat equivalent lifecycle for AmneziaWG with compatible client; if unavailable, record exact blocker and do not fabricate PASS.

### Task 7: Panel/CLI smoke matrix
- [ ] Hosts/groups/templates CRUD smoke, backup validity, node/core logs, resource health.
- [ ] CLI help/status/logs/restart/service-status/update and GUI Node update dispatch verification.

### Task 8: Reboot resilience
- [ ] Record pre-reboot fingerprints; reboot Node then Core; wait conditionally for management/services.
- [ ] Rerun node connectivity, active core traffic, subscription, accounting and CLI status.

### Task 9: Update/rollback acceptance
- [ ] Publish temporary higher QA release from same code plus distribution-version bump; require CI/GHCR success.
- [ ] Verify GUI detection and Panel/Node CLI + GUI updates use GamerKhaan only.
- [ ] Compare state/traffic; roll back to v1.0.0; restore v1.0.0 as stable latest.

### Task 10: Final verification/checkpoint
- [ ] Final upstream-link scan and amooserver configuration check.
- [ ] Release identities/digests, runtime health, tmux/MCP persistence.
- [ ] Update Mem; concise Persian PASS/FAIL/limitations report.
