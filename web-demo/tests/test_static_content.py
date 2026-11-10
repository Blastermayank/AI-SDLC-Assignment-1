"""Accuracy of the portal's explanatory content (FR-002, FR-003; task T041)."""

import re
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[1] / "static" / "index.html"
HTML = INDEX.read_text(encoding="utf-8")
TEXT = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", HTML))
LOWER = TEXT.lower()


@pytest.mark.parametrize(
    "required",
    [
        "gemini-3.5-flash-lite",
        "category/alias matching",
        "not an LLM judge",
        "one recorded run",
        "Tiered Rate Limiter",
        "AI Security Code Reviewer",
        "lost when the server restarts",
        "Results depend on Gemini's availability",
        "never executed",
        "not in repository",
    ],
)
def test_required_statements_are_present(required):
    assert required.lower() in LOWER


@pytest.mark.parametrize(
    "section", ["overview", "methodology", "part-1a", "part-1b", "evaluation", "evidence"]
)
def test_six_sections_exist(section):
    assert f'id="section-{section}"' in HTML


def section_text(section):
    match = re.search(rf'<section id="section-{section}".*?</section>', HTML, re.DOTALL)
    assert match, f"section {section} missing"
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(0))).lower()


@pytest.mark.parametrize(
    "limitation",
    [
        "in memory",  # Part 1A: rate-limit state
        "not shared between processes",  # Part 1A
        "vary between runs",  # Part 1B: model variability
        "only the 16 cases",  # Part 1B: dataset coverage
        "names and aliases",  # Part 1B: alias-based semantic layer
        "availability",  # Part 1B: service dependency
    ],
)
def test_overview_states_known_limitations(limitation):
    # US4 independent test: the limitations must be answerable from the overview itself.
    assert limitation in section_text("overview")


def test_no_llm_judge_claim():
    assert "llm-as-a-judge" not in LOWER
    for match in re.finditer(r"llm judge", LOWER):
        assert re.search(r"not an (independent )?$", LOWER[: match.start()]), "LLM judge claim"


def test_no_perfect_accuracy_or_mock_claims():
    assert "100%" not in TEXT
    assert "mock" not in LOWER
    assert "guarantee" not in LOWER.replace("not a general accuracy guarantee", "")
