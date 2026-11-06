"""Portal settings (task T011). Never reads or stores the Gemini API key value."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

WEB_DEMO_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = WEB_DEMO_DIR / "static"
DEFAULT_CONFIG_FILE = WEB_DEMO_DIR / "portal-config.json"

# data-model.md: RateLimitRequest.client_id "1-64 chars, regex ^[A-Za-z0-9_.-]{1,64}$"
CLIENT_ID_PATTERN = r"^[A-Za-z0-9_.-]{1,64}$"
# data-model.md: ReviewSubmission.code "1-20,000 characters and not whitespace-only"
MAX_CODE_CHARS = 20_000
# FR-004: only https://github.com/<owner>/<repo> URLs are shown.
REPOSITORY_URL_PATTERN = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")


def load_repository_url(config_file: Path) -> str | None:
    """Return the configured repository URL, or None if absent or not a GitHub URL."""
    try:
        data = json.loads(Path(config_file).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    value = data.get("repository_url") if isinstance(data, dict) else None
    if isinstance(value, str) and REPOSITORY_URL_PATTERN.fullmatch(value):
        return value
    return None


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    repository_url: str | None = None
    static_dir: Path = STATIC_DIR
    max_body_bytes: int = 65_536
    max_code_chars: int = MAX_CODE_CHARS
    analysis_timeout_s: float = 60.0
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost")
    max_evidence_bytes: int = 1_048_576

    @classmethod
    def from_environment(
        cls,
        repo_root: Path | None = None,
        config_file: Path | None = None,
        **overrides,
    ) -> Settings:
        root = repo_root or os.environ.get("WEB_DEMO_REPO_ROOT") or WEB_DEMO_DIR.parent
        url = load_repository_url(config_file or DEFAULT_CONFIG_FILE)
        return cls(repo_root=Path(root).resolve(), repository_url=url, **overrides)

    # Part 1A
    @property
    def limiter_path(self) -> Path:
        return self.repo_root / "Part-1A" / "src" / "limiter.py"

    @property
    def part1a_harness_results(self) -> Path:
        return self.repo_root / "Part-1A" / "evidence" / "harness-results"

    # Part 1B
    @property
    def evaluate_path(self) -> Path:
        return self.repo_root / "Part-1B" / ".harness" / "evaluate.py"

    @property
    def part1b_evidence_dir(self) -> Path:
        return self.repo_root / "Part-1B" / "evidence"

    @property
    def eval_results_file(self) -> Path:
        return self.part1b_evidence_dir / "eval-results.json"

    @property
    def dataset_file(self) -> Path:
        return self.repo_root / "Part-1B" / "evals" / "dataset.json"

    # Portal evidence
    @property
    def web_harness_results(self) -> Path:
        return self.repo_root / "web-demo" / "evidence" / "harness-results"

    def relative(self, path: Path) -> str:
        """Repository-relative, forward-slash path for display."""
        return Path(path).resolve().relative_to(self.repo_root).as_posix()
