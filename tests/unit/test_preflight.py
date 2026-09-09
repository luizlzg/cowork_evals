"""The unmet conditions of each backend.

Nothing here starts a daemon, a container or a CoWork session. The configuration files are
written to `tmp_path`, the case tree and the run log are hand-written, and the ceiling
arithmetic is read back from what `cowork_backend.plan` reported. The conditions are the
preflight table in docs/cli.md. See ../README.md.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cowork_evals import preflight
from cowork_evals.config import Config

DATA = Path(__file__).resolve().parent.parent / "data"
TREE = DATA / "cases" / "tree"


def configured(tmp_path: Path, text: str) -> Config:
    """One `cowork_evals.yaml` written to disk and loaded, as an invocation loads it."""
    path = tmp_path / "cowork_evals.yaml"
    path.write_text(text, encoding="utf-8")
    return Config.load(path)


# The shape of each returned list.


def test_every_backend_returns_a_list_of_lines() -> None:
    config = Config()
    for backend in (preflight.DOCKER, preflight.COWORK, preflight.TEST):
        lines = preflight.checks(backend, config)
        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)


def test_checks_all_covers_both_backends_in_order() -> None:
    config = Config()
    assert preflight.checks_all(config) == preflight.checks(
        preflight.DOCKER, config
    ) + preflight.checks(preflight.COWORK, config)


def test_the_test_verb_preflight_never_names_the_container_login() -> None:
    """There is no model call in that path, so there is nothing to authenticate."""
    lines = preflight.checks(preflight.TEST, Config())
    assert not [line for line in lines if "credential" in line]


def test_an_unknown_backend_is_refused() -> None:
    with pytest.raises(ValueError, match="no preflight for venv"):
        preflight.checks("venv", Config())


def test_every_docker_line_names_the_command_that_fixes_it() -> None:
    for line in preflight.checks(preflight.DOCKER, Config()):
        assert "cowork_evals setup --docker" in line or "Docker Desktop" in line


# The CoWork lines.


def test_no_configured_profile_is_one_line_carrying_its_message(tmp_path: Path) -> None:
    config = configured(tmp_path, "cowork:\n  surface: cowork\n")
    lines = preflight.checks(preflight.COWORK, config)
    assert [line for line in lines if "cowork.profile" in line] == [
        "no CoWork profile configured: set cowork.profile in cowork_evals.yaml"
    ]


def test_an_unreadable_sessions_root_is_one_line_naming_it(tmp_path: Path) -> None:
    profile = tmp_path / "Profile"
    profile.mkdir()
    config = configured(tmp_path, f"cowork:\n  profile: {profile}\n")
    sessions = profile / "local-agent-mode-sessions"
    lines = preflight.checks(preflight.COWORK, config)
    assert [line for line in lines if str(sessions) in line] == [
        f"{sessions}: no readable sessions root: check cowork.profile in the "
        "configuration file, and open CoWork once on this profile"
    ]


def test_a_readable_sessions_root_reports_nothing(tmp_path: Path) -> None:
    profile = tmp_path / "Profile"
    (profile / "local-agent-mode-sessions").mkdir(parents=True)
    config = configured(tmp_path, f"cowork:\n  profile: {profile}\n")
    lines = preflight.checks(preflight.COWORK, config)
    assert not [line for line in lines if "sessions root" in line]
    assert not [line for line in lines if "cowork.profile" in line]


def test_the_platform_is_reported_only_off_macos(tmp_path: Path) -> None:
    config = configured(tmp_path, "cowork:\n  profile: Nowhere\n")
    named = [line for line in preflight.checks(preflight.COWORK, config) if "platform" in line]
    assert named == ([] if sys.platform == preflight.DARWIN else [named[0]])


# The rate ceiling.


def run_log(path: Path, entries: int) -> None:
    """A CoWork run log carrying `entries` submissions inside the trailing 24 hours."""
    stamp = datetime.now(UTC).isoformat()
    path.write_text(
        "".join(
            json.dumps({"timestamp": stamp, "outcome": "collected", "session_dir": None}) + "\n"
            for _ in range(entries)
        ),
        encoding="utf-8",
    )


def test_a_suite_inside_the_ceiling_reports_nothing(tmp_path: Path) -> None:
    log = tmp_path / "runs.jsonl"
    run_log(log, 2)
    config = configured(tmp_path, f"cowork:\n  max_runs: 50\n  run_log: {log}\n")
    assert preflight.cowork_ceiling(TREE / "evals", config=config) == []


def test_a_suite_above_the_ceiling_is_one_line_carrying_the_arithmetic(tmp_path: Path) -> None:
    """`tests/data/cases/tree/evals` holds four cases, two of which this backend can honour."""
    log = tmp_path / "runs.jsonl"
    run_log(log, 3)
    config = configured(tmp_path, f"cowork:\n  max_runs: 3\n  run_log: {log}\n")
    assert preflight.cowork_ceiling(TREE / "evals", config=config) == [
        "the rate ceiling would be exceeded: 2 submissions planned, "
        "3 already made in the last 24 hours, max_runs is 3"
    ]


def test_the_ceiling_reads_the_filters_it_is_given(tmp_path: Path) -> None:
    log = tmp_path / "runs.jsonl"
    run_log(log, 3)
    config = configured(tmp_path, f"cowork:\n  max_runs: 3\n  run_log: {log}\n")
    assert preflight.cowork_ceiling(TREE / "evals", config=config, tags=("absent",)) == []
