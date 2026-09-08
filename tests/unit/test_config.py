"""`cowork_evals.yaml` loads as docs/cowork_driver.md says it does."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from cowork_evals.config import CONFIG_FILENAME, Config, CoWorkError


@contextlib.contextmanager
def working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def write(directory: Path, body: str, name: str = CONFIG_FILENAME) -> Path:
    file = directory / name
    file.write_text(body, encoding="utf-8")
    return file


def test_missing_file_yields_defaults(tmp_path: Path) -> None:
    with working_directory(tmp_path):
        config = Config.load()
    assert config.profile is None
    assert config.surface == "cowork"
    assert config.settle_seconds == 3.0
    assert config.session_timeout == 120.0
    assert config.idle_seconds == 20.0
    assert config.run_timeout == 1800.0
    assert config.max_runs == 50
    assert config.run_log == Path.home() / ".cowork-runs.jsonl"
    assert config.log_dir == tmp_path / "logs"


def test_file_values_beat_defaults(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  profile: Fixture\n  max_runs: 7\n  surface: ''\n")
    config = Config.load(file)
    assert config.profile == "Fixture"
    assert config.max_runs == 7
    assert config.surface == ""


def test_override_beats_the_file(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  profile: Fixture\n  max_runs: 7\n")
    config = Config.load(file, max_runs=3)
    assert config.profile == "Fixture"
    assert config.max_runs == 3


def test_unknown_key_inside_cowork_raises(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  profil: Fixture\n")
    with pytest.raises(CoWorkError) as raised:
        Config.load(file)
    assert raised.value.code == 2
    assert "profil" in str(raised.value)


def test_unknown_override_raises(tmp_path: Path) -> None:
    with working_directory(tmp_path), pytest.raises(CoWorkError) as raised:
        Config.load(nonsense=1)
    assert raised.value.code == 2


def test_unknown_top_level_section_is_ignored(tmp_path: Path) -> None:
    file = write(tmp_path, "docker:\n  platform: linux/arm64\ncowork:\n  profile: Fixture\n")
    assert Config.load(file).profile == "Fixture"


def test_tilde_is_expanded(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  run_log: ~/somewhere/runs.jsonl\n")
    config = Config.load(file)
    assert config.run_log == Path.home() / "somewhere" / "runs.jsonl"
    assert "~" not in str(config.run_log)


def test_relative_path_resolves_against_the_working_directory(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  log_dir: build/logs\n")
    with working_directory(tmp_path):
        config = Config.load(file)
    assert config.log_dir == tmp_path / "build" / "logs"


def test_log_dir_null_turns_the_file_off(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  log_dir: null\n")
    assert Config.load(file).log_dir is None


def test_empty_file_yields_defaults(tmp_path: Path) -> None:
    file = write(tmp_path, "")
    assert Config.load(file) == Config.load(write(tmp_path, "cowork:\n", "other.yaml"))


def test_a_named_file_that_is_absent_raises(tmp_path: Path) -> None:
    with pytest.raises(CoWorkError) as raised:
        Config.load(tmp_path / "absent.yaml")
    assert raised.value.code == 2


def test_a_wrongly_typed_value_raises(tmp_path: Path) -> None:
    file = write(tmp_path, "cowork:\n  max_runs: many\n")
    with pytest.raises(CoWorkError) as raised:
        Config.load(file)
    assert raised.value.code == 2


def test_sessions_root_is_derived_from_the_profile() -> None:
    root = Config(profile="Fixture").sessions_root
    assert root == (
        Path.home() / "Library" / "Application Support" / "Fixture" / "local-agent-mode-sessions"
    )


def test_sessions_root_without_a_profile_raises() -> None:
    with pytest.raises(CoWorkError) as raised:
        _ = Config().sessions_root
    assert raised.value.code == 2


def test_config_is_frozen() -> None:
    config = Config(profile="Fixture")
    with pytest.raises((AttributeError, TypeError)):
        config.profile = "Other"  # type: ignore[misc]
