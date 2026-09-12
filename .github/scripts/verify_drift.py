#!/usr/bin/env python3
"""Read-only verification of Nowlert CE runtime images against the S3 ledger."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

AWS_REGION = "eu-west-1"
AWS_ACCOUNT_ID = "845958214943"
BUCKET = "theriark-ops-ledger-845958214943-eu-west-1"
KMS_KEY_ARN = "arn:aws:kms:eu-west-1:845958214943:key/f9818d3f-9708-4889-9a6f-1c6801037bf0"
EXPECTED_REPOSITORY = "Theriark/nowlert-ce"
EDITION = "ce"
PREFIX = "nowlert-ce"
IMAGE_PATTERN = re.compile(r"^ghcr\.io/theriark/nowlert-ce@sha256:[0-9a-f]{64}$")
SOURCE_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RUN_PATTERN = re.compile(r"^[0-9]+$")

ENVIRONMENTS = {
    "stage": {
        "application_id": "D0aI55MKe3G77LFdQcPdY",
    },
    "production-reference": {
        "application_id": "-Qb71PLUZmBHLJ_Iv68Oo",
    },
}


class DriftError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise DriftError(f"Required environment variable {name} is missing")
    return value


def validate_repository() -> None:
    repository = os.environ.get("GITHUB_REPOSITORY", EXPECTED_REPOSITORY)
    if repository != EXPECTED_REPOSITORY:
        raise DriftError(
            f"This verifier is restricted to {EXPECTED_REPOSITORY}, not {repository}"
        )


def run(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise DriftError(f"Required command is unavailable: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise DriftError(f"Command failed ({' '.join(command)}): {detail}") from exc
    return completed.stdout.strip()


def api_url(path: str, query: dict[str, str]) -> str:
    base = required_env("DOKPLOY_URL").rstrip("/")
    return f"{base}/api/{path.lstrip('/')}?{urllib.parse.urlencode(query)}"


def request_json(path: str, query: dict[str, str]) -> Any:
    request = urllib.request.Request(
        api_url(path, query),
        headers={
            "accept": "application/json",
            "x-api-key": required_env("DOKPLOY_API_KEY"),
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise DriftError(
            f"Dokploy read failed with HTTP {exc.code}: {body[:1000]}"
        ) from exc
    except (TimeoutError, urllib.error.URLError) as exc:
        raise DriftError(f"Dokploy read failed: {exc}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise DriftError("Dokploy returned invalid JSON") from exc


def find_key(value: Any, key: str) -> Any | None:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = find_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_key(child, key)
            if found is not None:
                return found
    return None


def current_image(application_id: str) -> str:
    payload = request_json(
        "application.one",
        {"applicationId": application_id},
    )
    image = find_key(payload, "dockerImage")
    if not isinstance(image, str) or not image.strip():
        raise DriftError(
            f"Could not read dockerImage for Dokploy application {application_id}"
        )
    return image.strip()


def validate_record(
    record: dict[str, Any],
    *,
    environment: str,
    application_id: str,
) -> str:
    expected_fields = {
        "schema_version": 1,
        "record_type": "desired_state",
        "edition": EDITION,
        "environment": environment,
        "application_id": application_id,
    }
    mismatches = [
        f"{name}: expected {expected!r}, found {record.get(name)!r}"
        for name, expected in expected_fields.items()
        if record.get(name) != expected
    ]
    if mismatches:
        raise DriftError("Ledger identity mismatch: " + "; ".join(mismatches))

    image = record.get("image")
    if not isinstance(image, str) or not IMAGE_PATTERN.fullmatch(image):
        raise DriftError("Ledger image is not an immutable Nowlert CE digest")

    source_commit = record.get("source_commit")
    if not isinstance(source_commit, str) or not SOURCE_PATTERN.fullmatch(source_commit):
        raise DriftError("Ledger source_commit is invalid")

    promotion_run = str(record.get("promotion_run", ""))
    if not RUN_PATTERN.fullmatch(promotion_run):
        raise DriftError("Ledger promotion_run is invalid")

    return image


def fetch_ledger_record(environment: str) -> tuple[dict[str, Any], str, str]:
    key = f"{PREFIX}/{environment}/current.json"
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
        raise DriftError(f"Ledger object {key} is not encrypted with SSE-KMS")
    if head.get("SSEKMSKeyId") != KMS_KEY_ARN:
        raise DriftError(f"Ledger object {key} uses an unexpected KMS key")
    if head.get("BucketKeyEnabled") is not True:
        raise DriftError(f"Ledger object {key} does not use the S3 Bucket Key")

    with tempfile.TemporaryDirectory(prefix="nowlert-drift-") as directory:
        target = Path(directory) / "current.json"
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
            record = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DriftError(f"Ledger object {key} is not valid JSON: {exc}") from exc

    if not isinstance(record, dict):
        raise DriftError(f"Ledger object {key} must contain a JSON object")

    return record, key, str(head.get("VersionId", ""))


def verify_environment(environment: str) -> dict[str, Any]:
    config = ENVIRONMENTS[environment]
    application_id = config["application_id"]
    record, key, version_id = fetch_ledger_record(environment)
    expected_image = validate_record(
        record,
        environment=environment,
        application_id=application_id,
    )
    observed_image = current_image(application_id)
    matches = observed_image == expected_image

    return {
        "environment": environment,
        "application_id": application_id,
        "ledger_key": key,
        "ledger_version_id": version_id,
        "approved_at": record.get("approved_at", ""),
        "source_commit": record.get("source_commit", ""),
        "promotion_run": str(record.get("promotion_run", "")),
        "expected_image": expected_image,
        "observed_image": observed_image,
        "matches": matches,
        "status": "in-sync" if matches else "drift",
    }


def write_summary(results: list[dict[str, Any]], errors: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines = [
        "## CE runtime drift verification",
        "",
        "| Environment | Result | Expected digest | Observed digest | Ledger version |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            "| {environment} | {status} | `{expected_image}` | `{observed_image}` | `{ledger_version_id}` |".format(
                **result
            )
        )
    for error in errors:
        lines.extend(["", f"- Error: `{error}`"])
    lines.extend(
        [
            "",
            "- Read-only verification: yes",
            "- Deployment performed: no",
            "- QA schedule triggered: no",
            "- Rollback performed: no",
        ]
    )
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="ce-runtime-drift-report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        validate_repository()
        required_env("DOKPLOY_URL")
        required_env("DOKPLOY_API_KEY")
        for environment in ENVIRONMENTS:
            try:
                result = verify_environment(environment)
                results.append(result)
                if result["matches"]:
                    print(
                        f"PASS: {environment} runs the approved image "
                        f"{result['expected_image']}"
                    )
                else:
                    message = (
                        f"DRIFT: {environment} application {result['application_id']} runs "
                        f"{result['observed_image']}, expected {result['expected_image']}"
                    )
                    errors.append(message)
                    print(f"::error::{message}", file=sys.stderr)
            except DriftError as exc:
                message = f"{environment}: {exc}"
                errors.append(message)
                print(f"::error::{message}", file=sys.stderr)
    except DriftError as exc:
        errors.append(str(exc))
        print(f"::error::{exc}", file=sys.stderr)

    report = {
        "schema_version": 1,
        "record_type": "runtime_drift_verification",
        "edition": EDITION,
        "repository": os.environ.get("GITHUB_REPOSITORY", EXPECTED_REPOSITORY),
        "generated_at": utc_now(),
        "aws_account_id": AWS_ACCOUNT_ID,
        "aws_region": AWS_REGION,
        "bucket": BUCKET,
        "read_only": True,
        "deployment_performed": False,
        "qa_schedule_triggered": False,
        "rollback_performed": False,
        "results": results,
        "errors": errors,
        "status": "failed" if errors else "in-sync",
    }
    Path(args.report).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_summary(results, errors)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
