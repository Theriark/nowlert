"""v3.1.0 brand asset and immutable deployment readiness gates."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from formatters.presentation import PresentationMixin
from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]
BRAND_ROUTE = "/ui/brand/nowlert-owl-v3.1.0.png"
BRAND_SHA256 = "684bda33be520811ab80057da41c34112ffc58ee7a559ffd66ba3f02b92f052a"


class Configuration:
    @staticmethod
    def get(*_keys, default=None):
        return default


def png_metadata(path: Path):
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height, depth, color_type, compression, filter_method, interlace = (
        struct.unpack(">IIBBBBB", data[16:29])
    )
    return data, (
        width,
        height,
        depth,
        color_type,
        compression,
        filter_method,
        interlace,
    )


def test_approved_owl_assets_are_exact_versioned_rgba_pngs():
    paths = (
        ROOT / "assets" / "icons" / "nowlert.png",
        ROOT / "assets" / "icons" / "discord" / "nowlert-owl-v3.1.0.png",
    )
    for path in paths:
        data, metadata = png_metadata(path)
        assert hashlib.sha256(data).hexdigest() == BRAND_SHA256
        assert metadata[:4] == (256, 256, 8, 6)


def test_webui_uses_cache_busted_approved_owl_everywhere():
    service = WebUIService(Configuration(), root=ROOT)
    index = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    qa_patch = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "src" / "webui" / "dashboard.js").read_text(encoding="utf-8")

    assert service.assets[BRAND_ROUTE] == (
        "assets/icons/nowlert.png",
        "image/png",
        "public, max-age=31536000, immutable",
    )
    assert service.assets["/ui/icon.png"][2] == "no-cache"
    assert index.count(BRAND_ROUTE) >= 3
    assert "/ui/icon.png" not in index
    assert f'GENERIC_SOURCE_ICON = "{BRAND_ROUTE}"' in app
    assert f'const ICON_PATH = "{BRAND_ROUTE}"' in qa_patch
    assert f'icon.src = "{BRAND_ROUTE}"' in dashboard


def test_discord_generic_product_uses_versioned_owl_attachment():
    assert (
        PresentationMixin.DISCORD_PRODUCT_ICONS["nowlert"]
        == "discord/nowlert-owl-v3.1.0.png"
    )
    assert (
        PresentationMixin()._discord_product_icon_url("nowlert")
        == "nowlert-asset://discord/nowlert-owl-v3.1.0.png"
    )


def test_deployment_workflows_wait_for_the_source_version():
    helper = (ROOT / ".github" / "scripts" / "dokploy_release.py").read_text(
        encoding="utf-8"
    )
    development = (
        ROOT / ".github" / "workflows" / "docker-development.yml"
    ).read_text(encoding="utf-8")
    stage = (
        ROOT / ".github" / "workflows" / "promote-stage.yml"
    ).read_text(encoding="utf-8")

    assert 'deploy_parser.add_argument("--expected-version", default="")' in helper
    assert "expected_version=args.expected_version" in helper
    assert "consecutive_matches >= 2" in helper
    assert "healthy response is still version" in helper
    assert "Verify Development image version and approved owl" in development
    assert BRAND_SHA256 in development
    assert '--expected-version "${EXPECTED_VERSION}"' in development
    assert '--expected-version "${EXPECTED_VERSION}"' in stage
    assert not (ROOT / ".github" / "workflows" / "promote-production-reference.yml").exists()
