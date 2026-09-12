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


def test_promotion_workflow_yaml_is_valid() -> None:
    for relative in (
        ".github/workflows/promote-stage.yml",
        ".github/workflows/promote-production-reference.yml",
        ".github/workflows/finalize-release.yml",
    ):
        payload = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        assert isinstance(payload, dict), relative


def test_stage_promotion_targets_migrated_vm09_application_and_hostname() -> None:
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )
    prodref = (
        ROOT / ".github" / "workflows" / "promote-production-reference.yml"
    ).read_text(encoding="utf-8")

    assert f"CE_STAGE_APPLICATION_ID: {STAGE_APPLICATION_ID}" in stage
    assert f"CE_STAGE_APPLICATION_ID: {STAGE_APPLICATION_ID}" in prodref
    assert STAGE_HEALTH_URL in stage

    assert "D0aI55MKe3G77LFdQcPdY" not in stage
    assert "D0aI55MKe3G77LFdQcPdY" not in prodref
    assert "https://ce-stage.nowlert.theriark.com/api/health" not in stage


def test_automatic_promotion_workflows_have_zero_active_delivery_test_paths() -> None:
    forbidden = (
        "run-schedule",
        "stage_ce_qa_schedule_id",
        "prodref_ce_smoke_schedule_id",
        "schedule-id",
        "/api/v2",
    )

    for relative in (
        ".github/workflows/promote-stage.yml",
        ".github/workflows/promote-production-reference.yml",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        folded = content.casefold()
        assert "promotion-smoke" in content
        assert "external notification delivery during promotion: disabled" in folded
        assert "--evidence-type silent-promotion-smoke" in content
        for value in forbidden:
            assert value not in folded, (relative, value)


def test_full_promotion_gates_run_complete_suite_without_external_network() -> None:
    workflows = {
        ".github/workflows/promote-stage.yml": "STAGE CE SILENT FULL GATE PASSED",
        ".github/workflows/promote-production-reference.yml": (
            "PRODUCTION REFERENCE CE SILENT FULL GATE PASSED"
        ),
    }

    for relative, marker in workflows.items():
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "requirements-dev.txt" in content
        assert "env -i" in content
        assert '"${UNSHARE_BIN}" --net' in content
        assert "route show default" in content
        assert "addr show scope global" in content
        assert "PASS: promotion gate network namespace has no default route" in content
        assert '"${PYTHON_BIN}" -m pytest -q' in content
        assert marker in content


def test_production_reference_rejects_unsafe_stage_promotion_evidence() -> None:
    content = (
        ROOT / ".github" / "workflows" / "promote-production-reference.yml"
    ).read_text(encoding="utf-8")

    for required in (
        "STAGE CE SILENT FULL GATE PASSED",
        "STAGE CE SILENT PROMOTION SMOKE PASSED",
        "PASS: promotion gate network namespace has no default route",
        "PASS: notification delivery tests disabled for this promotion smoke",
    ):
        assert required in content

    assert 'grep -Fq "${forbidden}" "${stage_log}"' in content

    # The finalizer scans the complete Actions log for these runtime markers.
    # They must therefore not appear contiguously in the ProdRef workflow source,
    # because Actions echoes the shell source before executing it.
    for forbidden_log_fragment in (
        "===== DELIVERY =====",
        "Expected deliveries:",
        "Accepted deliveries:",
        "Related firing run:",
        "stage-ce-all-",
        "stage-ce-zabbix-",
        "stage-ce-portainer-",
    ):
        assert forbidden_log_fragment not in content

    # Adjacent shell strings reconstruct the exact same values at runtime, so
    # the Stage log rejection remains strict without poisoning the ProdRef log.
    for split_guard_fragment in (
        '"===== ""DELIVERY ====="',
        '"Expected ""deliveries:"',
        '"Accepted ""deliveries:"',
        '"Related ""firing run:"',
        '"stage-ce-""all-"',
        '"stage-ce-""zabbix-"',
        '"stage-ce-""portainer-"',
    ):
        assert split_guard_fragment in content


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


def test_release_finalization_rejects_delivery_qa_for_new_promotion_chain() -> None:
    finalizer = (
        ROOT / ".github" / "scripts" / "finalize_release.py"
    ).read_text(encoding="utf-8")
    workflow = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")

    assert "STAGE CE SILENT PROMOTION SMOKE PASSED" in finalizer
    assert "PRODUCTION REFERENCE CE SILENT PROMOTION SMOKE PASSED" in finalizer
    assert "SILENT_PROMOTION_FORBIDDEN_LOG_FRAGMENTS" in finalizer
    assert "qa_schedule_deployment_id" not in workflow
    assert "Notification delivery tests during promotions: disabled" in workflow


def test_legacy_schedule_runner_remains_available_but_is_not_auto_promoted() -> None:
    helper = load_helper()
    assert callable(helper.run_schedule)

    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )
    prodref = (
        ROOT / ".github" / "workflows" / "promote-production-reference.yml"
    ).read_text(encoding="utf-8")
    assert "run-schedule" not in stage
    assert "run-schedule" not in prodref
