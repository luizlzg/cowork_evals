# The test command

A consumer's Python tests, run inside the CoWork image. No model, no harness, no case tree,
no grader, no result document and no gate. pytest collects, runs and reports, and this
package supplies only the runtime it runs in.

It is not an eval. An eval needs a model in the loop, and there is none here. Code destined
for a skill is exercised on the CoWork runtime before an eval is written over it.

The image this one is built over is [docker.md](docker.md), and the inventory that image
reproduces is [runtime.md](runtime.md). Neither is restated here. What of this is built is
the status table in [running_evals.md](running_evals.md).

## Usage

```bash
cowork_evals test --docker path/to/plugin/tests            # the shipped route
cowork_evals test --docker path/to/plugin -- -k parser -v  # with a pytest tail

scripts/cowork_pytest.sh                                   # development: build for docker.platform
scripts/cowork_pytest.sh --check                           # development: the digest is present, no writes
scripts/cowork_pytest.sh --recreate                        # development: build with --no-cache
scripts/cowork_pytest.sh path/to/plugin/tests -- -v        # development: run a suite
```

`scripts/cowork_pytest.sh` is the development route until the verb exists, exactly as
`scripts/image.sh` is for the eval image. It is a development task for this repository and
is not part of the command. See [../scripts/README.md](../scripts/README.md).

## Transparency

Once the container starts, this package adds nothing and interprets nothing.

| Rule                                                                                |
| ------------------------------------------------------------------------------------- |
| No pytest option is added. Not `-p no:cacheprovider`, not `-q`, not a colour flag   |
| No pytest plugin is installed, `pytest-timeout` included                            |
| No pytest environment variable is set. Not `PYTHONDONTWRITEBYTECODE`, not `PYTHONPATH` |
| The exit code is pytest's, unchanged                                                |
| A raw pytest argument tail is forwarded verbatim, after the resolved target         |

Whatever `pytest <path>` does on a laptop is what it does here, on the CoWork runtime
instead of the laptop's. A surprise in a test runner is a defect.

A timeout is the one of these a reader asks about. It is a restriction the developer did
not ask for, so a caller that wants one passes it in the tail.

## Two images

| Tag                          | Is                                            | Built by                     |
| ---------------------------- | --------------------------------------------- | ---------------------------- |
| `cowork-evals:<digest>`      | The CoWork image an eval runs in              | `scripts/image.sh`           |
| `cowork-evals-test:<digest>` | That image plus one install layer             | `scripts/cowork_pytest.sh`   |

The eval image never carries pytest. That keeps `scripts/parity.sh` and
`tests/unit/test_parity.py` untouched and the inventory in [runtime.md](runtime.md) exact:
a package installed for the test runner would show in the eval image's `pip freeze` and
would be a package a session does not have.

The test digest is the sha256 of the base image's digest, `Dockerfile.pytest`,
`requirements_test.txt` and the resolved `docker.platform`, truncated to twelve characters.
The base digest goes in first, so a rebuilt base is a different test tag rather than a stale
hit over an old base. There is no `latest`, for the reason in [docker.md](docker.md).

One module per image. `src/cowork_evals/docker/__init__.py` owns the image the harness runs
in and `src/cowork_evals/docker/pytest_image.py` owns the image pytest runs in. Each owns
its Dockerfile, its digest, its argument lists, its check and the one command that fixes an
absent image. The class is `PytestImage` and not `TestImage`, because pytest collects a
class named `Test*` and would warn on the second name every time a test module imported it.

`Dockerfile.pytest` declares `ARG BASE_TAG` before its `FROM` and nothing else, so it names
no image of its own. BuildKit prints `InvalidDefaultArgInFrom` on every build, because that
argument has no default. Giving it one would be a default base tag, which is the stale base
this design exists to prevent, so the warning stays.

## The pinned list

`src/cowork_evals/data/requirements_test.txt` holds pytest and every package it needs that
the inventory does not carry, each pinned to an exact version. A package already in the
inventory is never listed, whatever version pytest would prefer. The layer installs it with
`--no-deps`: a bare `pip install pytest` may move an inventory pin, and a moved pin voids
what the image claims to be.

Which of the three requirements files a new pin goes in is
[environments.md](environments.md), which owns that split.

Measured 2026-09-09 on `cowork-evals:57f48ba2adac`, `linux/arm64`, a snapshot.
`pip install --dry-run pytest` inside that image resolves pytest 9.1.1 and would install
five packages and move none:

| Package         | Version | In the inventory |
| --------------- | ------- | ---------------- |
| `pytest`        | 9.1.1   | no               |
| `pluggy`        | 1.6.0   | no               |
| `iniconfig`     | 2.3.0   | no               |
| `exceptiongroup`| 1.3.1   | no               |
| `tomli`         | 2.4.1   | no               |

Three requirements pytest declares are already satisfied at the inventory's versions:
`packaging` 26.3, `Pygments` 2.11.2 and `typing_extensions` 4.16.0. So the measurement did
not fail, and what shipped is the plain install layer above. The fallback, a virtual
environment at `/opt/pytest` built `--system-site-packages` and invoked by absolute path,
was not needed and is not built. Installing the five with `--no-deps` adds exactly those
five lines to the image's `pip freeze` and changes no other line.
`tests/integration/test_pytest_image.py` asserts that against both real images, and
`tests/unit/test_environments.py` asserts the lists do not overlap without a daemon.

## The container

One container per invocation, one pytest process in it, nothing between the two.

| Host path       | Container path | Mode | Why                          |
| --------------- | -------------- | ---- | ---------------------------- |
| the plugin root | `/work/plugin` | rw   | The tree the suite runs over |

The plugin root is the nearest ancestor of the path argument holding
`.claude-plugin/plugin.json`, resolved exactly as every backend resolves it, and the target
pytest is given is that path relative to it. A path with no plugin root above it is an
error.

The mount is read-write, unlike a `run --docker`. pytest writes `.pytest_cache` and
`__pycache__` beside a suite on a laptop, and a read-only mount would change what a suite
does. The container runs as the host uid and gid, so what pytest writes into the tree
belongs to the developer and not to root. A `--junitxml` in the tail therefore needs nothing
from this package: the report lands in the tree like any other file the suite writes.

What is deliberately absent, and why:

| Absent                                | Why                                                        |
| ------------------------------------- | ----------------------------------------------------------- |
| The two credential mounts             | There is no model call, so there is nothing to authenticate |
| `--security-opt`                      | There is no `Bash` grant, so no OS sandbox starts           |
| The harness enablement variable       | The harness is not in the path                              |
| `--network`                           | A session has network. Cutting it would fail a test here that passes there |
| A log mount, a run directory, `env.txt`, `latest` and `--out` | Those hold `aggregate-result.json`, which pytest does not produce |
| `PYTHONPATH`                          | The image sets its own, for pyuno. Overwriting it would remove `import uno` from the runtime this reproduces |

The working directory is the plugin root, so pytest's rootdir is the plugin root and the
consumer's own `conftest.py`, `pytest.ini` or `pyproject.toml` there is the one that is
read. How a test imports the code it tests is the consumer's, decided by those files.

The base image already carries an extra root CA when the host that built it supplied one,
so anything in the container that reads the system store trusts it. `NODE_EXTRA_CA_CERTS`
is passed as a run passes it, because Node carries its own root store. See
[docker.md](docker.md).

## Exit codes

pytest's exit code is returned unchanged. Not remapped, not collapsed, not interpreted.

| Code | Means                          |
| ---- | ------------------------------ |
| 0    | every test passed              |
| 1    | a test failed                  |
| 2    | interrupted                    |
| 3    | an internal pytest error       |
| 4    | a pytest usage error           |
| 5    | no test was collected          |

`5` stays `5`. A red suite is a result, not an error, so nothing in this package raises on
an exit code. Every code the CLI defines for itself is reachable only before the container
starts, on a parse failure or a failed preflight: an unreachable daemon or an absent image
raises before any container starts.

## The one backend

There is no `test --venv` and no `test --cowork`. The mirror reproduces the interpreter and
the wheels only, so a suite that touches LibreOffice, pandoc, tesseract or a font passes
there and fails in a session. CoWork exposes no route to run a process that is not an agent
turn. See [environments.md](environments.md) and [approaches.md](approaches.md).

The backend flag is still required and still has no default, so the surface reads the same
on every verb.

`test` is not a fourth backend. A backend runs an eval and returns a result document; this
returns an exit code.

## What the consumer provides

A `tests/` directory in the plugin, holding a pytest suite. One plugin root carries both
`evals/` and `tests/`, and target resolution reaches each without a rule of its own.

That directory imports pytest, which is not on the CoWork image. It is not shipped code and
is never loaded in a session, so the CoWork wheel set does not bind it. What the wheel set
does bind is the code under test the suite imports. See [library.md](library.md).

A junit report, a coverage report and a cadence are the consumer's. The pytest tail is the
route to the first two, and the tree is writable.
