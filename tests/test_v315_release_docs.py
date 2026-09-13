"""Current Nowlert CE v3.1.5 release/documentation contract."""

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


def test_v315_release_identity_is_consistent():
    assert VERSION == "3.1.5"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.5.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "v3.1.5-qa-checklist.md").read_text(encoding="utf-8")
    assert "stable-v3.1.5-F4C542" in readme
    assert "**Current Stable Release** | **v3.1.5**" in readme
    assert "current stable release is **v3.1.5**" in dockerhub.casefold()
    assert "theriark/nowlert-ce:3.1.5" in dockerhub
    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.5" in environment
    assert "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.5}" in compose
    assert release.startswith("# Nowlert CE v3.1.5 release notes")
    assert checklist.startswith("# Nowlert CE v3.1.5 QA checklist")


def test_v315_approved_visual_baseline_is_packaged_and_referenced():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    for filename in CURRENT_SCREENSHOTS:
        path = ROOT / "docs" / "images" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in readme or filename in webui
        assert filename in docs_index
    assert "does not introduce a visual redesign" in " ".join(docs_index.split())


def test_v315_consolidated_guide_batch_is_packaged():
    guide_index = (ROOT / "docs" / "guides" / "README.md").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "integrations" / "README.md").is_file()
    for filename in CURRENT_GUIDES:
        path = ROOT / "docs" / "guides" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in guide_index
        text = path.read_text(encoding="utf-8")
        for forbidden in ("\noutputs:\n", "\nrouting:\n", "\napi:\n  tokens:\n"):
            assert forbidden not in text, filename


def test_v315_release_safety_contract():
    finalizer = (ROOT / ".github" / "workflows" / "finalize-release.yml").read_text(encoding="utf-8")
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(encoding="utf-8")
    assert '[[ "${VERSION}" == "v${SOURCE_VERSION}" ]]' in finalizer
    assert "Release tag ${VERSION} does not match source version" in finalizer
    assert 'docs/releases/${VERSION}.md' in finalizer
    assert 'docs/${VERSION}-qa-checklist.md' in finalizer
    assert "refs/remotes/origin/stage" in finalizer
    assert "does not match Stage-approved source" in finalizer
    assert "production_reference_run_id" not in finalizer
    assert "skopeo copy --all --preserve-digests" in finalizer
    assert "Verify all stable aliases use the approved digest" in finalizer
    assert "-F force=true" not in stage
    assert "-F force=false" in stage
    assert "Waiting for stage ref propagation" in stage
    assert "cannot fast-forward" in stage


def test_v315_documentation_validator_tracks_current_release():
    validator = (ROOT / "tools" / "validate_current_documentation.py").read_text(encoding="utf-8")
    assert 'ROOT / "docs" / "releases" / "v3.1.5.md"' in validator
    assert 'ROOT / "docs" / "v3.1.5-qa-checklist.md"' in validator
    assert "stable-v3.1.5-F4C542" in validator
    assert 'VERSION = "3.1.5"' in validator
    assert 'version="v3.1.5"' in validator
    assert "promote-production-reference.yml" not in validator


def test_v315_deployment_docs_contain_stage_final_promotion_chain():
    deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.5.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "v3.1.5-qa-checklist.md").read_text(encoding="utf-8")
    normalized = " ".join(deployment.split()).casefold()
    assert "gh workflow run promote-stage.yml" in deployment
    assert "gh workflow run finalize-release.yml" in deployment
    assert "gh workflow run docker-release.yml" not in deployment
    assert "promote-production-reference.yml" not in deployment
    assert "production reference" not in release.casefold()
    assert "production reference" not in checklist.casefold()
    assert "development -> stage -> main -> release" in normalized
    assert 'version="v3.1.5"' in deployment
    assert "ghcr.io/theriark/nowlert-ce:3.1.5" in deployment
    assert "docker.io/theriark/nowlert-ce:3.1.5" in deployment
    assert "no image rebuild" in normalized
    assert "there is no additional ce dokploy `production` deployment workflow" in normalized
