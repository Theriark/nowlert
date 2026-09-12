"""Regression test for Cloudflare-compatible deployment health polling."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".github" / "scripts" / "dokploy_release.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("nowlert_dokploy_release", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_health_polling_uses_theriark_user_agent() -> None:
    helper = load_helper()
    source = inspect.getsource(helper.wait_health)

    assert '"User-Agent": "Theriark-GitHub-Actions/1.0"' in source
