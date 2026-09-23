"""The fixture for the session environment. A `Bash` call sees only the kept names.

`env.txt` holds the variable names one `Bash` call saw, one per line. The allowed set is the
defaults of `docker.session_env` and `docker.keep_env`, because this repository sets neither
key, plus `_`, which `env` sets on itself. A CoWork session has only `session_env` names, so the
same case passes on both backends. See ../../../../../README.md.
"""

from cowork_evals.checks import Run, check
from cowork_evals.config import DockerSection

ALLOWED = {*DockerSection().session_env, *DockerSection().keep_env, "_"}
REQUIRED = ("HOME", "PATH", "TMPDIR")


def names(run: Run) -> set[str]:
    return set(run.file("env.txt").read_text(encoding="utf-8").split())


@check
def only_kept_names(run: Run) -> None:
    extra = sorted(names(run) - ALLOWED)
    assert not extra, f"a Bash call saw names outside the kept lists: {' '.join(extra)}"


@check
def the_session_names_are_there(run: Run) -> None:
    missing = [name for name in REQUIRED if name not in names(run)]
    assert not missing, f"a Bash call did not see {' '.join(missing)}"
