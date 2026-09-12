"""Current Nowlert CE v3.1.4 release/documentation contract."""

from pathlib import Path

from version import VERSION


ROOT = Path(__file__).resolve().parents[1]
CURRENT_SCREENSHOTS = (
    "v3.1.0-dashboard.png",
    "v3.1.0-routing-flow.png",
    "v3.1.0-destinations.png",
    "v3.1.0-delivery-history.png",
    "v3.1.0-discord-xen-orchestra.png",
    "v3.1.0-teams-xen-orchestra.png",
)
CURRENT_GUIDES = (
    "xen-orchestra-to-discord.md",
    "xen-orchestra-to-teams.md",
    "centralise-homelab-smtp-alerts.md",
    "dell-idrac-redfish-routing.md",
    "zabbix-webhook-to-discord.md",
)


def test_v314_release_identity_is_consistent():
    assert VERSION == "3.1.4"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.4.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.4-qa-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "stable-v3.1.4-F4C542" in readme
    assert "**Current Stable Release** | **v3.1.4**" in readme
    assert "current stable release is **v3.1.4**" in dockerhub.casefold()
    assert "theriark/nowlert-ce:3.1.4" in dockerhub
    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.4" in environment
    assert "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.4}" in compose
    assert release.startswith("# Nowlert CE v3.1.4 release notes")
    assert checklist.startswith("# Nowlert CE v3.1.4 QA checklist")


def test_v314_approved_visual_baseline_is_packaged_and_referenced():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    for filename in CURRENT_SCREENSHOTS:
        path = ROOT / "docs" / "images" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in readme or filename in webui
        assert filename in docs_index

    normalized_index = " ".join(docs_index.split())
    assert "does not introduce a visual redesign" in normalized_index


def test_v314_consolidated_guide_batch_is_packaged():
    guide_index = (ROOT / "docs" / "guides" / "README.md").read_text(
        encoding="utf-8"
    )
    integration_index = ROOT / "docs" / "integrations" / "README.md"

    assert integration_index.is_file()
    for filename in CURRENT_GUIDES:
        path = ROOT / "docs" / "guides" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in guide_index

    for forbidden in ("\noutputs:\n", "\nrouting:\n", "\napi:\n  tokens:\n"):
        for filename in CURRENT_GUIDES:
            text = (ROOT / "docs" / "guides" / filename).read_text(
                encoding="utf-8"
            )
            assert forbidden not in text, filename


def test_v314_release_safety_contract():
    finalizer = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )

    assert '[[ "${VERSION}" == "v${SOURCE_VERSION}" ]]' in finalizer
    assert "Release tag ${VERSION} does not match source version" in finalizer
    assert 'docs/releases/${VERSION}.md' in finalizer
    assert 'docs/${VERSION}-qa-checklist.md' in finalizer
    assert "refs/remotes/origin/stage" in finalizer
    assert "does not match Stage-approved source" in finalizer
    assert "production_reference_run_id" not in finalizer

    assert "-F force=true" not in stage
    assert "-F force=false" in stage
    assert "Waiting for stage ref propagation" in stage
    assert "cannot fast-forward" in stage


def test_v314_deployment_docs_contain_stage_final_promotion_chain():
    deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.4.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.4-qa-checklist.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(deployment.split()).casefold()

    for workflow in (
        "promote-stage.yml",
        "finalize-release.yml",
        "docker-release.yml",
    ):
        assert f"gh workflow run {workflow}" in deployment

    assert "promote-production-reference.yml" not in deployment
    assert "production reference" not in release.casefold()
    assert "production reference" not in checklist.casefold()
    assert "development -> stage -> main -> release" in normalized
    assert 'version="v3.1.4"' in deployment
    assert 'tag="v3.1.4"' in deployment
    assert "ghcr.io/theriark/nowlert-ce:3.1.4" in deployment
    assert "docker.io/theriark/nowlert-ce:3.1.4" in deployment
    assert "image rebuild is performed from the release tag" in normalized
    assert "there is no additional ce dokploy `production` deployment workflow" in normalized
