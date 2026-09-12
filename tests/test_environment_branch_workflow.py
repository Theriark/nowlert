"""Environment branch and immutable CE promotion contracts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return (
        ROOT / ".github" / "workflows" / name
    ).read_text(encoding="utf-8")


def test_environment_branch_and_immutable_promotion_contract():
    ci = workflow("ci.yml")
    development = workflow("docker-development.yml")
    stage = workflow("promote-stage.yml")
    finalization = workflow("finalize-release.yml")
    release = workflow("docker-release.yml")

    assert "- development" in ci
    assert "- main" in ci

    assert "workflow_run:" not in development
    assert "refs/heads/development" in development
    assert "ghcr.io/theriark/nowlert-ce" in development
    assert ":development" in development

    assert "contents: write" in stage
    assert "refs/heads/development" in stage
    assert "refs/heads/stage" in stage
    assert "force=false" in stage
    assert "force=true" not in stage
    assert "Waiting for stage ref propagation" in stage
    assert "cannot fast-forward" in stage

    assert not (ROOT / ".github" / "workflows" / "promote-production-reference.yml").exists()

    assert "refs/heads/main" in finalization
    assert "refs/remotes/origin/main" in finalization
    assert "refs/remotes/origin/stage" in finalization
    assert "is not current main" in finalization
    assert "does not match Stage-approved source" in finalization
    assert "production_reference_run_id" not in finalization
    assert "CE_PRODREF_APPLICATION_ID" not in finalization

    assert "docker/build-push-action" not in release
    assert "skopeo copy --all --preserve-digests" in release
    assert "Image rebuild performed: no" in release
