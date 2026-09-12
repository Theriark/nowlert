"""Regression contract for keeping one WebUI renderer from blanking every view."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "webui" / "app.js"


def test_render_all_isolates_component_failures_and_continues_rendering():
    script = APP.read_text(encoding="utf-8")

    start = script.index("function renderAll()")
    end = script.index("\nfunction renderWorkspaceErrors()", start)
    render_all = script[start:end]

    assert "const renderers = [" in render_all
    for component in (
        "Notices",
        "Dashboard",
        "Sources",
        "Destinations",
        "Routes",
        "Event API tokens",
        "Delivery history",
        "Audit log",
        "Users",
        "Backups",
        "Backup destinations",
        "Configuration",
        "Health checks",
        "Backup settings",
        "Updates",
        "Preferences",
        "Integration settings",
        "Language",
    ):
        assert f'["{component}",' in render_all

    assert "for (const [component, renderer] of renderers)" in render_all
    assert "try {" in render_all
    assert "renderer();" in render_all
    assert "catch (error)" in render_all
    assert "state.workspaceErrors.push" in render_all
    assert "WebUI rendering failed" in render_all

    # The workspace alert is refreshed only after every renderer had a chance
    # to run, so a Dashboard failure cannot prevent Sources/Destinations/etc.
    loop_position = render_all.index("for (const [component, renderer] of renderers)")
    alert_position = render_all.rindex("renderWorkspaceErrors();")
    assert loop_position < alert_position
