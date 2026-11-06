"""Evidence browser in Edge (User Story 5; task T047)."""

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import open_section

pytestmark = pytest.mark.e2e


def test_three_groups_are_shown(page):
    open_section(page, "evidence")
    expect(page.locator("#evd-groups .evidence-group")).to_have_count(3)


def test_dataset_opens_with_metadata_and_literal_markup(page):
    open_section(page, "evidence")
    page.click("#evd-groups button[data-evidence-id='1b-dataset']")
    viewer = page.locator("#evd-viewer")
    expect(viewer).to_contain_text("Part-1B/evals/dataset.json")
    expect(viewer).to_contain_text("SHA-256")
    expect(viewer.locator("pre")).to_contain_text('"expected_vuln"')
    expect(viewer.locator("pre")).to_contain_text("<div>{user_input}</div>")
    assert viewer.locator("pre div").count() == 0
    expect(page.locator("#evd-groups button[data-evidence-id='1b-dataset']")).to_have_attribute(
        "aria-pressed", "true"
    )


def test_filter_narrows_the_list(page):
    open_section(page, "evidence")
    page.fill("#evd-filter", "limiter")
    visible = page.locator("#evd-groups .evidence-item:visible")
    expect(visible.first).to_be_visible()
    for index in range(visible.count()):
        expect(visible.nth(index)).to_contain_text("limiter", ignore_case=True)
