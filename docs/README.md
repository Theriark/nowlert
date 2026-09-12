# Nowlert CE documentation

This directory contains current operator/developer guidance plus historical
release records.

## Current documentation

Use these guides for the current v3.1.4 release line:

| Guide | Purpose |
|---|---|
| [Current configuration model](current-configuration-model.md) | What belongs in `config.yaml` versus database-authoritative platform state |
| [Deployment](deployment.md) | Docker/Compose operation, immutable promotion flow, upgrade and rollback |
| [WebUI](webui.md) | Current pages, permissions, route editing, history, users and backups |
| [Integrations and inputs](integrations-and-inputs.md) | Built-in integration catalogue and SMTP/HTTP/Redfish input model |
| [Integration setup index](integrations/README.md) | Stable index for product-specific setup notes |
| [Technical use-case guides](guides/README.md) | Practical end-to-end SMTP/HTTP/Redfish flows to real destinations |
| [Platform routing](platform-routing.md) | Tokens, destinations, routes, fallback behavior, delivery and audit rules |
| [Platform outputs](platform-outputs.md) | Destination adapters and safe output contracts |
| [Platform API](platform-api.md) | `/api/v2` authentication, endpoints, CSRF and event ingestion |
| [Platform state](platform-state.md) | SQLite schema, local accounts, secrets, backup layout and recovery |
| [Data portability](data-portability.md) | Credential-free export/import, private backups, restore and deletion |
| [SMTP security](smtp-security.md) | STARTTLS, SMTP AUTH and trusted-network boundaries |
| [Presentation contract](presentation-contract.md) | Normalized notification presentation rules |
| [Roadmap](roadmap.md) | Shipped milestones and current maintenance priorities |

## Integration guides

Integration-specific setup is indexed under [`integrations/`](integrations/).
The existing product-specific guide files remain at their established top-level
`docs/` paths so historical and inbound links continue to work.

The built-in catalogue is authoritative for which normalized inputs are
available to each integration. A guide may contain product-specific endpoint or
payload examples, but routing always uses the shared integration + input model.

## Practical use-case guides

The [`guides/`](guides/) collection contains current end-to-end operator flows,
including Xen Orchestra to Discord/Teams, direct homelab SMTP ingestion, Dell
iDRAC/Redfish routing, and Zabbix Event API delivery to Discord.

## Release documentation

Current release material:

- [v3.1.4 release notes](releases/v3.1.4.md)
- [v3.1.4 QA checklist](v3.1.4-qa-checklist.md)

Historical notes under `releases/` and historical acceptance/QA checklists are
version snapshots. They are intentionally preserved even when a newer release
changes current documentation.

## Screenshots

Current public screenshots live under `images/`. v3.1.4 does not introduce a
visual redesign, so it deliberately reuses the approved v3.1.0 visual baseline
rather than duplicating identical PNGs under new filenames.

The README/current WebUI documentation uses:

- `v3.1.0-dashboard.png`
- `v3.1.0-routing-flow.png`
- `v3.1.0-destinations.png`
- `v3.1.0-delivery-history.png`
- `v3.1.0-discord-xen-orchestra.png`
- `v3.1.0-teams-xen-orchestra.png`

Additional packaged screenshots may be referenced by individual practical
guides when they accurately demonstrate an existing integration/destination
presentation.

Refresh screenshots only when the rendered UI or notification presentation
materially changes. Never publish captures that show passwords, destination
URLs, API tokens, setup tokens, private hostnames, email addresses, or other
secret/personal material.

## Documentation validation

Run:

```bash
python tools/validate_current_documentation.py
python -m pytest -q tests/test_comprehensive_readme.py \
  tests/test_v252_documentation_refresh.py \
  tests/test_v310_release_docs.py \
  tests/test_v311_release_docs.py \
  tests/test_v314_release_docs.py
```

Documentation, release metadata, runtime version, Compose defaults, and the
approved visual baseline should describe the same release before a tag is
created.
