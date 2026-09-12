#!/usr/bin/env python3
"""Small stdlib-only helper for immutable Dokploy deployments and QA schedules."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

IMAGE_RE = re.compile(
    r"^ghcr\.io/theriark/nowlert-ce@sha256:[0-9a-f]{64}$"
)
TERMINAL_FAILURE = {"error", "failed", "failure", "cancelled", "canceled"}
TERMINAL_SUCCESS = {"done", "success", "succeeded", "completed", "complete"}


class DokployError(RuntimeError):
    pass


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise DokployError(f"Required environment variable {name} is missing")
    return value


def api_url(path: str, query: dict[str, str] | None = None) -> str:
    base = required_env("DOKPLOY_URL").rstrip("/")
    url = f"{base}/api/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    return url


def request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
    timeout: int = 30,
) -> Any:
    data = None
    headers = {
        "accept": "application/json",
        "x-api-key": required_env("DOKPLOY_API_KEY"),
    }
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        api_url(path, query), data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise DokployError(
            f"Dokploy API {method} {path} failed with HTTP {exc.code}: {body[:1000]}"
        ) from exc
    except TimeoutError as exc:
        raise DokployError(
            f"Dokploy API {method} {path} timed out after {timeout} seconds"
        ) from exc
    except urllib.error.URLError as exc:
        raise DokployError(f"Dokploy API {method} {path} failed: {exc}") from exc

    if not body.strip():
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def find_key(value: Any, key: str) -> Any | None:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            result = find_key(child, key)
            if result is not None:
                return result
    elif isinstance(value, list):
        for child in value:
            result = find_key(child, key)
            if result is not None:
                return result
    return None


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(flatten_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


def deployment_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            if any(key in item for key in ("deploymentId", "id")) and any(
                key in item for key in ("status", "createdAt", "finishedAt", "startedAt")
            ):
                records.append(item)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    unique: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = str(record.get("deploymentId") or record.get("id") or "")
        if identifier:
            unique[identifier] = record
    return list(unique.values())


def record_id(record: dict[str, Any]) -> str:
    return str(record.get("deploymentId") or record.get("id") or "")


def record_status(record: dict[str, Any]) -> str:
    return str(record.get("status") or "").strip().lower()


def record_sort_key(record: dict[str, Any]) -> str:
    return str(
        record.get("createdAt")
        or record.get("startedAt")
        or record.get("finishedAt")
        or record_id(record)
    )


def write_output(name: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def validate_image(image: str, *, allow_mutable: bool = False) -> None:
    if allow_mutable:
        if not image or any(character.isspace() for character in image):
            raise DokployError("Rollback image reference is empty or invalid")
        return
    if not IMAGE_RE.fullmatch(image):
        raise DokployError(
            "Image must be an immutable Nowlert GHCR reference ending in "
            "@sha256:<64 lowercase hexadecimal characters>"
        )


def current_image(application_id: str) -> str:
    response = request_json(
        "GET", "application.one", query={"applicationId": application_id}
    )
    image = find_key(response, "dockerImage")
    if not isinstance(image, str) or not image.strip():
        raise DokployError(
            f"Could not read dockerImage for Dokploy application {application_id}"
        )
    return image.strip()


def wait_health(
    url: str,
    timeout_seconds: int,
    *,
    expected_version: str = "",
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = "health endpoint did not respond"
    consecutive_matches = 0

    while time.monotonic() < deadline:
        request = urllib.request.Request(
            url,
            headers={"accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read().decode("utf-8", errors="replace")
                status_code = response.status
            payload = json.loads(body)
            observed_version = str(payload.get("version") or "").strip()
            healthy = status_code == 200 and payload.get("status") == "ok"

            if not healthy:
                consecutive_matches = 0
                last_error = f"HTTP {status_code}: {body[:500]}"
            elif expected_version and observed_version != expected_version:
                consecutive_matches = 0
                last_error = (
                    f"healthy response is still version {observed_version or 'unknown'}; "
                    f"waiting for {expected_version}"
                )
                print(f"WAIT: {url} {last_error}")
            else:
                consecutive_matches += 1
                if consecutive_matches >= 2:
                    print(
                        f"PASS: {url} returned two consecutive HTTP 200 "
                        f"status=ok responses version={observed_version or 'unknown'}"
                    )
                    return
                last_error = (
                    f"received first matching healthy response version="
                    f"{observed_version or 'unknown'}; confirming"
                )
                print(f"WAIT: {url} {last_error}")
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            json.JSONDecodeError,
            TimeoutError,
        ) as exc:
            consecutive_matches = 0
            last_error = str(exc)
        time.sleep(5)

    expected = f" version={expected_version}" if expected_version else ""
    raise DokployError(
        f"Health check timed out for {url}{expected}: {last_error}"
    )


def deploy(args: argparse.Namespace) -> None:
    validate_image(args.image, allow_mutable=args.allow_mutable)
    previous = current_image(args.application_id)
    write_output("previous_image", previous)
    write_output("deployed_image", args.image)

    if previous == args.image and args.noop_ok:
        print(f"No image change required for {args.application_id}: {args.image}")
    else:
        request_json(
            "POST",
            "application.update",
            payload={"applicationId": args.application_id, "dockerImage": args.image},
        )
        request_json(
            "POST",
            "application.deploy",
            payload={
                "applicationId": args.application_id,
                "title": args.title,
                "description": args.description,
            },
        )
        print(f"Deployment requested for {args.application_id}: {args.image}")

    wait_health(
        args.health_url,
        args.timeout,
        expected_version=args.expected_version,
    )
    observed = current_image(args.application_id)
    if observed != args.image:
        raise DokployError(
            f"Dokploy application {args.application_id} reports {observed}, expected {args.image}"
        )
    print(f"PASS: Dokploy application image is exactly {observed}")


def assert_image(args: argparse.Namespace) -> None:
    validate_image(args.image)
    observed = current_image(args.application_id)
    if observed != args.image:
        raise DokployError(
            f"Application {args.application_id} runs {observed}, expected {args.image}"
        )
    print(f"PASS: {args.application_id} runs {observed}")


def promotion_smoke(args: argparse.Namespace) -> None:
    """Passively verify a promoted image without submitting notification events."""
    validate_image(args.image)
    marker = args.success_marker.strip()
    if not marker:
        raise DokployError("Promotion smoke success marker must not be empty")

    wait_health(
        args.health_url,
        args.timeout,
        expected_version=args.expected_version,
    )
    observed = current_image(args.application_id)
    if observed != args.image:
        raise DokployError(
            f"Dokploy application {args.application_id} reports {observed}, expected {args.image}"
        )

    print(f"PASS: passive promotion smoke confirmed exact image {observed}")
    print("PASS: notification delivery tests disabled for this promotion smoke")
    print(marker)


def list_schedule_deployments(schedule_id: str) -> list[dict[str, Any]]:
    response = request_json(
        "GET",
        "deployment.allByType",
        query={"id": schedule_id, "type": "schedule"},
    )
    return deployment_records(response)


def read_deployment_logs(deployment_id: str) -> str:
    response = request_json(
        "GET",
        "deployment.readLogs",
        query={"deploymentId": deployment_id, "tail": "10000"},
    )
    return flatten_text(response)


def run_schedule(args: argparse.Namespace) -> None:
    before = {record_id(record) for record in list_schedule_deployments(args.schedule_id)}
    trigger = request_json(
        "POST",
        "schedule.runManually",
        payload={"scheduleId": args.schedule_id},
        timeout=args.timeout,
    )
    deployment_id = find_key(trigger, "deploymentId")
    if deployment_id is not None:
        deployment_id = str(deployment_id)

    deadline = time.monotonic() + args.timeout
    terminal_success_seen: float | None = None
    last_logs = ""

    while time.monotonic() < deadline:
        records = list_schedule_deployments(args.schedule_id)
        if not deployment_id:
            candidates = [record for record in records if record_id(record) not in before]
            if candidates:
                candidates.sort(key=record_sort_key, reverse=True)
                deployment_id = record_id(candidates[0])
                write_output("deployment_id", deployment_id)
                print(
                    f"Detected schedule deployment {deployment_id} for {args.schedule_id}"
                )

        if deployment_id:
            matching = next(
                (record for record in records if record_id(record) == deployment_id), None
            )
            status = record_status(matching or {})
            try:
                last_logs = read_deployment_logs(deployment_id)
            except DokployError:
                last_logs = last_logs

            if args.success_marker in last_logs:
                print(last_logs[-8000:])
                print(
                    f"PASS: schedule {args.schedule_id} emitted marker: "
                    f"{args.success_marker}"
                )
                write_output("deployment_id", deployment_id)
                return

            if status in TERMINAL_FAILURE:
                print(last_logs[-8000:])
                raise DokployError(
                    f"Schedule {args.schedule_id} deployment {deployment_id} ended with {status}"
                )

            if status in TERMINAL_SUCCESS:
                if terminal_success_seen is None:
                    terminal_success_seen = time.monotonic()
                elif time.monotonic() - terminal_success_seen >= 30:
                    print(last_logs[-8000:])
                    raise DokployError(
                        f"Schedule {args.schedule_id} completed without required marker "
                        f"{args.success_marker!r}"
                    )

        time.sleep(10)

    if last_logs:
        print(last_logs[-8000:])
    raise DokployError(
        f"Timed out waiting for schedule {args.schedule_id} marker "
        f"{args.success_marker!r}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy")
    deploy_parser.add_argument("--application-id", required=True)
    deploy_parser.add_argument("--image", required=True)
    deploy_parser.add_argument("--health-url", required=True)
    deploy_parser.add_argument("--title", default="Immutable image deployment")
    deploy_parser.add_argument("--description", default="Managed by GitHub Actions")
    deploy_parser.add_argument("--timeout", type=int, default=600)
    deploy_parser.add_argument("--expected-version", default="")
    deploy_parser.add_argument("--allow-mutable", action="store_true")
    deploy_parser.add_argument("--noop-ok", action="store_true")
    deploy_parser.set_defaults(func=deploy)

    assert_parser = subparsers.add_parser("assert-image")
    assert_parser.add_argument("--application-id", required=True)
    assert_parser.add_argument("--image", required=True)
    assert_parser.set_defaults(func=assert_image)

    smoke_parser = subparsers.add_parser("promotion-smoke")
    smoke_parser.add_argument("--application-id", required=True)
    smoke_parser.add_argument("--image", required=True)
    smoke_parser.add_argument("--health-url", required=True)
    smoke_parser.add_argument("--expected-version", required=True)
    smoke_parser.add_argument("--success-marker", required=True)
    smoke_parser.add_argument("--timeout", type=int, default=300)
    smoke_parser.set_defaults(func=promotion_smoke)

    schedule_parser = subparsers.add_parser("run-schedule")
    schedule_parser.add_argument("--schedule-id", required=True)
    schedule_parser.add_argument("--success-marker", required=True)
    schedule_parser.add_argument("--timeout", type=int, default=3600)
    schedule_parser.set_defaults(func=run_schedule)

    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except DokployError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
