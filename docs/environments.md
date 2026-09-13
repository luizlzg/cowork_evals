# Environments

## Summary

Two Python environments in this repository. They are not reconciled, and neither replaces the
other. One is built on clone and the other on demand.

- `.venv` is repository tooling. It runs `scripts/` and `tests/`, never a CoWork session,
  and its dependencies are unconstrained. `scripts/init.sh` builds it.
- `.venv_cowork` is the CoWork mirror. It pins the wheel set a session provides, and nothing
  else. Nothing in the package reads it and only `scripts/cowork_run.sh` uses it, so
  `init.sh` does not build it and no test requires it. Build it with
  `scripts/cowork_venv.sh` when you need it, and that script verifies it.
- Both are Python 3.10.12, the exact interpreter a session runs. The wheel set is what
  separates them, not the interpreter.
- Both are development environments. Neither is shipped, and `cowork_evals setup` creates
  neither.
- The mirror reproduces the interpreter and the wheels only. Not the OS, not the architecture,
  not the document tooling or the font stack. The container does; see [docker.md](docker.md).
- This file owns the split between the three requirements files, and the rule that decides
  which one a new pin goes in. Everything else links here for it.

| Environment   | Path           | Python   | Built by            | Runs                 |
| ------------- | -------------- | -------- | ------------------- | -------------------- |
| Repo tooling  | `.venv`        | 3.10.12  | `init.sh`, on clone | `scripts/`, `tests/` |
| CoWork mirror | `.venv_cowork` | 3.10.12  | `cowork_venv.sh`, on demand | Code that must behave like a session |

The mirror costs 604 MB, and the interpreter is no longer a reason to build it: both
environments are the same one. The wheel set is the only thing that separates
them, so build the mirror when an import has to be checked against a session's packages
without a container, and not otherwise. `cowork_evals test --docker` answers the same
question against the real image.

`.python-version` holds that version, and it is the only place on the development side that
does. `scripts/venv.sh`, `scripts/cowork_venv.sh` and `scripts/build.sh` all read it, so no
two of them can disagree. `docker/parity.py` carries the same version a second time, because
it ships in the wheel and cannot read a checkout file; `tests/unit/test_environments.py`
asserts the two agree.

Repo tooling never runs on a CoWork VM, so its dependencies are unconstrained. Code that must
behave like a session is pinned to what the VM has. Both interpreters are 3.10, so a file that
runs under one parses under the other, and only an import can tell them apart.

## Building it

```bash
scripts/init.sh                # both environments
scripts/venv.sh                # .venv, after a pyproject.toml change
scripts/cowork_venv.sh         # the mirror, after a requirements change
scripts/cowork_venv.sh --check # verify the mirror, no writes
```

`scripts/cowork_venv.sh` owns the mirror. Shell, not Python: it builds the environment the
3.10 code runs under and does not run under it. Verifying it calls `.venv` through `uv run`
for the PEP 503 name normalization in `cowork_evals.requirements`. That is the one
implementation of it: the mirror, the container parity comparison and the tests all read a
pinned requirements file through it, so no two of them can disagree on what `foo__bar`
normalizes to.

| Invocation   | Does                                                            |
| ------------ | --------------------------------------------------------------- |
| (no args)    | Create the mirror if absent, sync it, exit 0 if already correct |
| `--recreate` | Delete and rebuild from scratch                                 |
| `--check`    | Verify only, no writes, non-zero exit on drift                  |

`--check` verifies three things: the interpreter reports 3.10, every pin in
`requirements_installable.txt` is installed at its exact version, and nothing else is
installed except the test-only packages listed in the script.

## Running under the mirror

```bash
scripts/cowork_run.sh python3 path/to/x.py
scripts/cowork_run.sh pytest tests/
```

`cowork_run.sh` puts the mirror first on `PATH`, sets `VIRTUAL_ENV`, then `exec`s the command.
That is what activation does, scoped to one command. It matters for child processes: a script
that shells out to bare `python3` then resolves to 3.10, as it does on the VM.

**Never run `uv run` through it.** uv resolves against the project and will use or create
`.venv`, ignoring `VIRTUAL_ENV`. The command would then run against the dev dependency group
rather than the CoWork wheel set, which is the whole point of the mirror. `cowork_run.sh`
refuses a `uv` command line for that reason.

## The test-only packages

`pytest` and `pytest-timeout`, plus their transitive `pluggy`, `iniconfig`, `exceptiongroup`
and `tomli`.

None of them is on the CoWork image. Code under eval must not import one: it would pass here
and fail in a session. They are installed only so pytest can collect and run tests against
code that must behave like a session.

`cowork_venv.sh --check` also fails when a direct test-only package is not installed. Without
that check a newly added one is never installed by a plain sync: it is not a pin, so it cannot
be missing, and it is on the allowed-extras list, so it is not an extra.

## What the mirror does not reproduce

The interpreter and the wheels, nothing else. Not Ubuntu 22.04, not aarch64, not LibreOffice,
ImageMagick, pandoc, tesseract, or the Ubuntu font stack. Rendering and OCR behaviour still
diverges from a session. See [runtime.md](runtime.md) for what the image holds, and
[docker.md](docker.md) for the container that does reproduce them.

The mirror does not reach an eval case. `scripts/cowork_run.sh` puts it on `PATH` for a
command you run yourself, and that works. Inside a run the OS sandbox that a `Bash` grant
turns on cannot read it, because a virtual environment leaves its interpreter and standard
library outside that sandbox's readable set. A backend that ran the harness on the host would
have to stage a relocatable interpreter into the plugin under test instead. That design is
[staged_runtime.md](staged_runtime.md), and it is not built.

## Three requirements files

This file owns the split. Everything else links here for it.

| File                           | Is                                                   | Pins | Read by                           |
| ------------------------------ | ---------------------------------------------------- | ---- | --------------------------------- |
| `requirements.txt`             | The VM `pip freeze`, verbatim                        | 136  | Import checking, parity           |
| `requirements_installable.txt` | The same minus the nine below                        | 127  | The image build, `cowork_venv.sh` |
| `requirements_test.txt`        | pytest and what it needs that the inventory lacks    | 5    | The test image layer              |

All three are at `src/cowork_evals/data/` and ship as package data. See
[library.md](library.md).

The rule that decides which file a new pin goes in:

| The pin is                                        | Goes in                                       |
| ------------------------------------------------- | --------------------------------------------- |
| On a CoWork VM, measured                          | `requirements.txt`, and `requirements_installable.txt` unless it will not build on a laptop |
| Not on a CoWork VM, and needed to run pytest there | `requirements_test.txt`                      |
| Neither                                           | Nowhere. It is not a fact about the runtime   |

Nothing appears in more than one file. `tests/unit/test_environments.py` asserts that
`requirements_installable.txt` is `requirements.txt` minus exactly the nine below, at
identical versions, and that `requirements_test.txt` names nothing `requirements.txt` already
pins. That second assertion is what keeps the test image's install additive; see
[cowork_test.md](cowork_test.md).

The nine are `command-not-found`, `dbus-python`, `distro-info`, `pipx`, `PyGObject`,
`pyinotify`, `python-apt`, `ufw`, `unattended-upgrades`. They are importable in a session, so
an import checker still allows them; they will not build on a laptop, so the mirror omits
them. Which apt package supplies each one in the image is [docker.md](docker.md).
