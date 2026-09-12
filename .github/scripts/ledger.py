#!/usr/bin/env python3
"""Write and verify immutable Nowlert desired-state ledger records in S3."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

AWS_REGION = "eu-west-1"
AWS_ACCOUNT_ID = "845958214943"
BUCKET = "theriark-ops-ledger-845958214943-eu-west-1"
KMS_KEY_ARN = "arn:aws:kms:eu-west-1:845958214943:key/f9818d3f-9708-4889-9a6f-1c6801037bf0"
EXPECTED_REPOSITORY = "Theriark/nowlert-ce"
EDITION = "ce"
PREFIX = "nowlert-ce"
IMAGE_PREFIX = f"ghcr.io/theriark/{PREFIX}@sha256:"
STAGE_APPLICATION_ID = "x9zOew6dmrn-jmcnFbllk"
VALID_ENVIRONMENTS = {"stage"}


def fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def run(command: list[str], *, capture: bool = True) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=capture,
        )
    except FileNotFoundError:
        fail(f"Required command is unavailable: {command[0]}")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        fail(f"Command failed ({' '.join(command)}): {detail}")
    return completed.stdout.strip() if capture else ""


def validate_repository() -> None:
    repository = os.environ.get("GITHUB_REPOSITORY", EXPECTED_REPOSITORY)
    if repository != EXPECTED_REPOSITORY:
        fail(f"This ledger writer is restricted to {EXPECTED_REPOSITORY}, not {repository}")


def validate_image(image: str) -> None:
    if not re.fullmatch(re.escape(IMAGE_PREFIX) + r"[0-9a-f]{64}", image):
        fail(f"Image must be an immutable {PREFIX} digest")


def validate_source_commit(source_commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        fail("Source commit must be a full lowercase 40-character SHA")


def normalize_run_id(value: str) -> str:
    value = value.strip().rstrip("/")
    match = re.search(r"(?:^|/)([0-9]+)$", value)
    if not match:
        fail(f"Workflow run must be a numeric ID or URL ending in a numeric ID: {value}")
    return match.group(1)


def validate_token(value: str, label: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        fail(f"{label} contains unexpected characters")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def workflow_metadata() -> dict[str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", EXPECTED_REPOSITORY)
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}" if run_id else ""
    return {
        "repository": repository,
        "workflow": os.environ.get("GITHUB_WORKFLOW", ""),
        "run_id": run_id,
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "run_url": run_url,
        "workflow_commit": os.environ.get("GITHUB_SHA", ""),
        "actor": os.environ.get("GITHUB_ACTOR", ""),
    }


def json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def set_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def upload_record(key: str, payload: dict[str, Any], output_path: str | None) -> None:
    body = json_bytes(payload)
    digest = hashlib.sha256(body).hexdigest()

    if output_path:
        Path(output_path).write_bytes(body)

    with tempfile.TemporaryDirectory(prefix="nowlert-ledger-") as directory:
        source = Path(directory) / "record.json"
        downloaded = Path(directory) / "downloaded.json"
        source.write_bytes(body)

        response = json.loads(
            run(
                [
                    "aws",
                    "s3api",
                    "put-object",
                    "--region",
                    AWS_REGION,
                    "--bucket",
                    BUCKET,
                    "--key",
                    key,
                    "--body",
                    str(source),
                    "--content-type",
                    "application/json",
                    "--server-side-encryption",
                    "aws:kms",
                    "--ssekms-key-id",
                    KMS_KEY_ARN,
                    "--bucket-key-enabled",
                    "--metadata",
                    f"sha256={digest},edition={EDITION}",
                    "--output",
                    "json",
                ]
            )
        )

        head = json.loads(
            run(
                [
                    "aws",
                    "s3api",
                    "head-object",
                    "--region",
                    AWS_REGION,
                    "--bucket",
                    BUCKET,
                    "--key",
                    key,
                    "--output",
                    "json",
                ]
            )
        )
        if head.get("ServerSideEncryption") != "aws:kms":
            fail(f"Ledger object {key} is not encrypted with SSE-KMS")
        if head.get("SSEKMSKeyId") != KMS_KEY_ARN:
            fail(f"Ledger object {key} uses an unexpected KMS key")
        if head.get("BucketKeyEnabled") is not True:
            fail(f"Ledger object {key} does not use the S3 Bucket Key")
        if head.get("Metadata", {}).get("sha256") != digest:
            fail(f"Ledger object {key} metadata checksum does not match")

        run(
            [
                "aws",
                "s3api",
                "get-object",
                "--region",
                AWS_REGION,
                "--bucket",
                BUCKET,
                "--key",
                key,
                str(downloaded),
                "--output",
                "json",
            ]
        )
        if downloaded.read_bytes() != body:
            fail(f"Ledger object {key} does not match the uploaded record")

    version_id = str(response.get("VersionId", ""))
    etag = str(response.get("ETag", "")).strip('"')
    set_output("key", key)
    set_output("version_id", version_id)
    set_output("etag", etag)
    set_output("sha256", digest)
    print(f"Wrote s3://{BUCKET}/{key} version {version_id or '(none)'}")


def fetch_record(key: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nowlert-ledger-read-") as directory:
        target = Path(directory) / "record.json"
        run(
            [
                "aws",
                "s3api",
                "get-object",
                "--region",
                AWS_REGION,
                "--bucket",
                BUCKET,
                "--key",
                key,
                str(target),
                "--output",
                "json",
            ]
        )
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"Ledger object {key} is not valid JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"Ledger object {key} must contain a JSON object")
    return value


def build_current(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    if args.environment not in VALID_ENVIRONMENTS:
        fail(f"Environment must be one of {sorted(VALID_ENVIRONMENTS)}")
    validate_image(args.image)
    validate_source_commit(args.source_commit)
    promotion_run = normalize_run_id(args.promotion_run)
    validate_token(args.application_id, "Application ID")

    evidence_type = str(getattr(args, "evidence_type", "schedule") or "schedule")
    if evidence_type == "schedule":
        schedule_id = str(getattr(args, "schedule_id", "") or "").strip()
        schedule_deployment_id = str(
            getattr(args, "schedule_deployment_id", "") or ""
        ).strip()
        qa_marker = str(getattr(args, "qa_marker", "") or "").strip()
        validate_token(schedule_id, "Schedule ID")
        validate_token(schedule_deployment_id, "Schedule deployment ID")
        if not qa_marker:
            fail("QA marker must not be empty")
        evidence = {
            "type": "qa_schedule",
            "schedule_id": schedule_id,
            "schedule_deployment_id": schedule_deployment_id,
            "success_marker": qa_marker,
            "notification_delivery_tests": True,
        }
    elif evidence_type == "silent-promotion-smoke":
        health_url = str(getattr(args, "health_url", "") or "").strip()
        success_marker = str(getattr(args, "success_marker", "") or "").strip()
        if not health_url.startswith("https://"):
            fail("Silent promotion smoke health URL must use https://")
        if not success_marker:
            fail("Silent promotion smoke success marker must not be empty")
        evidence = {
            "type": "silent_promotion_smoke",
            "health_url": health_url,
            "success_marker": success_marker,
            "notification_delivery_tests": False,
            "schedule_triggered": False,
        }
    else:
        fail(f"Unsupported evidence type: {evidence_type}")

    key = f"{PREFIX}/{args.environment}/current.json"
    payload = {
        "schema_version": 1,
        "record_type": "desired_state",
        "edition": EDITION,
        "environment": args.environment,
        "image": args.image,
        "source_commit": args.source_commit,
        "promotion_run": promotion_run,
        "application_id": args.application_id,
        "qa_evidence": evidence,
        "workflow": workflow_metadata(),
        "approved_at": utc_now(),
    }
    return key, payload


def build_release(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Release manifest is unavailable or invalid: {exc}")
    if not isinstance(manifest, dict):
        fail("Release manifest must contain a JSON object")

    version = str(manifest.get("version", ""))
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        fail("Release manifest version is invalid")
    if manifest.get("edition") != EDITION:
        fail(f"Release manifest edition must be {EDITION}")
    validate_image(str(manifest.get("final_image", "")))
    validate_source_commit(str(manifest.get("source_commit", "")))

    stage_application_id = str(manifest.get("stage_application_id", ""))
    if stage_application_id != STAGE_APPLICATION_ID:
        fail(
            "Release manifest Stage application ID does not match the approved "
            f"application {STAGE_APPLICATION_ID}"
        )

    key = f"{PREFIX}/releases/{version}.json"
    payload = {
        "schema_version": 1,
        "record_type": "release",
        "edition": EDITION,
        "version": version,
        "source_commit": manifest["source_commit"],
        "final_image": manifest["final_image"],
        "development_run": str(manifest.get("development_run", "")),
        "stage_promotion_run": str(manifest.get("stage_promotion_run", "")),
        "stage_application_id": stage_application_id,
        "qa_evidence": manifest.get("qa_evidence", {}),
        "release_manifest": manifest,
        "workflow": workflow_metadata(),
        "approved_at": utc_now(),
    }
    return key, payload


def command_current(args: argparse.Namespace) -> None:
    key, payload = build_current(args)
    upload_record(key, payload, args.output_path)


def command_release(args: argparse.Namespace) -> None:
    key, payload = build_release(args)
    upload_record(key, payload, args.output_path)


def command_assert_current(args: argparse.Namespace) -> None:
    if args.environment not in VALID_ENVIRONMENTS:
        fail(f"Environment must be one of {sorted(VALID_ENVIRONMENTS)}")
    validate_image(args.image)
    validate_source_commit(args.source_commit)
    expected_run = normalize_run_id(args.promotion_run)
    key = f"{PREFIX}/{args.environment}/current.json"
    record = fetch_record(key)

    expected = {
        "schema_version": 1,
        "record_type": "desired_state",
        "edition": EDITION,
        "environment": args.environment,
        "image": args.image,
        "source_commit": args.source_commit,
        "promotion_run": expected_run,
    }
    mismatches = [
        f"{name}: expected {value!r}, found {record.get(name)!r}"
        for name, value in expected.items()
        if record.get(name) != value
    ]
    if mismatches:
        fail(f"Ledger record {key} does not match: {'; '.join(mismatches)}")
    print(f"PASS: {key} matches image, source commit, and promotion run")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    current = subparsers.add_parser("current")
    current.add_argument("--environment", required=True)
    current.add_argument("--image", required=True)
    current.add_argument("--source-commit", required=True)
    current.add_argument("--promotion-run", required=True)
    current.add_argument("--application-id", required=True)
    current.add_argument(
        "--evidence-type",
        choices=("schedule", "silent-promotion-smoke"),
        default="schedule",
    )
    current.add_argument("--health-url", default="")
    current.add_argument("--success-marker", default="")
    current.add_argument("--schedule-id", default="")
    current.add_argument("--schedule-deployment-id", default="")
    current.add_argument("--qa-marker", default="")
    current.add_argument("--output-path")
    current.set_defaults(function=command_current)

    release = subparsers.add_parser("release")
    release.add_argument("--manifest", required=True)
    release.add_argument("--output-path")
    release.set_defaults(function=command_release)

    assert_current = subparsers.add_parser("assert-current")
    assert_current.add_argument("--environment", required=True)
    assert_current.add_argument("--image", required=True)
    assert_current.add_argument("--source-commit", required=True)
    assert_current.add_argument("--promotion-run", required=True)
    assert_current.set_defaults(function=command_assert_current)

    return parser.parse_args()


def main() -> None:
    validate_repository()
    args = parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
