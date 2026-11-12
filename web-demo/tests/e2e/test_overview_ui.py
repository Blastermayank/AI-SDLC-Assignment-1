"""Overview, navigation, health badge, repository link and methodology (US4; task T042)."""

import dataclasses

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import open_section

pytestmark = pytest.mark.e2e

ROUTES = ["overview", "methodology", "part-1a", "part-1b", "evaluation", "evidence"]


def test_default_route_shows_only_overview(page):
    page.goto("/")
    expect(page.locator("#section-overview")).to_be_visible()
    for route in ROUTES[1:]:
        expect(page.locator(f"#section-{route}")).to_be_hidden()


def test_navigation_switches_sections(page):
    page.goto("/")
    for route in ROUTES:
        page.click(f".nav-list a[data-route='{route}']")
        expect(page.locator(f"#section-{route}")).to_be_visible()
        expect(page.locator(f".nav-list a[data-route='{route}']")).to_have_attribute(
            "aria-current", "page"
        )
        assert page.locator("main section.view:visible").count() == 1


def test_health_badge_reports_missing_key(page, no_key):
    page.goto("/")
    expect(page.locator("#health-badge")).to_contain_text("Gemini not configured")


def test_repository_link_states(page, live_server):
    # Both states are set here, so the test does not depend on the real portal-config.json.
    original = live_server.app.state.settings
    url = "https://github.com/example-owner/example-repo"
    try:
        live_server.app.state.settings = dataclasses.replace(original, repository_url=None)
        page.goto("/")
        expect(page.locator("#repo-link")).to_have_text("Repository link not configured")

        live_server.app.state.settings = dataclasses.replace(original, repository_url=url)
        page.reload()
        expect(page.locator("#repo-link a")).to_have_attribute("href", url)
        expect(page.locator("#overview-repo-link a")).to_have_text(url)
    finally:
        live_server.app.state.settings = original


def test_methodology_marks_missing_and_links_present_artifacts(page):
    open_section(page, "methodology")
    missing = page.locator("#section-methodology [data-evidence-id='1a-plan']")
    expect(missing).to_contain_text("not in repository")
    present = page.locator("#section-methodology a[data-evidence-id='1a-spec']").first
    expect(present).to_be_visible()
    present.click()
    expect(page.locator("#section-evidence")).to_be_visible()
    expect(page.locator("#evd-viewer")).to_contain_text("Part-1A/speckit.specify.md")
