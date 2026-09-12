"""Contracts for GitHub Actions access to the protected Dokploy control plane."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOKPLOY_RELEASE = ROOT / ".github" / "scripts" / "dokploy_release.py"
VERIFY_DRIFT = ROOT / ".github" / "scripts" / "verify_drift.py"
WORKFLOWS = {
    "development": ROOT / ".github" / "workflows" / "docker-development.yml",
    "stage": ROOT / ".github" / "workflows" / "promote-stage.yml",
    "production-reference": ROOT
    / ".github"
    / "workflows"
    / "promote-production-reference.yml",
    "finalize": ROOT / ".github" / "workflows" / "finalize-release.yml",
    "runtime-drift": ROOT / ".github" / "workflows" / "verify-runtime-drift.yml",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
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


def _capture_headers(monkeypatch, module, call):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["headers"] = {
            key.lower(): value for key, value in request.header_items()
        }
        return DummyResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    call()
    return captured["headers"]


def _set_machine_auth_env(monkeypatch):
    monkeypatch.setenv("DOKPLOY_URL", "https://dokploy.theriark.com")
    monkeypatch.setenv("DOKPLOY_API_KEY", "dokploy-test-key")
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "ci-client.access")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "ci-client-secret")


def test_release_helper_sends_cloudflare_service_auth_and_ci_user_agent(monkeypatch):
    module = load_module("dokploy_release", DOKPLOY_RELEASE)
    _set_machine_auth_env(monkeypatch)

    headers = _capture_headers(
        monkeypatch,
        module,
        lambda: module.request_json(
            "GET",
            "application.one",
            query={"applicationId": "ivj7Ixgw2cP29g6riR2AH"},
        ),
    )

    assert headers["x-api-key"] == "dokploy-test-key"
    assert headers["cf-access-client-id"] == "ci-client.access"
    assert headers["cf-access-client-secret"] == "ci-client-secret"
    assert headers["user-agent"] == "Theriark-GitHub-Actions/1.0"


def test_runtime_drift_helper_sends_cloudflare_service_auth_and_ci_user_agent(monkeypatch):
    module = load_module("verify_drift", VERIFY_DRIFT)
    _set_machine_auth_env(monkeypatch)

    headers = _capture_headers(
        monkeypatch,
        module,
        lambda: module.request_json(
            "application.one",
            {"applicationId": "D0aI55MKe3G77LFdQcPdY"},
        ),
    )

    assert headers["x-api-key"] == "dokploy-test-key"
    assert headers["cf-access-client-id"] == "ci-client.access"
    assert headers["cf-access-client-secret"] == "ci-client-secret"
    assert headers["user-agent"] == "Theriark-GitHub-Actions/1.0"


def test_all_dokploy_workflows_use_shared_cloudflare_machine_auth_secrets():
    for name, path in WORKFLOWS.items():
        workflow = path.read_text(encoding="utf-8")
        assert (
            "CF_ACCESS_CLIENT_ID: ${{ secrets.CF_ACCESS_CLIENT_ID }}" in workflow
        ), name
        assert (
            "CF_ACCESS_CLIENT_SECRET: ${{ secrets.CF_ACCESS_CLIENT_SECRET }}" in workflow
        ), name


def test_development_workflow_targets_vm09_and_flattened_hostname():
    workflow = WORKFLOWS["development"].read_text(encoding="utf-8")

    assert "DOKPLOY_CE_DEVELOPMENT_APPLICATION_ID: ivj7Ixgw2cP29g6riR2AH" in workflow
    assert "https://ce-dev-nowlert.theriark.dev/api/health" in workflow

    assert "LZHV0rpjSvusK9k9MGGpp" not in workflow
    assert "https://ce-dev.nowlert.theriark.com/api/health" not in workflow
    assert "https://ce-dev.nowlert.theriark.dev/api/health" not in workflow
