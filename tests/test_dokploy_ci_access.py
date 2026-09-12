"""Contracts for GitHub Actions access to the protected Dokploy control plane."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOKPLOY_RELEASE = ROOT / ".github" / "scripts" / "dokploy_release.py"
DEVELOPMENT_WORKFLOW = ROOT / ".github" / "workflows" / "docker-development.yml"


def load_dokploy_release():
    spec = importlib.util.spec_from_file_location("dokploy_release", DOKPLOY_RELEASE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b"{}"


def test_request_json_sends_cloudflare_service_auth_and_ci_user_agent(monkeypatch):
    module = load_dokploy_release()
    monkeypatch.setenv("DOKPLOY_URL", "https://dokploy.theriark.com")
    monkeypatch.setenv("DOKPLOY_API_KEY", "dokploy-test-key")
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "ci-client.access")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "ci-client-secret")

    captured = {}

    def fake_urlopen(request, timeout):
        captured["headers"] = {
            key.lower(): value for key, value in request.header_items()
        }
        return DummyResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    module.request_json(
        "GET",
        "application.one",
        query={"applicationId": "ivj7Ixgw2cP29g6riR2AH"},
    )

    headers = captured["headers"]
    assert headers["x-api-key"] == "dokploy-test-key"
    assert headers["cf-access-client-id"] == "ci-client.access"
    assert headers["cf-access-client-secret"] == "ci-client-secret"
    assert headers["user-agent"] == "Theriark-GitHub-Actions/1.0"


def test_development_workflow_targets_vm09_and_requires_machine_auth():
    workflow = DEVELOPMENT_WORKFLOW.read_text(encoding="utf-8")

    assert "DOKPLOY_CE_DEVELOPMENT_APPLICATION_ID: ivj7Ixgw2cP29g6riR2AH" in workflow
    assert "https://ce-dev.nowlert.theriark.dev/api/health" in workflow
    assert "CF_ACCESS_CLIENT_ID: ${{ secrets.CF_ACCESS_CLIENT_ID }}" in workflow
    assert "CF_ACCESS_CLIENT_SECRET: ${{ secrets.CF_ACCESS_CLIENT_SECRET }}" in workflow

    assert "LZHV0rpjSvusK9k9MGGpp" not in workflow
    assert "https://ce-dev.nowlert.theriark.com/api/health" not in workflow
