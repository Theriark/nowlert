"""Permanent release icon wiring regressions."""

import json
from pathlib import Path

from models import Notification
from outputs.discord import DiscordOutput
import outputs.discord as discord_output_module


ROOT = Path(__file__).resolve().parents[1]


def notification():
    item = Notification(
        source="synology",
        title="Storage Pool Degraded",
        body="Storage Pool 1 entered a degraded state.",
        category="storage",
        status="warning",
    )
    item.metadata = {
        "nas_name": "NAS-02",
        "severity": "warning",
        "event_time": "2026-07-21T03:38:00+01:00",
        "message": "Storage Pool 1 entered a degraded state.",
    }
    return item


def find_thumbnail_media(value):
    if isinstance(value, dict):
        if value.get("type") == 11 and isinstance(value.get("media"), dict):
            return value["media"]
        for child in value.values():
            found = find_thumbnail_media(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_thumbnail_media(child)
            if found is not None:
                return found
    return None


def test_official_release_build_uses_packaged_notification_icons():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    development = (
        ROOT / ".github" / "workflows" / "docker-development.yml"
    ).read_text(encoding="utf-8")
    finalization = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")
    presentation = (
        ROOT / "src" / "formatters" / "presentation.py"
    ).read_text(encoding="utf-8")

    assert "COPY assets /nowlert/assets" in dockerfile
    assert "validate_packaged_icons.py" in dockerfile

    assert "NOWLERT_ICON_DIR" in presentation
    assert "NOWLERT_TEAMS_ICON_BASE_URL" in presentation
    assert "nowlert-asset://" in presentation
    assert "data:{mime_type};base64," not in presentation
    assert dockerfile.count("ARG NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert dockerfile.count("ENV NOWLERT_TEAMS_ICON_BASE_URL=") == 1

    # The one and only image build is the Development build.
    assert development.count("NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert "${{ env.SOURCE_SHA }}/assets/icons" in development

    # Release finalization only republishes the approved image digest.
    assert "NOWLERT_TEAMS_ICON_BASE_URL=" not in finalization
    assert "docker/build-push-action" not in finalization


def test_components_v2_delivery_uploads_packaged_icon(monkeypatch, tmp_path):
    icon = tmp_path / "synology.png"
    icon.write_bytes(b"synthetic-png")
    captured = {}

    class Config:
        def get(self, *keys, default=None):
            if keys[-1:] == ("webhook",):
                return "https://discord.com/api/webhooks/123/token"
            return default

    class Response:
        status_code = 204
        text = ""

    def fake_post(url, data, files, timeout):
        captured["url"] = url
        captured["payload"] = json.loads(data["payload_json"])
        captured["filename"] = files["files[0]"][0]
        captured["content"] = files["files[0]"][1].read()
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(discord_output_module, "config", Config())
    monkeypatch.setattr(discord_output_module.requests, "post", fake_post)

    output = DiscordOutput()
    output.ICON_DIR = tmp_path
    assert output.send(notification(), target="synology")

    payload = captured["payload"]
    media = find_thumbnail_media(payload["components"])
    assert media == {"url": "attachment://synology.png"}
    assert payload["attachments"] == [{"id": 0, "filename": "synology.png"}]
    assert captured["filename"] == "synology.png"
    assert captured["content"] == b"synthetic-png"
    assert payload["flags"] == 32768
    assert captured["timeout"] == 15
