from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "verify_drift.py"
spec = importlib.util.spec_from_file_location("verify_drift", SCRIPT)
assert spec and spec.loader
verify_drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_drift)


def valid_record(environment: str, application_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "desired_state",
        "edition": "ce",
        "environment": environment,
        "application_id": application_id,
        "image": "ghcr.io/theriark/nowlert-ce@sha256:" + "a" * 64,
        "source_commit": "b" * 40,
        "promotion_run": "30776030212",
        "approved_at": "2026-08-03T00:00:00+00:00",
    }


def test_stage_targets_migrated_dokploy_application() -> None:
    assert (
        verify_drift.ENVIRONMENTS["stage"]["application_id"]
        == "x9zOew6dmrn-jmcnFbllk"
    )


def test_validate_stage_record_returns_immutable_image() -> None:
    application_id = verify_drift.ENVIRONMENTS["stage"]["application_id"]
    record = valid_record("stage", application_id)

    assert (
        verify_drift.validate_record(
            record,
            environment="stage",
            application_id=application_id,
        )
        == record["image"]
    )


def test_validate_record_rejects_wrong_application() -> None:
    application_id = verify_drift.ENVIRONMENTS["production-reference"][
        "application_id"
    ]
    record = valid_record("production-reference", "wrong-application")

    with pytest.raises(verify_drift.DriftError, match="application_id"):
        verify_drift.validate_record(
            record,
            environment="production-reference",
            application_id=application_id,
        )


def test_validate_record_rejects_mutable_image() -> None:
    application_id = verify_drift.ENVIRONMENTS["stage"]["application_id"]
    record = valid_record("stage", application_id)
    record["image"] = "ghcr.io/theriark/nowlert-ce:main"

    with pytest.raises(verify_drift.DriftError, match="immutable"):
        verify_drift.validate_record(
            record,
            environment="stage",
            application_id=application_id,
        )
