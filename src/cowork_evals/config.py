"""`cowork_evals.yaml`, and the frozen `Config` it produces.

The fields, their defaults and the five loading rules are in
[docs/cowork_driver.md](../../docs/cowork_driver.md). This module reads that file and
nothing else: no session, no process, no environment variable.

`CoWorkError` lives here because configuration is the first thing that fails, and
`cowork.py` imports it rather than the other way round.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = "cowork_evals.yaml"
SECTION = "cowork"

# The deep link prompt cap. docs/cowork_desktop.md.
PROMPT_LIMIT = 14336


class CoWorkError(Exception):
    """A driver failure, carrying its taxonomy code from docs/cowork_driver.md."""

    def __init__(self, code: int, message: str, session_dir: Path | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.session_dir = session_dir


def _absolute(value: Path | str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise CoWorkError(2, f"{SECTION}.{name}: expected a string, got {type(value).__name__}")
    return value


def _optional_text(name: str, value: Any) -> str | None:
    return None if value is None else _text(name, value)


def _seconds(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CoWorkError(2, f"{SECTION}.{name}: expected a number, got {type(value).__name__}")
    if value < 0:
        raise CoWorkError(2, f"{SECTION}.{name}: expected a number at or above zero, got {value}")
    return float(value)


def _count(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CoWorkError(2, f"{SECTION}.{name}: expected an integer, got {type(value).__name__}")
    if value < 0:
        raise CoWorkError(2, f"{SECTION}.{name}: expected an integer at or above zero, got {value}")
    return value


def _path(name: str, value: Any) -> Path:
    if isinstance(value, Path):
        return _absolute(value)
    return _absolute(_text(name, value))


def _optional_path(name: str, value: Any) -> Path | None:
    return None if value is None else _path(name, value)


# One converter per field. The key set is also the set of accepted keys and overrides.
_FIELDS: dict[str, Callable[[str, Any], Any]] = {
    "profile": _optional_text,
    "surface": _text,
    "settle_seconds": _seconds,
    "session_timeout": _seconds,
    "idle_seconds": _seconds,
    "run_timeout": _seconds,
    "max_runs": _count,
    "run_log": _path,
    "log_dir": _optional_path,
}


@dataclass(frozen=True, slots=True)
class Config:
    """The resolved driver configuration. Frozen, and never reassigned."""

    profile: str | None = None
    surface: str = "cowork"
    settle_seconds: float = 3.0
    session_timeout: float = 120.0
    idle_seconds: float = 20.0
    run_timeout: float = 1800.0
    max_runs: int = 50
    run_log: Path = Path("~/.cowork-runs.jsonl")
    log_dir: Path | None = Path("logs")

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_log", _path("run_log", self.run_log))
        if self.log_dir is not None:
            object.__setattr__(self, "log_dir", _path("log_dir", self.log_dir))

    @property
    def sessions_root(self) -> Path:
        """Where the application writes sessions. docs/cowork_desktop.md.

        Raises when `profile` is unset, which is how a missing profile is refused at the
        first call that needs one rather than at construction.
        """
        if not self.profile:
            raise CoWorkError(
                2, f"no CoWork profile configured: set {SECTION}.profile in {CONFIG_FILENAME}"
            )
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / self.profile
            / "local-agent-mode-sessions"
        )

    @classmethod
    def load(cls, path: Path | str | None = None, **overrides: Any) -> Config:
        """Read the configuration file, apply the overrides, and freeze the result.

        `path` defaults to `cowork_evals.yaml` in the working directory, and a missing
        default file is not an error. A file named explicitly must exist, so a mistyped
        path is never a silent set of defaults.
        """
        values = _read(path)
        values.update(_convert(overrides, "override"))
        return cls(**values)


def _read(path: Path | str | None) -> dict[str, Any]:
    named = path is not None
    file = Path(path).expanduser() if named else Path.cwd() / CONFIG_FILENAME
    if not file.is_file():
        if named:
            raise CoWorkError(2, f"{file}: no such configuration file")
        return {}

    try:
        document = yaml.safe_load(file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise CoWorkError(2, f"{file}: unreadable configuration: {error}") from error

    if document is None:
        return {}
    if not isinstance(document, dict):
        raise CoWorkError(2, f"{file}: expected a mapping at the top level")

    # An unknown top level section is ignored, so a later plan adds one without touching this.
    section = document.get(SECTION)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise CoWorkError(2, f"{file}: expected a mapping under {SECTION}:")
    return _convert(section, str(file))


def _convert(values: dict[str, Any], source: str) -> dict[str, Any]:
    unknown = sorted(set(values) - set(_FIELDS))
    if unknown:
        raise CoWorkError(2, f"{source}: unknown {SECTION} key {', '.join(unknown)}")
    return {name: _FIELDS[name](name, value) for name, value in values.items()}
