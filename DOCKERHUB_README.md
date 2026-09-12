<p align="center">
  <img src="https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/logo.png" width="210" alt="Nowlert logo">
</p>

<h1 align="center">Nowlert CE</h1>

<p align="center">
  <strong>Infrastructure reports. Nowlert delivers.</strong><br>
  Community Edition · free & open source · self-hosted
</p>

Nowlert CE receives infrastructure signals over **SMTP**, **HTTP**, and
**Redfish**, normalizes vendor-specific events, applies deterministic routing,
and delivers clear operational notifications to Discord, Microsoft Teams,
Slack, generic webhooks, MQTT, and ntfy.

The current stable release is **v3.1.4**. The versioned Docker Hub image is:

```text
theriark/nowlert-ce:3.1.4
```

## v3.1.4 highlights

- Stage is the final runtime acceptance gate for CE releases.
- Release chain is Development → Stage → main → Release.
- One immutable Development image is promoted to Stage without rebuild.
- `main` advances only to the exact Stage-approved source commit.
- Stable GHCR/Docker Hub aliases are copied from the approved digest without
  rebuild.
- Database schema 9 and `platform_database_v1` remain unchanged.

v3.1.4 is a release-engineering maintenance patch. Event ingestion, parsers,
routing, destinations, authentication, backups, and WebUI behavior are unchanged
from v3.1.3, and no database migration is required.

## Preview

v3.1.4 keeps the approved v3.1.0 visual baseline.

![Nowlert Dashboard](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-dashboard.png)

![Nowlert Routing Flow](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-routing-flow.png)

![Nowlert Delivery History](https://raw.githubusercontent.com/Theriark/nowlert-ce/main/docs/images/v3.1.0-delivery-history.png)

## Quick start

```bash
git clone https://github.com/Theriark/nowlert-ce.git
cd nowlert-ce

cp .env.example .env
cp config/config.example.yaml config/config.yaml
mkdir -p logs/emails secrets state external-backups
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups

docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml pull
docker compose -f compose.production.yaml up -d
docker logs -f nowlert-ce
```

Set `NOWLERT_UID` and `NOWLERT_GID` in `.env` to the numeric identity that owns
the mounted directories.

On first start, the container prints a short-lived, single-use setup token.
Open the WebUI and choose the first administrator username/password. No default
password exists.

## Ports

- `8025/tcp` — SMTP input
- `8080/tcp` — WebUI + HTTP/Redfish service inside the container
- supplied Compose maps host port `18080` to container port `8080` by default

## Persistent mounts

| Container path | Purpose |
|---|---|
| `/nowlert/config` | bootstrap `config.yaml` and optional TLS material |
| `/nowlert/state` | SQLite state, owner-scoped secrets, private state backups |
| `/nowlert/logs` | application logs and optional retained event material |
| `/run/secrets` | externally managed read-only secrets |
| `/nowlert/external-backups` | bounded external backup target |

Back up `config`, `state`, and external `secrets` as one matched set before an
upgrade or rollback.

## Configuration model

`config.yaml` is intentionally small and controls process/bootstrap concerns:
listeners, transport security, state location, and WebUI publication.

Destinations, routes, Event API tokens, preferences, backup schedules,
integration behavior, aliases, users, notices, audit events, and delivery
history are database-authoritative in private platform state.

Do not add the legacy WebUI-managed `outputs`, `routing`, `api.tokens`,
`notifications`, `presentation`, `home_assistant`, `redfish`,
`platform.backups`, or `webui.language` sections to a fresh v3.1.4
configuration.

## Built-in integrations

Xen Orchestra, Zabbix, Grafana, Portainer, Proxmox, QNAP, Synology, TrueNAS,
UniFi Network, UniFi Protect, UniFi Drive, Supermicro, HPE iLO, Dell iDRAC, and
Home Assistant.

Normalized inputs are SMTP, HTTP, and Redfish. The built-in catalogue defines
which input(s) and route criteria apply to each integration.

## Routing model

Nowlert evaluates enabled dedicated integration routes before wildcard fallback
routes. Fallback routes run only when no dedicated route matches, and duplicate
delivery to the same destination is suppressed.

The v3.1.4 route editor behavior is unchanged from v3.1.3: host/event patterns
plus included severities and statuses are supported, and unselected
severity/status values are implicitly excluded.

## Security

The production Compose definition uses:

- configurable non-root UID/GID;
- read-only root filesystem;
- dropped Linux capabilities;
- `no-new-privileges`;
- private persistent state; and
- bounded writable mounts/temp storage.

Use direct HTTP only on a trusted private network. For public/untrusted access,
terminate TLS at a trusted reverse proxy, set `webui.public_url`, enable WebUI
HTTPS enforcement, and enable secure cookies.

SMTP STARTTLS and SMTP AUTH are optional and disabled by default.

## Upgrade and rollback

Before upgrading:

1. back up `config`, `state`, and external `secrets` as one matched set;
2. record the currently running image/digest;
3. deploy the versioned v3.1.4 image;
4. verify `/api/health`, login, routes, destinations, history, and backups; and
5. keep the matched backup until acceptance passes.

v3.1.4 keeps schema 9, so no v3.1.3 database migration is expected.

## Immutable release provenance

Theriark's CE release workflow builds the candidate on `development`, promotes
the exact immutable digest to Stage, advances `main` only to the Stage-approved
source commit, creates the release tag on that same source, then copies the
approved digest to the versioned and `latest` GHCR/Docker Hub aliases.

Stage is the final live runtime acceptance gate. The stable image is **not
rebuilt from the release tag**.

## Documentation

Repository: https://github.com/Theriark/nowlert-ce

Current documentation includes:

- deployment and immutable release flow;
- WebUI guide;
- integration/input catalogue;
- routing/delivery model;
- platform API/state model;
- data portability and private backups;
- integration-specific setup guides;
- practical end-to-end use-case guides; and
- release notes/QA checklists.

MIT License · Powered by Theriark
