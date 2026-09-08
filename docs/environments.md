# Environments

Two Python environments. They are not reconciled, and neither replaces the other.

| Environment   | Path today     | Python | Defined by                         | Runs                 |
| ------------- | -------------- | ------ | ---------------------------------- | -------------------- |
| Repo tooling  | `.venv`        | 3.14   | `pyproject.toml` dependency groups | `scripts/`, `tests/` |
| CoWork mirror | `.venv_cowork` | 3.10   | `requirements_installable.txt`     | Code under eval      |

Repo tooling never runs on a CoWork VM, so it is unconstrained. Code under eval runs on the
VM, so it is pinned to what the VM has.

Only the mirror is shipped. `.venv` is this repository's own, a consumer never builds it,
and `cowork_evals setup` does not create it.

The mirror moves from `.venv_cowork` to `~/.cache/cowork_evals/venv-<digest>/` when the
package is built, so that one mirror serves the command and the development scripts alike.
[library.md](library.md) says where it lands and how the digest is computed.

## Building it

The `cowork_evals` routes are design and are not built. The `scripts/` routes are built and
are what builds the mirror today. See the status table in
[running_evals.md](running_evals.md).

```bash
cowork_evals setup --venv      # the shipped route
cowork_evals check --venv      # verify the mirror, no writes

scripts/init.sh                # development: both environments
scripts/venv.sh                # development: .venv, after a pyproject.toml change
scripts/cowork_venv.sh         # development: the mirror, after a requirements change
scripts/cowork_venv.sh --check # development: verify the mirror, no writes
```

`scripts/cowork_venv.sh` owns the mirror during development. Shell, not Python: it runs
before and independently of `.venv`.

| Invocation   | Does                                                             |
| ------------ | ---------------------------------------------------------------- |
| (no args)    | Create the mirror if absent, sync it, exit 0 if already correct  |
| `--recreate` | Delete and rebuild from scratch                                  |
| `--check`    | Verify only, no writes, non-zero exit on drift                   |

`--check` verifies three things: the interpreter reports 3.10, every pin in
`requirements_installable.txt` is installed at its exact version, and nothing else is
installed except the test-only packages listed in the script.

## Running under the mirror

```bash
scripts/cowork_run.sh python3 path/to/x.py
scripts/cowork_run.sh pytest tests/
```

`cowork_run.sh` puts the mirror first on `PATH`, sets `VIRTUAL_ENV`, then `exec`s the
command. That is what activation does, scoped to one command. It matters for child
processes: a script that shells out to bare `python3` then resolves to 3.10, as it does on
the VM.

**Never run `uv run` through it.** uv resolves against the project and will use or create
the 3.14 `.venv`, ignoring `VIRTUAL_ENV`. `cowork_run.sh` refuses a `uv` command line for
that reason.


## The test-only packages

`pytest` and `pytest-timeout`, plus their transitive `pluggy`, `iniconfig`, `exceptiongroup`
and `tomli`.

None of them is on the CoWork image. Code under eval must not import one: it would pass here
and fail in a session. They are installed only so pytest can collect and run tests against
code that must behave like a session.

`cowork_venv.sh --check` also fails when a direct test-only package is not installed.
Without that check a newly added one is never installed by a plain sync: it is not a pin, so
it cannot be missing, and it is on the allowed-extras list, so it is not an extra.

## What the mirror does not reproduce

The interpreter and the wheels, nothing else. Not Ubuntu 22.04, not aarch64, not
LibreOffice, ImageMagick, pandoc, tesseract, or the Ubuntu font stack. Rendering and OCR
behaviour still diverges from a session. See [runtime.md](runtime.md) for what the image
holds, and [docker.md](docker.md) for the container that does reproduce them.

The mirror does not itself reach an eval case. `scripts/cowork_run.sh` puts it on `PATH` for
a command you run yourself, and that works. Inside a run the OS sandbox that a `Bash` grant
turns on cannot read it, because a virtual environment leaves its interpreter and standard
library under the home directory. The venv backend therefore copies a relocatable
interpreter and this mirror's `site-packages` into the plugin under test instead. See
[staged_runtime.md](staged_runtime.md).

## Two requirements files

This file owns the split. Everything else links here for it.

| File                           | Is                                       | Pins | Used by                          |
| ------------------------------ | ---------------------------------------- | ---- | -------------------------------- |
| `requirements.txt`             | The VM `pip freeze`, verbatim            | 136  | Import checking, the image       |
| `requirements_installable.txt` | The same minus the nine below            | 127  | `setup --venv`, `cowork_venv.sh` |

Both are at [`../src/cowork_evals/data/`](../src/cowork_evals/data/) and ship as package
data. See [library.md](library.md).
`tests/unit/test_environments.py` asserts that the second is the first minus exactly those nine,
at identical versions.

The nine are `command-not-found`, `dbus-python`, `distro-info`, `pipx`, `PyGObject`,
`pyinotify`, `python-apt`, `ufw`, `unattended-upgrades`. They are importable in a session,
so an import checker still allows them; they will not build on a laptop, so the mirror omits
them. Which apt package supplies each one in the image is [docker.md](docker.md).
