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

    assert "- development" in ci
    assert "- main" in ci

    # A successful push CI on development must call the Development Image
    # workflow automatically. Manual dispatch remains available for recovery.
    assert "needs: tests" in ci
    assert "uses: ./.github/workflows/docker-development.yml" in ci
    assert "github.event_name == 'push'" in ci
    assert "github.ref == 'refs/heads/development'" in ci
    assert "secrets: inherit" in ci
    assert "workflow_call:" in development
    assert "workflow_dispatch:" in development
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

    assert "environment: stage" in finalization
    assert "contents: write" in finalization
    assert "packages: write" in finalization
    assert "refs/heads/main" in finalization
    assert "refs/remotes/origin/main" in finalization
    assert "refs/remotes/origin/stage" in finalization
    assert "is not current main" in finalization
    assert "does not match Stage-approved source" in finalization
    assert "production_reference_run_id" not in finalization
    assert "CE_PRODREF_APPLICATION_ID" not in finalization
    assert "CE_RELEASE_TOKEN" not in finalization
    assert "GH_TOKEN: ${{ github.token }}" in finalization

    # Finalize CE Release is the only stable publication workflow. It must
    # reuse the Stage-approved digest, publish both registries, and verify all
    # aliases without rebuilding the image.
    assert not (ROOT / ".github" / "workflows" / "docker-release.yml").exists()
    assert "docker/build-push-action" not in finalization
    assert "docker/login-action@v4" in finalization
    assert "DOCKERHUB_USERNAME" in finalization
    assert "DOCKERHUB_TOKEN" in finalization
    assert "skopeo copy --all --preserve-digests" in finalization
    assert 'ghcr.io/theriark/nowlert-ce:${RELEASE_VERSION}' in finalization
    assert "ghcr.io/theriark/nowlert-ce:latest" in finalization
    assert 'docker.io/theriark/nowlert-ce:${RELEASE_VERSION}' in finalization
    assert "docker.io/theriark/nowlert-ce:latest" in finalization
    assert "Verify all stable aliases use the approved digest" in finalization
    assert "Image rebuild performed: no" in finalization
