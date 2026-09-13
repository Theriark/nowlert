"""Release metadata invariants for Nowlert CE v3.1.5."""

import json
from pathlib import Path

from version import EDITION, EDITION_SLUG, REPOSITORY, VERSION


ROOT = Path(__file__).resolve().parents[1]
CURRENT_RELEASE_GUIDES = (
    "docs/current-configuration-model.md",
    "docs/data-portability.md",
    "docs/database-authoritative-resources.md",
    "docs/integrations-and-inputs.md",
    "docs/platform-api.md",
    "docs/platform-outputs.md",
    "docs/platform-routing.md",
    "docs/platform-state.md",
    "docs/presentation-contract.md",
    "docs/smtp-security.md",
    "docs/webui.md",
)


def test_application_version_and_repository_are_current():
    assert VERSION == "3.1.5"
    assert EDITION == "Community Edition"
    assert EDITION_SLUG == "ce"
    assert REPOSITORY == "https://github.com/Theriark/nowlert-ce"


def test_public_enterprise_release_manifest_is_valid():
    manifest = json.loads(
        (ROOT / "release-manifests" / "nowlert-ee.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["edition"] == "ee"
    assert manifest["version"] == "3.0.0"
    assert "release_url" in manifest


def test_readme_release_metadata_is_current():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "stable-v3.1.5-F4C542" in readme
    assert "| **Current Stable Release** | **v3.1.5** |" in readme
    assert "https://github.com/Theriark/nowlert-ce/releases" in readme
    assert "stable-v3.1.4-F4C542" not in readme


def test_changelog_preserves_release_history():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    # Documentation/release-engineering patch records are authoritative in
    # docs/releases/. Preserve the existing historical changelog order.
    assert "## 3.1.2 - 2026-08-20" in changelog
    assert "## 3.1.1 - 2026-08-14" in changelog
    assert "## 3.1.0 - 2026-08-08" in changelog
    assert "## 3.0.0 - 2026-07-29" in changelog
    assert "## 2.5.5 - 2026-07-27" in changelog
    assert changelog.index("## Unreleased") < changelog.index("## 3.1.2")
    assert changelog.index("## 3.1.2") < changelog.index("## 3.1.1")
    assert changelog.index("## 3.1.1") < changelog.index("## 3.1.0")
    assert changelog.index("## 3.1.0") < changelog.index("## 3.0.0")


def test_unchanged_runtime_guides_remain_on_v312_contract():
    """v3.1.5 does not change the runtime contracts documented from v3.1.2."""

    for relative in CURRENT_RELEASE_GUIDES:
        document = (ROOT / relative).read_text(encoding="utf-8")
        assert "Nowlert v3.1.2" in document, relative
        assert "Nowlert v3.1.1" not in document, relative


def test_historical_v300_v310_v311_v312_v313_and_v314_documents_remain_historical():
    v300_notes = ROOT / "docs" / "releases" / "v3.0.0.md"
    v300_checklist = ROOT / "docs" / "v3.0.0-acceptance-checklist.md"
    v310_notes = ROOT / "docs" / "releases" / "v3.1.0.md"
    v311_notes = ROOT / "docs" / "releases" / "v3.1.1.md"
    v311_checklist = ROOT / "docs" / "releases" / "v3.1.1-qa-checklist.md"
    v312_notes = ROOT / "docs" / "releases" / "v3.1.2.md"
    v312_checklist = ROOT / "docs" / "v3.1.2-qa-checklist.md"
    v313_notes = ROOT / "docs" / "releases" / "v3.1.3.md"
    v313_checklist = ROOT / "docs" / "v3.1.3-qa-checklist.md"
    v314_notes = ROOT / "docs" / "releases" / "v3.1.4.md"
    v314_checklist = ROOT / "docs" / "v3.1.4-qa-checklist.md"
    docker_hub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")

    assert v300_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.0.0 release notes"
    )
    assert v300_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.0.0 acceptance checklist"
    )
    assert v310_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert v3.1.0 release notes"
    )
    assert v311_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.1 release notes"
    )
    assert v311_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.1 QA checklist"
    )
    assert v312_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.2 release notes"
    )
    assert v312_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.2 QA checklist"
    )
    assert v313_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.3 release notes"
    )
    assert v313_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.3 QA checklist"
    )
    assert v314_notes.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.4 release notes"
    )
    assert v314_checklist.read_text(encoding="utf-8").startswith(
        "# Nowlert CE v3.1.4 QA checklist"
    )
    assert "current stable release is **v3.1.5**" in docker_hub.casefold()
    assert "theriark/nowlert-ce:3.1.5" in docker_hub


def test_historical_v255_release_identity_is_preserved():
    notes = (ROOT / "docs" / "releases" / "v2.5.5.md").read_text(
        encoding="utf-8"
    )

    assert notes.startswith("# Nowlert v2.5.5 release notes")


def test_quick_starts_prepare_platform_state():
    for path in (ROOT / "README.md", ROOT / "DOCKERHUB_README.md"):
        document = path.read_text(encoding="utf-8")

        assert "mkdir -p logs/emails secrets state" in document
        assert "chmod 700 logs logs/emails secrets state" in document


def test_production_defaults_are_versioned_and_compatible():
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.5" in environment
    assert "theriark/nowlert-ce:3.1.5" in compose
    assert "NOWLERT_IMAGE" in compose
    assert "NOWLERT_EXTERNAL_BACKUP_DIR" in compose
    assert "/nowlert/external-backups" in compose


def test_release_notes_cover_v315_compatibility_and_rollback():
    notes = (ROOT / "docs" / "releases" / "v3.1.5.md").read_text(
        encoding="utf-8"
    )

    for heading in (
        "## Highlights",
        "## Compatibility",
        "## Upgrade from v3.1.4",
        "## Rollback",
    ):
        assert heading in notes

    assert "schema **9**" in notes
    assert "platform_database_v1" in notes
    assert "without rebuild" in notes.casefold()


def test_release_workflow_is_guarded_and_reuses_approved_image():
    finalization = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )

    assert "final_image:" in finalization
    assert "skopeo copy --all --preserve-digests" in finalization
    assert 'docker://ghcr.io/theriark/nowlert-ce:${RELEASE_VERSION}' in finalization
    assert 'docker://docker.io/theriark/nowlert-ce:${RELEASE_VERSION}' in finalization
    assert "docker/build-push-action" not in finalization

    assert '--title "Nowlert CE ${VERSION}"' in finalization
    assert 'gh release create "${VERSION}"' in finalization
    assert "Release finalization must be launched from main" in finalization
    assert '[[ "${VERSION}" == "v${SOURCE_VERSION}" ]]' in finalization
    assert "Release tag ${VERSION} does not match source version" in finalization
    assert 'docs/releases/${VERSION}.md' in finalization
    assert 'docs/${VERSION}-qa-checklist.md' in finalization
    assert "refs/remotes/origin/stage" in finalization
    assert "production_reference_run_id" not in finalization

    assert "-F force=false" in stage
    assert "-F force=true" not in stage
    assert "Waiting for stage ref propagation" in stage

    assert "fortpt/nowlert:" not in finalization
    assert "ghcr.io/fortpt/nowlert:" not in finalization


def test_release_workflows_use_current_action_majors():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    finalization = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")

    assert "actions/checkout@v7" in ci
    assert "actions/setup-python@v7" in ci
    assert "actions/setup-node@v7" in ci

    assert "actions/checkout@v7" in finalization
    assert "docker/login-action@v4" in finalization
    assert "docker/setup-buildx-action" not in finalization
    assert "docker/build-push-action" not in finalization
    assert "skopeo copy --all --preserve-digests" in finalization


def test_development_workflow_targets_only_ce():
    workflow = (
        ROOT / ".github" / "workflows" / "docker-development.yml"
    ).read_text(encoding="utf-8")

    assert "IMAGE: ghcr.io/theriark/nowlert-ce" in workflow
    assert "environment: development" in workflow
    assert "DOKPLOY_CE_DEVELOPMENT_APPLICATION_ID" in workflow
    assert "DOKPLOY_EE_DEVELOPMENT_APPLICATION_ID" not in workflow
