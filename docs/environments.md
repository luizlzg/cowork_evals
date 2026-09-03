# Environments

Two Python environments. They are not reconciled, and neither replaces the other.

| Environment   | Path           | Python | Defined by                               | Runs                 |
| ------------- | -------------- | ------ | ---------------------------------------- | -------------------- |
| Repo tooling  | `.venv`        | 3.14   | `pyproject.toml` dependency groups       | `scripts/`, `tests/` |
| CoWork mirror | `.venv_cowork` | 3.10   | `docs/data/requirements_installable.txt` | Code under eval      |

Repo tooling never runs on a CoWork VM, so it is unconstrained. Code under eval runs on the
VM, so it is fully constrained. One interpreter for both would drag the repo tooling down to
3.10 for no gain.

## Building them

```bash
scripts/init.sh                # both
scripts/venv.sh                # .venv, after a pyproject.toml change
scripts/cowork_venv.sh         # .venv_cowork, after a requirements change
scripts/cowork_venv.sh --check # verify the mirror, no writes
```

`scripts/cowork_venv.sh` owns the mirror. Shell, not Python: it runs before and
independently of `.venv`.

| Invocation   | Does                                                                |
| ------------ | ------------------------------------------------------------------- |
| (no args)    | Create `.venv_cowork` if absent, sync it, exit 0 if already correct |
| `--recreate` | Delete and rebuild from scratch                                     |
| `--check`    | Verify only, no writes, non-zero exit on drift                      |

`--check` verifies three things: the interpreter reports 3.10, all 127 pins are installed at
their exact versions, and nothing else is installed except the test-only packages listed in
the script.

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

## Two requirements files

| File                                     | Is                                       | Used by          |
| ---------------------------------------- | ---------------------------------------- | ---------------- |
| `docs/data/requirements.txt`             | The VM `pip freeze`, 136 pins, verbatim  | Import checking  |
| `docs/data/requirements_installable.txt` | The same minus the 9 that cannot install | `cowork_venv.sh` |

The nine are `command-not-found`, `dbus-python`, `distro-info`, `pipx`, `PyGObject`,
`pyinotify`, `python-apt`, `ufw`, `unattended-upgrades`. They are importable in a session,
so an import checker still allows them; they will not build on a laptop, so the mirror omits
them.
