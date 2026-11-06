"""Load the existing Part 1A and Part 1B code by file path (research R3; task T012).

The portal never copies or re-implements this code (Constitution I). Modules are loaded
under unique names so Part 1A's `src` package and Part 1B's `reviewer` cannot collide, and
bytecode writing is disabled while loading so nothing is written under Part-1A/ or Part-1B/.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from app.config import Settings

_CACHE: dict[tuple[str, Path], ModuleType] = {}


class BackendLoadError(RuntimeError):
    """Raised when a Part 1A or Part 1B module cannot be found or imported."""


@dataclass(frozen=True)
class Backends:
    limiter_module: ModuleType
    evaluate_module: ModuleType

    @property
    def reviewer_module(self) -> ModuleType:
        return sys.modules[self.evaluate_module.analyze_code.__module__]


def _load(name: str, path: Path) -> ModuleType:
    path = Path(path).resolve()
    if (name, path) in _CACHE:
        return _CACHE[(name, path)]
    if not path.is_file():
        raise BackendLoadError(f"Backend module not found: {path}")

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BackendLoadError(f"Backend module cannot be loaded: {path}")
    module = importlib.util.module_from_spec(spec)

    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise BackendLoadError(f"Backend module failed to import: {path}") from exc
    finally:
        sys.dont_write_bytecode = previous

    _CACHE[(name, path)] = module
    return module


def load_backends(settings: Settings) -> Backends:
    limiter = _load("part1a_limiter", settings.limiter_path)
    evaluate = _load("part1b_evaluate", settings.evaluate_path)
    return Backends(limiter_module=limiter, evaluate_module=evaluate)
