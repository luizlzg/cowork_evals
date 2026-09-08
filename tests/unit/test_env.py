"""`env.py` reads the three layers docs/library.md defines, in that order.

Every test here writes a real `.env` and sets the real process environment. Neither is a
stand-in: the module reads the file the test wrote and the environment the test set, and
both are restored afterwards. The `environment` fixture is in tests/conftest.py.
"""

from __future__ import annotations

import os
from pathlib import Path

from cowork_evals.env import DEFAULTS, env_values, setting


def write_env(directory: Path, body: str) -> Path:
    path = directory / ".env"
    path.write_text(body)
    return path


def test_a_missing_env_file_is_not_an_error(environment, tmp_path):
    assert env_values(tmp_path / ".env") == {}
    with environment(EVAL_MODEL=None):
        assert setting("EVAL_MODEL", env_file=tmp_path / ".env") == "sonnet"


def test_the_default_applies_when_no_layer_carries_the_name(environment, tmp_path):
    env_file = write_env(tmp_path, "EVAL_JUDGE_MODEL=opus\n")
    with environment(EVAL_MODEL=None):
        assert setting("EVAL_MODEL", env_file=env_file) == "sonnet"


def test_env_beats_the_default(environment, tmp_path):
    env_file = write_env(tmp_path, "EVAL_MODEL=haiku\n")
    with environment(EVAL_MODEL=None):
        assert setting("EVAL_MODEL", env_file=env_file) == "haiku"


def test_the_process_environment_beats_env(environment, tmp_path):
    env_file = write_env(tmp_path, "EVAL_MODEL=haiku\n")
    with environment(EVAL_MODEL="opus"):
        assert setting("EVAL_MODEL", env_file=env_file) == "opus"


def test_an_explicit_default_beats_the_table(environment, tmp_path):
    with environment(EVAL_MODEL=None):
        assert setting("EVAL_MODEL", "sonnet-1m", env_file=tmp_path / ".env") == "sonnet-1m"


def test_an_unknown_name_defaults_to_the_empty_string(environment, tmp_path):
    with environment(EVAL_NOT_A_SETTING=None):
        assert setting("EVAL_NOT_A_SETTING", env_file=tmp_path / ".env") == ""


def test_an_unrecognised_key_in_the_file_is_kept(tmp_path):
    env_file = write_env(tmp_path, "EVAL_MODEL=haiku\nSOMETHING_ELSE=1\n")
    assert env_values(env_file) == {"EVAL_MODEL": "haiku", "SOMETHING_ELSE": "1"}


def test_a_value_is_never_interpolated(tmp_path):
    env_file = write_env(tmp_path, "EVAL_MODEL=haiku\nEVAL_JUDGE_MODEL=${EVAL_MODEL}\n")
    assert env_values(env_file)["EVAL_JUDGE_MODEL"] == "${EVAL_MODEL}"


def test_a_bare_key_is_absent_rather_than_none(tmp_path):
    env_file = write_env(tmp_path, "EVAL_MODEL\n")
    assert env_values(env_file) == {}


def test_env_resolves_from_the_working_directory(environment, working_directory, tmp_path):
    write_env(tmp_path, "EVAL_PLATFORM=linux/amd64\n")
    with environment(EVAL_PLATFORM=None), working_directory(tmp_path):
        assert setting("EVAL_PLATFORM") == "linux/amd64"


def test_reading_env_never_touches_the_process_environment(tmp_path):
    env_file = write_env(tmp_path, "EVAL_A_KEY_NOT_IN_THE_ENVIRONMENT=x\n")
    setting("EVAL_A_KEY_NOT_IN_THE_ENVIRONMENT", env_file=env_file)
    assert "EVAL_A_KEY_NOT_IN_THE_ENVIRONMENT" not in os.environ


def test_the_documented_defaults(environment, tmp_path):
    """Each row is the default its page records. docs/running_evals.md, docs/docker.md."""
    assert DEFAULTS == {
        "EVAL_MODEL": "sonnet",
        "EVAL_JUDGE_MODEL": "haiku",
        "EVAL_ALLOW_TOOLS": "Bash",
        "EVAL_MAX_COST_USD": "5",
        "EVAL_MAX_COST_TOTAL_USD": "25",
        "EVAL_PLATFORM": "linux/arm64",
        "CLAUDE_CODE_VERSION": "2.1.259",
        "CLAUDE_CODE_WALNUT_SPIRE": "1",
        "ANTHROPIC_API_KEY": "",
    }
    with environment(**dict.fromkeys(DEFAULTS)):
        for name, value in DEFAULTS.items():
            assert setting(name, env_file=tmp_path / ".env") == value
