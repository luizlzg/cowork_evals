# The test command

## Summary

`cowork_evals test` runs a consumer's own pytest suite inside a container built from the CoWork
image, so the code a plugin ships is exercised on the interpreter and the wheel set a session
has rather than on the laptop's. It is not an eval: no model, no harness, no case tree, no
grader, no result document and no verdict. pytest collects, runs and reports, and this package
supplies only the runtime, one mount and the exit code, unchanged. Use it on code destined for
a skill, before an eval is written over it.

- **Once the container starts, this package adds nothing and interprets nothing.**
- **Two images, one layer apart.** The eval image never carries pytest, so the inventory stays
  exact.
- **One mount, read-write.** pytest writes beside a suite, and the container runs as the host
  uid.
- **One backend.** `--docker` is the only one, and there is no `test --cowork`.

The verb and its options are [cli.md](cli.md). The image this one is built over is
[docker.md](docker.md), and the inventory that image reproduces is [runtime.md](runtime.md).
`scripts/cowork_pytest.sh` is the development task behind the same two images, and
`scripts/README.md` owns it.

## Transparency

| Rule                                                                                   |
| -------------------------------------------------------------------------------------- |
| No pytest option is added. Not `-p no:cacheprovider`, not `-q`, not a colour flag       |
| No pytest plugin is installed, `pytest-timeout` included                                |
| No pytest environment variable is set. Not `PYTHONDONTWRITEBYTECODE`, not `PYTHONPATH`  |
| The exit code is pytest's, unchanged                                                    |
| A raw pytest argument tail is forwarded verbatim, after the resolved target             |

Whatever `pytest <path>` does on a laptop is what it does here, on the CoWork runtime instead
of the laptop's.

There is no timeout. A caller that wants one passes it in the tail.

## Two images

| Tag                          | Is                                | Built by                                        |
| ---------------------------- | --------------------------------- | ----------------------------------------------- |
| `cowork-evals:<digest>`      | The CoWork image an eval runs in  | `setup --docker`, or `scripts/image.sh`         |
| `cowork-evals-test:<digest>` | That image plus one install layer | `setup --docker`, or `scripts/cowork_pytest.sh` |

The eval image never carries pytest. A package installed for the test runner would show in the
eval image's `pip freeze` and would be a package a session does not have, so `scripts/parity.sh`
and the inventory in [runtime.md](runtime.md) both stay exact.

The test digest is the sha256 of the base image's digest, `Dockerfile.pytest`,
`requirements_test.txt` and the resolved `docker.platform`, truncated to twelve characters. The
base digest goes in first, so a rebuilt base is a different test tag rather than a stale hit
over an old base. There is no `latest`, for the reason in [docker.md](docker.md).

One module per image. `src/cowork_evals/docker/__init__.py` owns the image the harness runs in
and `src/cowork_evals/docker/pytest_image.py` owns the image pytest runs in. Each owns its
Dockerfile, its digest, its argument lists, its check and the one command that fixes an absent
image. The class is `PytestImage` and not `TestImage`, because pytest collects a class named
`Test*` and would warn on the second name in every test module that imported it.

`Dockerfile.pytest` declares `ARG BASE_TAG` before its `FROM` and nothing else, so it names no
image of its own. That argument has no default, so BuildKit prints `InvalidDefaultArgInFrom` on
every build. Giving it one would be a default base tag, which is the stale base this design
prevents, so the warning stays.

## The pinned list

`src/cowork_evals/data/requirements_test.txt` holds pytest and every package it needs that the
inventory does not carry, each pinned to an exact version. A package already in the inventory is
never listed, whatever version pytest would prefer. The layer installs the file with `--no-deps`:
a bare `pip install pytest` may move an inventory pin, and a moved pin voids what the image
claims to be.

Which of the three requirements files a new pin goes in is [environments.md](environments.md),
which owns that split.

`pip install --dry-run pytest` inside the image on `linux/arm64` resolves pytest 9.1.1 and would
install five packages and move none:

| Package          | Version | In the inventory |
| ---------------- | ------- | ---------------- |
| `pytest`         | 9.1.1   | no               |
| `pluggy`         | 1.6.0   | no               |
| `iniconfig`      | 2.3.0   | no               |
| `exceptiongroup` | 1.3.1   | no               |
| `tomli`          | 2.4.1   | no               |

Three further requirements pytest declares are already satisfied at the inventory's versions:
`packaging` 26.3, `Pygments` 2.11.2 and `typing_extensions` 4.16.0. Installing the five with
`--no-deps` adds exactly those five lines to the image's `pip freeze` and changes no other line.
`tests/integration/test_pytest_image.py` asserts that against both real images, and
`tests/unit/test_environments.py` asserts the lists do not overlap without a daemon.

## The container

One container per invocation, one pytest process in it, nothing between the two.

| Host path       | Container path | Mode | Is                           |
| --------------- | -------------- | ---- | ---------------------------- |
| the plugin root | `/work/plugin` | rw   | The tree the suite runs over |

The plugin root is the one [cli.md](cli.md) resolves from the path argument, exactly as every
backend resolves it, and the target pytest is given is that path relative to it.

The mount is read-write, unlike a `run --docker`. pytest writes `.pytest_cache` and `__pycache__`
beside a suite on a laptop, and a read-only mount would change what a suite does. The container
runs as the host uid and gid, so what pytest writes into the tree belongs to the developer and
not to root. A `--junitxml` in the tail therefore needs nothing from this package: the report
lands in the tree like any other file the suite writes.

What is deliberately absent:

| Absent                                | Why                                                                        |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| The two credential mounts             | There is no model call, so there is nothing to authenticate                |
| `--security-opt`                      | There is no `Bash` grant, so no OS sandbox starts                          |
| The harness enablement variable       | The harness is not in the path                                             |
| `--network`                           | A session has network. Cutting it would fail a test here that passes there |
| A log mount, a run directory, `env.txt`, `latest` and `--out` | Those hold `aggregate-result.json`, which pytest does not produce |
| `PYTHONPATH`                          | The image sets its own, for pyuno. Overwriting it would remove `import uno` from the runtime this reproduces |

`HOME` is set to a writable container path, so a tool that wants one finds it. The working
directory is the plugin root, so pytest's rootdir is the plugin root and the consumer's own
`conftest.py`, `pytest.ini` or `pyproject.toml` there is the one that is read. How a test imports
the code it tests is the consumer's, decided by those files.

The base image already carries an extra root CA when the host that built it supplied one, so
anything in the container that reads the system store trusts it. `NODE_EXTRA_CA_CERTS` is passed
as a run passes it, because Node carries its own root store. See [docker.md](docker.md).

## Exit codes

pytest's exit code is returned unchanged. Not remapped, not collapsed, not interpreted.

| Code | Means                                    |
| ---- | ---------------------------------------- |
| 0    | every test passed                        |
| 1    | a test failed                            |
| 2    | interrupted, a collection error included |
| 3    | an internal pytest error                 |
| 4    | a pytest usage error                     |
| 5    | no test was collected                    |

`5` stays `5`, and a file that does not parse on 3.10 stays `2`. A red suite is a result, not an
error, so nothing in this package raises on an exit code. Every code the CLI defines for itself
is reachable only before the container starts, on a parse failure or a failed preflight: an
unreachable daemon or an absent image raises before any container starts.

## The one backend

`--docker` is the only backend, and there is no `test --cowork`. CoWork exposes no route to run
a process that is not an agent turn.

Running a suite on the host under the 3.10 mirror is not offered either. The mirror reproduces
the interpreter and the wheels only, so a suite that touches LibreOffice, pandoc, tesseract or a
font passes there and fails in a session. See [environments.md](environments.md) and
[approaches.md](approaches.md).

The backend flag is still required and still has no default, so the surface reads the same on
every verb. `test` is not a third backend: a backend runs an eval and returns a result document,
and this returns an exit code.

## What the consumer provides

A `tests/` directory in the plugin, holding a pytest suite. One plugin root carries both `evals/`
and `tests/`, and target resolution reaches each without a rule of its own.

That directory imports pytest, which is not on the CoWork image. It is not shipped code and is
never loaded in a session, so the CoWork wheel set does not bind it. What the wheel set does bind
is the code under test the suite imports. See [library.md](library.md).

A junit report, a coverage report and a cadence are the consumer's. The pytest tail is the route
to the first two, and the tree is writable.
