"""Nowlert v2.5.3 compatibility and local-icon regressions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from formatters.presentation import PresentationMixin
from integrations.catalog import infer_input_type, integration, route_options
from outputs.discord import DiscordOutput
from parsers.unifi_protect import Parser as ProtectParser


ROOT = Path(__file__).resolve().parents[1]
PROTECT_FIXTURE = ROOT / "tests" / "fixtures" / "unifi" / "protect" / "motion.json"


def protect_payload() -> dict:
    return json.loads(PROTECT_FIXTURE.read_text(encoding="utf-8"))


def test_synology_catalogue_exposes_smtp_and_http():
    item = integration("synology")
    assert item is not None
    assert [value["id"] for value in item["inputs"]] == ["smtp", "http"]
    choices = {(value["source"], value["input_type"]) for value in route_options()}
    assert ("synology", "smtp") in choices
    assert ("synology", "http") in choices


def test_legacy_synology_and_zabbix_routes_remain_smtp():
    assert infer_input_type("synology") == "smtp"
    assert infer_input_type("zabbix") == "smtp"


def test_protect_accepts_payload_with_outer_alarm_id():
    payload = protect_payload()
    assert "alarm_id" in payload
    assert ProtectParser.is_envelope(payload)
    assert ProtectParser().parse(payload).metadata["alarm_id"]


def test_protect_accepts_payload_without_outer_alarm_id():
    payload = protect_payload()
    payload.pop("alarm_id", None)
    assert ProtectParser.is_envelope(payload)
    notification = ProtectParser().parse(payload)
    assert notification.source == "unifi_protect"
    assert notification.metadata["alarm_id"] == ""


def test_protect_rejects_payload_without_timestamp():
    payload = protect_payload()
    payload.pop("timestamp", None)
    assert ProtectParser.is_envelope(payload) is False


def test_protect_rejects_payload_without_alarm_dictionary():
    payload = protect_payload()
    payload["alarm"] = None
    assert ProtectParser.is_envelope(payload) is False


@pytest.mark.parametrize("field", ["conditions", "sources", "triggers"])
def test_protect_rejects_malformed_nested_lists(field):
    payload = protect_payload()
    payload["alarm"][field] = {"invalid": True}
    assert ProtectParser.is_envelope(payload) is False


@pytest.mark.parametrize(("source", "relative"), [("synology", "synology.png"), ("zabbix", "zabbix.png"), ("unifi_protect", "unifi-protect.png")])
def test_teams_icons_use_public_https_urls(source, relative):
    url = PresentationMixin()._product_icon_url(source)
    assert url.startswith("https://")
    assert url.endswith(f"/{relative}")
    assert "data:image/" not in url


def _components_thumbnail(url: str) -> dict:
    return {"components": [{"type": 17, "components": [{"type": 9, "components": [{"type": 10, "content": "Synthetic"}], "accessory": {"type": 11, "media": {"url": url}}}]}]}


def test_discord_resolves_exact_padded_packaged_variant():
    output = DiscordOutput()
    output.ICON_DIR = ROOT / "assets" / "icons"
    formatter = output.source_formatters["xo"]
    payload = _components_thumbnail("nowlert-asset://discord/xen-orchestra.png")
    filename, path, thumbnail = output._local_icon(payload, formatter)
    assert filename == "xen-orchestra.png"
    assert path == (ROOT / "assets" / "icons" / "discord" / "xen-orchestra.png").resolve()
    assert thumbnail["url"].startswith("nowlert-asset://")


def test_discord_resolves_regular_packaged_variant():
    output = DiscordOutput()
    output.ICON_DIR = ROOT / "assets" / "icons"
    formatter = output.source_formatters["synology"]
    payload = _components_thumbnail("nowlert-asset://synology.png")
    filename, path, _thumbnail = output._local_icon(payload, formatter)
    assert filename == "synology.png"
    assert path == (ROOT / "assets" / "icons" / "synology.png").resolve()


def test_discord_rejects_unmapped_and_traversal_assets():
    output = DiscordOutput()
    formatter = output.source_formatters["xo"]
    assert output._local_icon(_components_thumbnail("nowlert-asset://../secret"), formatter) is None
    assert output._local_icon(_components_thumbnail("nowlert-asset://unknown.png"), formatter) is None


def test_release_build_pins_teams_icons_while_discord_stays_packaged():
    presentation = (ROOT / "src" / "formatters" / "presentation.py").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    finalization = (ROOT / ".github" / "workflows" / "finalize-release.yml").read_text(encoding="utf-8")
    assert "NOWLERT_ICON_DIR" in presentation
    assert "NOWLERT_TEAMS_ICON_BASE_URL" in presentation
    assert "nowlert-asset://" in presentation
    assert "data:{mime_type};base64," not in presentation
    assert dockerfile.count("ARG NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert dockerfile.count("ENV NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert ci.count("NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert "${{ env.SOURCE_SHA }}/assets/icons" in ci
    assert "NOWLERT_TEAMS_ICON_BASE_URL=" not in finalization
    assert "docker/build-push-action" not in finalization


def test_invalid_teams_icon_base_url_fails_closed(monkeypatch):
    monkeypatch.setattr(PresentationMixin, "TEAMS_ICON_BASE_URL", "http://example.invalid/icons")
    assert PresentationMixin()._product_icon_url("synology") == ""
