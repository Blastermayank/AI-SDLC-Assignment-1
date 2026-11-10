"""Static frontend safety rules (SC-007; Constitution IV and VI; task T051)."""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "static"
JS_FILES = sorted((STATIC / "js").glob("*.js"))
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "css" / "portal.css").read_text(encoding="utf-8")
HTML_SINKS = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
              "new Function", "setAttribute('on", 'setAttribute("on')


def test_javascript_modules_exist():
    names = {path.name for path in JS_FILES}
    assert {"app.js", "api.js", "dom.js", "registry.js", "part1a.js", "part1b.js",
            "evaluation.js", "evidence.js", "methodology.js"} <= names


@pytest.mark.parametrize("path", JS_FILES, ids=lambda path: path.name)
def test_no_html_injection_sinks(path):
    source = path.read_text(encoding="utf-8")
    for sink in HTML_SINKS:
        assert sink not in source, f"{path.name} uses {sink}"


@pytest.mark.parametrize("path", JS_FILES, ids=lambda path: path.name)
def test_no_external_urls_in_javascript(path):
    assert not re.search(r"https?://", path.read_text(encoding="utf-8"))


def test_index_has_no_inline_script_bodies():
    for body in re.findall(r"<script\b[^>]*>(.*?)</script>", HTML, flags=re.S | re.I):
        assert body.strip() == ""


def test_index_has_no_event_handler_or_style_attributes():
    assert not re.search(r"\son[a-z]+\s*=", HTML, flags=re.I)
    assert not re.search(r"\sstyle\s*=", HTML, flags=re.I)


def test_index_has_no_external_urls():
    assert not re.search(r"https?://", HTML)


def test_stylesheet_has_no_remote_imports():
    assert "@import" not in CSS
    assert not re.search(r"url\(\s*['\"]?https?:", CSS)
