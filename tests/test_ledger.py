from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "ledger.py"
spec = importlib.util.spec_from_file_location("nowlert_ledger", SCRIPT)
assert spec and spec.loader
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


def test_normalize_run_id_accepts_id_and_url() -> None:
    assert ledger.normalize_run_id("34720678064") == "34720678064"
    assert (
        ledger.normalize_run_id(
            "https://github.com/Theriark/nowlert-ce/actions/runs/34720678064"
        )
        == "34720678064"
    )


def test_active_ledger_environment_is_stage_only() -> None:
    assert ledger.VALID_ENVIRONMENTS == {"stage"}


def test_build_current_stage_record_is_edition_scoped() -> None:
    args = Namespace(
        environment="stage",
        image=ledger.IMAGE_PREFIX + "a" * 64,
        source_commit="b" * 40,
        promotion_run="34720678064",
        application_id="x9zOew6dmrn-jmcnFbllk",
        evidence_type="silent-promotion-smoke",
        health_url="https://ce-stg-nowlert.theriark.dev/api/health",
        success_marker="STAGE CE SILENT PROMOTION SMOKE PASSED",
        schedule_id="",
        schedule_deployment_id="",
        qa_marker="",
    )

    key, payload = ledger.build_current(args)

    assert key == f"{ledger.PREFIX}/stage/current.json"
    assert payload["edition"] == ledger.EDITION
    assert payload["image"] == args.image
    assert payload["source_commit"] == args.source_commit
    assert payload["promotion_run"] == "34720678064"
    assert payload["application_id"] == "x9zOew6dmrn-jmcnFbllk"
    assert payload["qa_evidence"]["type"] == "silent_promotion_smoke"
    assert payload["qa_evidence"]["notification_delivery_tests"] is False


def test_build_current_rejects_removed_production_reference() -> None:
    args = Namespace(
        environment="production-reference",
        image=ledger.IMAGE_PREFIX + "a" * 64,
        source_commit="b" * 40,
        promotion_run="34720678064",
        application_id="removed",
        evidence_type="silent-promotion-smoke",
        health_url="https://example.invalid/api/health",
        success_marker="removed",
        schedule_id="",
        schedule_deployment_id="",
        qa_marker="",
    )

    with pytest.raises(SystemExit):
        ledger.build_current(args)


def test_build_release_record_has_no_production_reference_fields(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "edition": "ce",
        "version": "v3.1.3",
        "source_commit": "b" * 40,
        "final_image": ledger.IMAGE_PREFIX + "a" * 64,
        "development_run": "34720356146",
        "stage_promotion_run": "34720678064",
        "stage_application_id": "x9zOew6dmrn-jmcnFbllk",
        "qa_evidence": {
            "type": "notification_silent_stage_final_acceptance",
            "notification_delivery_tests": False,
        },
    }
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    key, payload = ledger.build_release(Namespace(manifest=str(path)))

    assert key == f"{ledger.PREFIX}/releases/v3.1.3.json"
    assert payload["stage_promotion_run"] == "34720678064"
    assert payload["stage_application_id"] == "x9zOew6dmrn-jmcnFbllk"
    assert "production_reference_run" not in payload
    assert "production_reference_application_id" not in payload
