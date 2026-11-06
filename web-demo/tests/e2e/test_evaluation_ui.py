"""Evaluation dashboard in Edge (User Story 3, SC-006; task T037)."""

import json

import pytest
from playwright.sync_api import expect

from tests.conftest import REPO_ROOT
from tests.e2e.conftest import open_section

pytestmark = pytest.mark.e2e

EVIDENCE = REPO_ROOT / "Part-1B" / "evidence"


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8-sig"))


def test_current_report_summary_matches_file(page):
    current = load("eval-results.json")
    open_section(page, "evaluation")
    summary = page.locator("#ev-summary")
    expect(summary).to_contain_text(current["model"])
    expect(summary).to_contain_text(current["status"])
    expect(summary).to_contain_text(f"{current['completed_cases']} / {current['total_cases']}")
    expect(page.locator("#ev-cases tr.case-row")).to_have_count(len(current["results"]))


def test_history_lists_every_saved_report_with_caveat(page):
    open_section(page, "evaluation")
    saved = list(EVIDENCE.glob("eval-results*.json"))
    expect(page.locator("#ev-history tr.history-run")).to_have_count(len(saved))
    expect(page.locator("#ev-history")).to_contain_text("not directly comparable")


def test_reference_run_shows_86_7_and_cases_3_and_8(page):
    open_section(page, "evaluation")
    page.select_option("#ev-report-select", "eval-results-run-6-86.7pct.json")
    summary = page.locator("#ev-summary")
    expect(summary).to_contain_text("86.7%")
    expect(summary).to_contain_text("PASS")
    expect(summary).to_contain_text("15 / 15")
    expect(summary).to_contain_text("13")

    failed = page.locator("#ev-cases tr.case-row.is-failed")
    expect(failed).to_have_count(2)
    expect(failed.nth(0)).to_contain_text("3")
    expect(failed.nth(1)).to_contain_text("8")

    failed.nth(0).locator("button").click()
    expect(page.locator("#ev-cases")).to_contain_text("L3: Expected 'Cross-Site Scripting (XSS)'")


def test_latest_completed_run_shortcut(page):
    open_section(page, "evaluation")
    page.click("#ev-view-latest")
    summary = page.locator("#ev-summary")
    expect(summary).not_to_contain_text("INCOMPLETE")
    expect(summary).to_contain_text("%")
