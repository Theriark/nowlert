"""Safety contract for notification-silent release promotions."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".github" / "scripts" / "dokploy_release.py"
STAGE_APPLICATION_ID = "x9zOew6dmrn-jmcnFbllk"
STAGE_HEALTH_URL = "https://ce-stg-nowlert.theriark.dev/api/health"


def load_helper():
    spec = importlib.util.spec_from_file_location("nowlert_dokploy_release", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_workflow_yaml_is_valid() -> None:
    for relative in (
        ".github/workflows/promote-stage.yml",
        ".github/workflows/finalize-release.yml",
    ):
        payload = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        assert isinstance(payload, dict), relative

    assert not (ROOT / ".github" / "workflows" / "promote-production-reference.yml").exists()


def test_stage_promotion_targets_migrated_vm09_application_and_hostname() -> None:
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )

    assert f"CE_STAGE_APPLICATION_ID: {STAGE_APPLICATION_ID}" in stage
    assert STAGE_HEALTH_URL in stage
    assert "D0aI55MKe3G77LFdQcPdY" not in stage
    assert "https://ce-stage.nowlert.theriark.com/api/health" not in stage


def test_automatic_stage_promotion_has_zero_active_delivery_test_paths() -> None:
    forbidden = (
        "run-schedule",
        "stage_ce_qa_schedule_id",
        "prodref_ce_smoke_schedule_id",
        "schedule-id",
        "/api/v2",
    )

    content = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )
    folded = content.casefold()
    assert "promotion-smoke" in content
    assert "external notification delivery during promotion: disabled" in folded
    assert "--evidence-type silent-promotion-smoke" in content
    for value in forbidden:
        assert value not in folded, value


def test_stage_full_gate_runs_complete_suite_without_external_network() -> None:
    content = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )
    assert "requirements-dev.txt" in content
    assert "env -i" in content
    assert '"${UNSHARE_BIN}" --net' in content
    assert "route show default" in content
    assert "addr show scope global" in content
    assert "PASS: promotion gate network namespace has no default route" in content
    assert '"${PYTHON_BIN}" -m pytest -q' in content
    assert "STAGE CE SILENT FULL GATE PASSED" in content


def test_promotion_smoke_function_is_passive_and_read_only() -> None:
    helper = load_helper()
    smoke = inspect.getsource(helper.promotion_smoke)
    folded = smoke.casefold()

    assert "wait_health(" in smoke
    assert "current_image(" in smoke
    assert "notification delivery tests disabled" in folded

    for forbidden in (
        "request_json(",
        "run_schedule(",
        "schedule.runmanually",
        "urllib.request",
        "post",
        "smtp",
        "/api/v2",
        "firing",
        "resolved",
    ):
        assert forbidden not in folded, forbidden

    health = inspect.getsource(helper.wait_health).casefold()
    assert "urllib.request.request(" in health
    assert "data=" not in health
    assert 'method="post"' not in health

    image_lookup = inspect.getsource(helper.current_image).casefold()
    assert '"get"' in image_lookup
    assert '"post"' not in image_lookup


def test_release_finalization_requires_stage_silent_gate_only() -> None:
    finalizer = (
        ROOT / ".github" / "scripts" / "finalize_release.py"
    ).read_text(encoding="utf-8")
    workflow = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")

    assert "STAGE CE SILENT PROMOTION SMOKE PASSED" in finalizer
    assert "SILENT_PROMOTION_FORBIDDEN_LOG_FRAGMENTS" in finalizer
    assert "PRODUCTION REFERENCE CE SILENT PROMOTION SMOKE PASSED" not in finalizer
    assert "production_reference" not in finalizer.casefold()
    assert "production_reference_run_id" not in workflow
    assert "CE_PRODREF_APPLICATION_ID" not in workflow
    assert "--environment stage" in workflow
    assert "Notification delivery tests during Stage promotion: disabled" in workflow


def test_legacy_schedule_runner_remains_available_but_is_not_auto_promoted() -> None:
    helper = load_helper()
    assert callable(helper.run_schedule)

    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )
    assert "run-schedule" not in stage
    assert not (ROOT / ".github" / "workflows" / "promote-production-reference.yml").exists()
