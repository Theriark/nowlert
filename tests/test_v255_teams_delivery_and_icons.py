"""v2.5.5 Microsoft Teams delivery and icon regressions."""

from __future__ import annotations

import json
import socket
from pathlib import Path

from models import Notification
from outputs.platform import TeamsPlatformAdapter
from outputs.teams import TeamsOutput
from storage.destinations import Destination
import outputs.teams as teams_output_module


ROOT = Path(__file__).resolve().parents[1]


class Response:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.text = ""


class HTTPClient:
    def __init__(self, status_code: int = 202):
        self.status_code = status_code
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return Response(self.status_code)


def public_resolver(*_args, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 443),
        )
    ]


def destination() -> Destination:
    return Destination(
        id="t" * 32,
        owner_user_id="u" * 32,
        name="Teams",
        output_type="teams",
        settings={},
        shared=True,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def notification(source: str = "nowlert") -> Notification:
    return Notification(
        source=source,
        title="Safe Microsoft Teams test",
        body="Safe Nowlert destination test.",
        status="information",
        category="hardware",
        metadata={
            "provider": "HPE iLO" if source == "hpe_ilo" else "Nowlert",
            "host": "Delta",
            "severity": "information",
        },
    )


def _image_items(value):
    items = []
    if isinstance(value, dict):
        if value.get("type") == "Image":
            items.append(value)
        for child in value.values():
            items.extend(_image_items(child))
    elif isinstance(value, list):
        for child in value:
            items.extend(_image_items(child))
    return items


def image_urls(value):
    urls = []
    if isinstance(value, dict):
        if value.get("type") == "Image":
            urls.append(value.get("url"))
        for child in value.values():
            urls.extend(image_urls(child))
    elif isinstance(value, list):
        for child in value:
            urls.extend(image_urls(child))
    return urls


def test_generic_and_hpe_ilo_cards_use_small_public_https_icons():
    output = TeamsOutput()
    for source, filename, expected_pixels in (("nowlert", "nowlert.png", 80), ("hpe_ilo", "hpe-ilo.png", 64)):
        formatter = output.source_formatters.get(source, output.default_formatter)
        payload = formatter._sanitize_payload(formatter.format(notification(source)))
        urls = image_urls(payload)
        assert urls
        assert all(url.startswith("https://") for url in urls)
        assert any(url.endswith(f"/{filename}") for url in urls)
        assert "data:image/" not in json.dumps(payload)
        assert any(image.get("url", "").endswith(f"/{filename}") and image.get("width") == f"{expected_pixels}px" and image.get("height") == f"{expected_pixels}px" for image in _image_items(payload))
        assert output.payload_size(payload) <= output.MAX_PAYLOAD_BYTES


def test_platform_teams_rejects_oversized_payload_before_posting():
    client = HTTPClient()
    adapter = TeamsPlatformAdapter(http_client=client, resolver=public_resolver)
    adapter.output.MAX_PAYLOAD_BYTES = 1
    result = adapter.deliver(destination(), b"https://example.com/teams-workflow", notification())
    assert result.success is False
    assert result.response_status is None
    assert result.error_code == "teams_payload_too_large"
    assert "exceeds the 1-byte limit" in result.safe_error
    assert client.calls == []


def test_legacy_teams_rejects_oversized_payload_before_posting(monkeypatch):
    calls = []
    class Config:
        def get(self, *keys, default=None):
            if keys[-1:] == ("webhook",):
                return "https://example.com/teams-workflow"
            return default
    monkeypatch.setattr(teams_output_module, "config", Config())
    monkeypatch.setattr(teams_output_module.requests, "post", lambda *args, **kwargs: calls.append((args, kwargs)))
    output = TeamsOutput()
    output.MAX_PAYLOAD_BYTES = 1
    assert output.send(notification()) is False
    assert calls == []


def test_http_202_is_accepted_but_webui_does_not_claim_delivery():
    client = HTTPClient(status_code=202)
    adapter = TeamsPlatformAdapter(http_client=client, resolver=public_resolver)
    result = adapter.deliver(destination(), b"https://example.com/teams-workflow", notification())
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    assert result.success is True
    assert result.response_status == 202
    assert len(client.calls) == 1
    assert "Microsoft Teams accepted the test (HTTP 202)." in script
    assert "Delivery is not confirmed; check the channel." in script
    assert "Last Microsoft Teams test was accepted with HTTP 202" in script


def test_release_image_pins_the_teams_icon_base_to_source_commit():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    finalization = (ROOT / ".github" / "workflows" / "finalize-release.yml").read_text(encoding="utf-8")
    assert dockerfile.count("ARG NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert dockerfile.count("ENV NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert ci.count("NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert "${{ env.SOURCE_SHA }}/assets/icons" in ci
    assert "NOWLERT_TEAMS_ICON_BASE_URL=" not in finalization
    assert "docker/build-push-action" not in finalization
