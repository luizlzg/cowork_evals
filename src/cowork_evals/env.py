"""`.env`, and the settings over it.

The three layers and their precedence are [docs/library.md](../../docs/library.md). The
names are [docs/running_evals.md](../../docs/running_evals.md),
[docs/docker.md](../../docs/docker.md) and
[docs/plugin_eval.md](../../docs/plugin_eval.md).

A value read here is a credential as often as not. Nothing in this module logs a value,
puts one in an exception message, or writes one into `os.environ`.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ENV_FILENAME = ".env"

# Every name this package reads, with the built-in default that applies when neither the
# process environment nor `.env` carries it. A name absent from this table defaults to the
# empty string, because a consumer's `.env` serves more than this command.
DEFAULTS: dict[str, str] = {
    "EVAL_MODEL": "sonnet",
    "EVAL_JUDGE_MODEL": "haiku",
    "EVAL_ALLOW_TOOLS": "Bash",
    "EVAL_MAX_COST_USD": "5",
    "EVAL_MAX_COST_TOTAL_USD": "25",
    "EVAL_PLATFORM": "linux/arm64",
    "CLAUDE_CODE_VERSION": "2.1.265",
    "CLAUDE_CODE_WALNUT_SPIRE": "1",
}


def env_values(env_file: Path | str | None = None) -> dict[str, str]:
    """The `.env` file as a mapping. An absent file is an empty mapping, not an error.

    `interpolate=False`: a value is never expanded against another value or against the
    process environment. Every key the file carries is kept, recognised or not.
    """
    path = Path(env_file) if env_file is not None else Path.cwd() / ENV_FILENAME
    if not path.is_file():
        return {}
    read = dotenv_values(path, interpolate=False)
    return {name: value for name, value in read.items() if value is not None}


def setting(name: str, default: str | None = None, *, env_file: Path | str | None = None) -> str:
    """The process environment beats `.env` beats `default`.

    `default` falls back to this module's `DEFAULTS`, and to the empty string for a name
    that is not in it.
    """
    if name in os.environ:
        return os.environ[name]
    values = env_values(env_file)
    if name in values:
        return values[name]
    if default is not None:
        return default
    return DEFAULTS.get(name, "")
