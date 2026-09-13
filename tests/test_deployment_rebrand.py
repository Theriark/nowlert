"""Nowlert deployment identity."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_production_compose_uses_nowlert_identity():
    compose = yaml.safe_load(
        (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    )

    assert compose["name"] == "nowlert-ce"
    assert "nowlert-ce" in compose["services"]

    service = compose["services"]["nowlert-ce"]

    assert service["container_name"] == "nowlert-ce"
    assert service["image"] == "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.6}"


def test_production_compose_uses_nowlert_host_variables():
    document = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

    names = (
        "NOWLERT_IMAGE",
        "NOWLERT_UID",
        "NOWLERT_GID",
        "NOWLERT_SMTP_PORT",
        "NOWLERT_HTTP_PORT",
        "NOWLERT_CONFIG_DIR",
        "NOWLERT_LOG_DIR",
        "NOWLERT_SECRETS_DIR",
        "NOWLERT_STATE_DIR",
        "NOWLERT_EXTERNAL_BACKUP_DIR",
        "NOWLERT_SMTP_PASSWORD",
        "NOWLERT_ADMIN_TOKEN",
        "NOWLERT_HARDWARE_TOKEN",
        "NOWLERT_AVAILABLE_VERSION",
    )

    for name in names:
        assert name in document


def test_new_environment_example_uses_nowlert_namespace():
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")

    assignments = [
        line
        for line in environment.splitlines()
        if line and not line.startswith("#") and "=" in line
    ]

    nowlert_assignments = [
        line for line in assignments if line.startswith("NOWLERT_")
    ]
    assert nowlert_assignments


def test_internal_container_paths_use_nowlert():
    compose = yaml.safe_load(
        (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    )
    service = compose["services"]["nowlert-ce"]

    assert service["environment"]["NOWLERT_STATE_DIR"] == "/nowlert/state"

    targets = {
        volume.rsplit(":", 1)[-1]
        for volume in service["volumes"]
    }

    assert "/nowlert/config" in targets
    assert "/nowlert/logs" in targets
    assert "/nowlert/state" in targets
    assert "/nowlert/external-backups" in targets


def test_development_compose_uses_nowlert_identity():
    compose = yaml.safe_load(
        (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    service = compose["services"]["nowlert-ce-dev"]

    assert service["image"] == "nowlert-ce-dev:local"
    assert service["container_name"] == "nowlert-ce-dev"
    assert service["working_dir"] == "/nowlert"
    assert service["command"] == "/nowlert/start.sh"
