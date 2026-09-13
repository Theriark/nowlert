#!/usr/bin/env python3
"""Validate local Markdown links and public-documentation drift."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "README.md",
    ROOT / "DOCKERHUB_README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "current-configuration-model.md",
    ROOT / "docs" / "data-portability.md",
    ROOT / "docs" / "database-authoritative-resources.md",
    ROOT / "docs" / "deployment.md",
    ROOT / "docs" / "integrations-and-inputs.md",
    ROOT / "docs" / "integrations" / "README.md",
    ROOT / "docs" / "guides" / "README.md",
    ROOT / "docs" / "guides" / "xen-orchestra-to-discord.md",
    ROOT / "docs" / "guides" / "xen-orchestra-to-teams.md",
    ROOT / "docs" / "guides" / "centralise-homelab-smtp-alerts.md",
    ROOT / "docs" / "guides" / "dell-idrac-redfish-routing.md",
    ROOT / "docs" / "guides" / "zabbix-webhook-to-discord.md",
    ROOT / "docs" / "platform-api.md",
    ROOT / "docs" / "platform-outputs.md",
    ROOT / "docs" / "platform-routing.md",
    ROOT / "docs" / "platform-state.md",
    ROOT / "docs" / "presentation-contract.md",
    ROOT / "docs" / "releases" / "v3.1.5.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "docs" / "smtp-security.md",
    ROOT / "docs" / "v3.1.5-qa-checklist.md",
    ROOT / "docs" / "webui.md",
)

# v3.1.5 intentionally does not change these runtime contracts. They continue
# to document the v3.1.2 behavior baseline while the current release identity
# and release-engineering documentation advance to v3.1.5.
UNCHANGED_RUNTIME_GUIDES = (
    ROOT / "docs" / "current-configuration-model.md",
    ROOT / "docs" / "data-portability.md",
    ROOT / "docs" / "database-authoritative-resources.md",
    ROOT / "docs" / "integrations-and-inputs.md",
    ROOT / "docs" / "platform-api.md",
    ROOT / "docs" / "platform-outputs.md",
    ROOT / "docs" / "platform-routing.md",
    ROOT / "docs" / "platform-state.md",
    ROOT / "docs" / "presentation-contract.md",
    ROOT / "docs" / "smtp-security.md",
    ROOT / "docs" / "webui.md",
)

CURRENT_SCREENSHOTS = (
    "v3.1.0-dashboard.png",
    "v3.1.0-routing-flow.png",
    "v3.1.0-destinations.png",
    "v3.1.0-delivery-history.png",
    "v3.1.0-discord-xen-orchestra.png",
    "v3.1.0-teams-xen-orchestra.png",
)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
missing: list[str] = []

for document in FILES:
    if not document.is_file():
        missing.append(str(document.relative_to(ROOT)))
        continue

    text = document.read_text(encoding="utf-8")
    for raw in LINK_RE.findall(text):
        target = raw.split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (document.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            missing.append(f"{document.relative_to(ROOT)} -> {raw}")
            continue
        if not resolved.exists():
            missing.append(f"{document.relative_to(ROOT)} -> {raw}")

for filename in CURRENT_SCREENSHOTS:
    path = ROOT / "docs" / "images" / filename
    if not path.is_file() or path.stat().st_size == 0:
        missing.append(str(path.relative_to(ROOT)))

if missing:
    print("ERROR: missing current documentation files/links:")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(1)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
api = (ROOT / "docs" / "platform-api.md").read_text(encoding="utf-8")
deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
release = (ROOT / "docs" / "releases" / "v3.1.5.md").read_text(encoding="utf-8")
checklist = (ROOT / "docs" / "v3.1.5-qa-checklist.md").read_text(encoding="utf-8")
version = (ROOT / "src" / "version.py").read_text(encoding="utf-8")
environment = (ROOT / ".env.example").read_text(encoding="utf-8")
compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
guide_index = (ROOT / "docs" / "guides" / "README.md").read_text(encoding="utf-8")
integration_index = (ROOT / "docs" / "integrations" / "README.md").read_text(
    encoding="utf-8"
)

required_pairs = (
    (readme, "stable-v3.1.5-F4C542"),
    (readme, "**v3.1.5**"),
    (dockerhub.casefold(), "current stable release is **v3.1.5**"),
    (version, 'VERSION = "3.1.5"'),
    (environment, "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.5"),
    (compose, "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.5}"),
    (release, "# Nowlert CE v3.1.5 release notes"),
    (checklist, "# Nowlert CE v3.1.5 QA checklist"),
    (deployment, 'version="v3.1.5"'),
    (deployment, 'tag="v3.1.5"'),
    (deployment, "ghcr.io/theriark/nowlert-ce:3.1.5"),
    (deployment, "docker.io/theriark/nowlert-ce:3.1.5"),
    (deployment, "Development -> Stage -> main -> Release"),
    (deployment, "docker-release.yml"),
    (api, "DELETE | `/api/v2/users/{id}`"),
    (api, "DELETE | `/api/v2/backups/{id}`"),
    (docs_index, "current v3.1.5 release line"),
    (docs_index, "does not introduce a\nvisual redesign"),
    (guide_index, "xen-orchestra-to-discord.md"),
    (guide_index, "xen-orchestra-to-teams.md"),
    (guide_index, "centralise-homelab-smtp-alerts.md"),
    (guide_index, "dell-idrac-redfish-routing.md"),
    (guide_index, "zabbix-webhook-to-discord.md"),
    (integration_index, "../redfish.md"),
    (integration_index, "../guides/README.md"),
)
for document, required in required_pairs:
    if required not in document:
        raise SystemExit(f"ERROR: current documentation contract missing: {required}")

for document in UNCHANGED_RUNTIME_GUIDES:
    text = document.read_text(encoding="utf-8")
    relative = document.relative_to(ROOT)
    if "Nowlert v3.1.2" not in text:
        raise SystemExit(
            f"ERROR: unchanged runtime guide lost v3.1.2 behavior baseline: {relative}"
        )
    if "Nowlert v3.1.1" in text:
        raise SystemExit(
            f"ERROR: stale runtime guide identity remains in {relative}: Nowlert v3.1.1"
        )

# Historical v3.1.4 release records are preserved, but mutable current-release
# surfaces must not continue to advertise the old release identity.
for stale in (
    "stable-v3.1.4-F4C542",
    "| **Current Stable Release** | **v3.1.4** |",
    'version="v3.1.4"',
    'tag="v3.1.4"',
    "ghcr.io/theriark/nowlert-ce:3.1.4",
    "docker.io/theriark/nowlert-ce:3.1.4",
):
    if stale in readme or stale in dockerhub or stale in deployment:
        raise SystemExit(f"ERROR: stale current-release reference remains: {stale}")

for legacy in ("\noutputs:\n", "\nrouting:\n"):
    if legacy in dockerhub:
        raise SystemExit("ERROR: legacy WebUI-managed YAML example remains in Docker Hub text")

for path in (ROOT / "docs" / "guides").glob("*.md"):
    if path.name == "README.md":
        continue
    text = path.read_text(encoding="utf-8")
    for legacy in ("\noutputs:\n", "\nrouting:\n", "\napi:\n  tokens:\n"):
        if legacy in text:
            raise SystemExit(
                f"ERROR: legacy WebUI-managed YAML example remains in {path.relative_to(ROOT)}"
            )

for stale_claim in (
    "Nowlert v2.5.2 packages",
    "mounted `config.yaml` is the single configuration authority",
):
    if stale_claim in webui:
        raise SystemExit(f"ERROR: stale WebUI documentation remains: {stale_claim}")

if "The mounted file is authoritative" in api:
    raise SystemExit("ERROR: platform API still claims legacy YAML authority")

print("documentation_links=passed")
print("documentation_release_identity=passed")
print("documentation_screenshots=passed")
print("documentation_guides=passed")
print("documentation_drift=passed")
