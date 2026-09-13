# Nowlert CE technical use-case guides

These guides show complete, practical event flows using the current Nowlert CE
platform model. They are written for operators evaluating or deploying Nowlert
rather than for historical release compatibility.

## Guides

- [Route Xen Orchestra alerts through Nowlert CE to Discord](xen-orchestra-to-discord.md)
- [Send Xen Orchestra alerts to Microsoft Teams](xen-orchestra-to-teams.md)
- [Centralise homelab SMTP alerts without mailbox rules](centralise-homelab-smtp-alerts.md)
- [Route Dell iDRAC Redfish events through Nowlert CE](dell-idrac-redfish-routing.md)
- [Send Zabbix webhooks to Discord](zabbix-webhook-to-discord.md)

## Current platform assumptions

These guides are part of the v3.1.6 documentation candidate and use the current
v3.1.x platform model:

- integrations are built into the image;
- inputs are normalised as SMTP, HTTP, or Redfish;
- destinations and routes are managed through the WebUI and stored in the
  platform database;
- destination credentials remain write-only;
- dedicated integration routes are evaluated before fallback routes; and
- `config.yaml` is used for listener/bootstrap/security settings, not for
  recreating legacy WebUI-managed routing or destination YAML.

For authoritative platform behaviour, also see:

- [Integrations and inputs](../integrations-and-inputs.md)
- [Integration setup index](../integrations/README.md)
- [Platform routing](../platform-routing.md)
- [SMTP security](../smtp-security.md)
- [Current configuration model](../current-configuration-model.md)
