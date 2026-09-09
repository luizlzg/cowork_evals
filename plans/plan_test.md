# Plan: the test command

Branch `feat/test`. Seven phases, one commit each.

A consumer's Python tests, run inside the CoWork image. No model, no harness, no case tree,
no grader, no result document and no gate. pytest collects, runs and reports, and the only
thing this plan supplies is the runtime it runs in.

**Transparency is the requirement.** Once the container starts, this package adds nothing
and interprets nothing. It passes no pytest option of its own, sets no pytest environment
variable, and returns the exit code pytest produced, unchanged. Whatever `pytest <path>`
does on a laptop is what it does here, on the CoWork runtime instead of the laptop's.
Anything else is a surprise, and a surprise in a test runner is a defect.

The rule that separates it from every other plan is already written in
[`../tests/README.md`](../tests/README.md): if a failure can be caught by pytest, it is not
an eval. Everything the other five plans build is the other half of that sentence.

## What it waits on

Nothing. It needs the container image, which plan 2 built, and
`src/cowork_evals/docker/__init__.py`, which holds it. Every phase here is executable today.

The `cowork_evals test` verb is built by [`plan_cli.md`](plan_cli.md), in its phase 5 and
its phase 6, alongside the other four. A fifth verb is a parser entry and a dispatch, and
that plan owns both. It calls `PytestImage.check()` and `PytestImage.run()` and nothing
else here.

This plan is therefore the mechanism and its documentation. `scripts/cowork_pytest.sh` is
how it is reached until the command exists, exactly as `scripts/image.sh` was for the
container backend before it.

## Scope

| Builds                                          | Is                                                            |
| ----------------------------------------------- | ------------------------------------------------------------- |
| `src/cowork_evals/data/requirements_test.txt`   | The pins the test layer installs, and nothing else            |
| `src/cowork_evals/docker/Dockerfile.pytest`     | One layer over the eval image                                 |
| `src/cowork_evals/docker/pytest_image.py`       | `PytestImage`: the digest, the build, the check, the run      |
| `scripts/cowork_pytest.sh`                      | The development route, until the verb exists                  |
| `plugins/smoke/tests/`                          | The fixture the integration tier runs                         |
| `docs/cowork_test.md`                           | The mechanism: the image, the container, the exit codes       |
| `tests/unit/test_pytest_image.py`, `tests/integration/test_pytest_image.py` | [`../tests/README.md`](../tests/README.md) |

## Out of scope

| Not built                                            | Belongs to                                    |
| ---------------------------------------------------- | --------------------------------------------- |
| The `cowork_evals test` verb, its parser and its dispatch | [`plan_cli.md`](plan_cli.md), phases 5 and 6 |
| Running a consumer's tests on the mirror or on CoWork | nobody. The rule is in the decisions below    |
| A test runner other than pytest                      | nobody                                        |
| Any test over a shipped plugin                       | the consumer repository                       |
| A junit report, a coverage report, a cadence          | the consumer. The pytest tail is the route, and the tree is writable |
| The 3.10 and import check over the code under test    | nowhere yet. Unchanged by this plan           |

## Decisions

Each row is a statement no file makes yet. Phase 7 writes every one of them into
[`../docs/cowork_test.md`](../docs/cowork_test.md) or
[`../docs/cli.md`](../docs/cli.md).

| Decision                                                                                     | Settled by    |
| ---------------------------------------------------------------------------------------------- | ------------- |
| Two images, not one. `cowork-evals:<digest>` is unchanged and is what an eval runs in; `cowork-evals-test:<digest>` is `FROM` it plus one install layer | the developer |
| The eval image never carries pytest, so `scripts/parity.sh` and `tests/unit/test_parity.py` are untouched and the inventory in [`../docs/runtime.md`](../docs/runtime.md) stays exact | this plan |
| The test layer installs with `--no-deps` against an explicit pinned list. `pip install pytest` may move a pin that is in the inventory, and a moved pin voids the verb's whole claim | this plan |
| The test image adds packages and moves none. A unit test asserts that its `pip freeze`, minus exactly the names in `requirements_test.txt`, equals the eval image's | this plan |
| One module per image. `docker/__init__.py` owns the image the harness runs in, `docker/pytest_image.py` owns the image pytest runs in, and each owns its Dockerfile, digest, argument lists and check | this plan |
| The class is `PytestImage`, not `TestImage`. pytest collects a class named `Test*`, so the second name warns on import into a test module and is never collected | this plan |
| No pytest plugin is installed, `pytest-timeout` included. A timeout is a restriction the developer did not ask for, and a caller that wants one passes it | this plan |
| The container runs with the default network. A session has network, so cutting it would fail a test here that passes there | this plan |
| No credential mount, no `--security-opt` line and no enablement variable. There is no model call and no `Bash` grant, so none of the three has a reason | this plan |
| pytest's exit code is returned unchanged. Not remapped, not collapsed, not interpreted. `5`, no test collected, stays `5` | the developer |
| Every code below 128 that the CLI defines for itself is reachable only before the container starts, on a parse or a preflight failure. Once the container starts, the code is pytest's | this plan |
| No pytest option, plugin or environment variable is added by this package. Not `-p no:cacheprovider`, not `PYTHONDONTWRITEBYTECODE`, not `-q`, not a colour flag | this plan |
| The plugin root is mounted read-write, unlike `run --docker`. pytest writes `.pytest_cache` and `__pycache__` on a laptop, and a read-only mount would change what a suite does | this plan |
| The container runs as the host uid and gid, so what pytest writes into the tree is owned by the developer and not by root | this plan |
| No run directory, no `env.txt`, no `latest`, no gate and no `--out`. Those exist to hold `aggregate-result.json`, which pytest does not produce, and the tree is writable, so a `--junitxml` in the pytest tail needs nothing from this package | this plan |
| A raw pytest argument tail is forwarded. `run` forbids one because the harness runs on two backends of three; `test` has one backend, so the objection does not apply | this plan |
| There is no `test --venv` and no `test --cowork`. The mirror reproduces the interpreter and the wheels only, and CoWork exposes no route to run a process that is not an agent turn | this plan |
| The backend flag is still required and still has no default, so the surface reads the same on every verb | this plan |
| `setup --docker` builds both images. `check --docker` reports both, and the credential, which the `test` preflight does not read | this plan |
| A consumer's `tests/` directory imports pytest, which is not on the CoWork image. It is not shipped code and is never loaded in a session, so the wheel set does not bind it | this plan |
| How a test imports the code it tests is the consumer's. The working directory and pytest's rootdir are the plugin root, so the consumer's own `conftest.py`, `pytest.ini` or `pyproject.toml` there decides it. This package sets no `PYTHONPATH`: the image already sets one, for pyuno | this plan |
| `requirements_test.txt` is a third requirements file, and the rule that decides which file a pin goes in is written into [`../docs/environments.md`](../docs/environments.md), which owns that split | this plan |
| `test` is not a fourth backend. A backend runs an eval and returns a result document, and this returns an exit code | this plan |

## Constraints

- Python 3.14 in this package, ruff `target-version = "py314"`. The code inside the
  container is the consumer's and is 3.10.
- No dependency is added to `pyproject.toml`. `hashlib`, `subprocess` and `pathlib` are the
  standard library, and `Docker` already exists.
- `PytestImage` does no work at construction, so its digest answers on a machine with no
  daemon. That is `Docker`'s rule and it holds here.
- Nothing here names a log directory, writes a symlink, prunes or decides pass and fail.
  Printing and `sys.exit` stay in `cli.py`. `scripts/cowork_pytest.sh` prints its own one
  line and exits on the container's code.
- No mock, fake, stub, patch or injected seam. The unit tier asserts argument lists and
  digests without a daemon; the integration tier runs real containers.
- No fixture and no example in a document carries a machine name, a user name, a home
  directory path or an account identifier. [`../README.md`](../README.md).

## Phase 1: Measure the install

Nothing is written in this phase except the pinned list it produces and the snapshot in
`docs/cowork_test.md`. It is separate because every later phase depends on its answer.

The inventory in [`../docs/runtime.md`](../docs/runtime.md) already carries
`packaging==26.3` and `attrs==21.2.0`. pytest on 3.10 also needs `pluggy`, `iniconfig`,
`exceptiongroup` and `tomli`, none of which is in the inventory.

- [x] Run `pip install --dry-run pytest` inside a container off the current
      `cowork-evals:<digest>`, and record what it would install and what it would move.
- [x] `src/cowork_evals/data/requirements_test.txt`: `pytest` and every package the previous
      box says is absent from the image, each pinned to an exact version. A package already
      in the inventory is never listed, whatever version pytest would prefer.
- [ ] The measurement, with its capture date, goes into `docs/cowork_test.md` in phase 7 as
      a snapshot.
- [ ] **If the measurement fails**, meaning no pytest version is satisfied by the inventory's
      `packaging` and `attrs`, the pin is still not moved. What ships instead is a virtual
      environment at `/opt/pytest`, built `--system-site-packages`, holding pytest and its
      needs and invoked by absolute path. The image's own `site-packages` is then untouched,
      and every later phase changes only in the command the container runs. Record which of
      the two shipped, and why, in `docs/cowork_test.md`.

## Phase 2: The image

`src/cowork_evals/docker/Dockerfile.pytest` and `src/cowork_evals/docker/pytest_image.py`.

- [ ] `Dockerfile.pytest`: `FROM ${BASE_TAG}`, then one `COPY` of
      `requirements_test.txt` and one `pip install --no-deps --no-cache-dir -r` over it. It
      declares `ARG BASE_TAG` and nothing else, and its build context is the same `data/`
      directory the base image uses.
- [ ] `PytestImage` in `pytest_image.py`, constructed from a `Config` like `Docker`, holding
      a `Docker` for the base tag. Frozen configuration, no work at construction.
- [ ] `digest`: the sha256 of the base image's digest, `Dockerfile.pytest`,
      `requirements_test.txt` and the platform, truncated to `DIGEST_LENGTH`. A rebuilt base
      image is therefore a different test tag, never a stale hit over an old base.
- [ ] `tag`: `cowork-evals-test:<digest>`. There is no `latest`.
- [ ] `build_argv()` and `build()`, mirroring `Docker`. The base image being absent is a
      failure naming `Docker.tag`, not an implicit base build.
- [ ] `image_is_present()` and `check()`, returning the same `(Condition, message)` pairs
      `Docker.check()` returns, reusing `Condition` and `remedy` from `docker/__init__.py`.
      `Condition.CREDENTIAL` is never returned: there is no login in this path.
- [ ] `tests/unit/test_environments.py` grows: `requirements_test.txt` lists no package that
      `requirements.txt` already pins. That is the assertion that keeps the install additive,
      checked without a daemon.
- [ ] `tests/unit/test_pytest_image.py`: the digest changes when the base digest, the
      Dockerfile, the pinned list or the platform changes, and is stable otherwise; the tag
      shape; the build argument list; and that `check()` never returns `CREDENTIAL`. No
      daemon is started.

## Phase 3: The run

Still `pytest_image.py`. One container, one pytest invocation, nothing between the two.

- [ ] `run_argv(target, *, pytest_args=())`: `docker run --rm`, the platform, the host uid
      and gid, `HOME`, the extra CA environment when one is configured, the plugin root
      mounted read-write at `CONTAINER_PLUGIN`, `-w CONTAINER_PLUGIN`, the tag, then
      `python3 -m pytest <container target> <pytest args>`.
- [ ] That command line carries no option this package chose. Everything after
      `python3 -m pytest` is the resolved target and then the caller's tail, verbatim and in
      that order.
- [ ] No `PYTHONPATH` is set. The image sets its own, for pyuno, and overwriting it would
      remove `import uno` from the runtime this verb claims to reproduce. The working
      directory is the plugin root, so pytest's rootdir is the plugin root and the
      consumer's configuration file there is the one that is read.
- [ ] The plugin root and the container-side relative target are resolved with
      `docker.plugin_root`, which is `cases.plugin_root`. Every backend resolves a target the
      same way and this one does not get its own rule.
- [ ] No credential mount, no `--security-opt`, no enablement variable, no `--network` flag
      and no log mount.
- [ ] `extra_ca_env_argv` and `plugin_root` are reused from `docker/__init__.py`. Neither is
      reimplemented here.
- [ ] `run(target, *, pytest_args=()) -> int` runs it with the terminal inherited, so
      pytest's output reaches it as pytest wrote it, and returns
      `subprocess.run(...).returncode` unchanged. It maps nothing, prints nothing of its own
      and raises on no exit code. A red suite is a result, not an error.
- [ ] A daemon that cannot be reached, or an absent image, raises `DockerError` before any
      container starts. That is a precondition, and the caller turns it into exit 3.
- [ ] `tests/unit/test_pytest_image.py` grows: the argument list with and without a pytest
      tail, for a plugin root target and for a subdirectory target; the absence of the
      credential mounts, the sandbox options, the enablement variable and any pytest option;
      and that the mount is `rw`.

## Phase 4: The development script

`scripts/cowork_pytest.sh`. It is `scripts/image.sh` for this image, and it goes away as a
route for a consumer the moment the verb exists. It stays as a development task.

- [ ] `scripts/cowork_pytest.sh [--check | --recreate] [<path>] [-- <pytest args>]`,
      following the conventions in [`../scripts/README.md`](../scripts/README.md):
      `set -euo pipefail`, `lib.sh` on the second line, the header block as the help text,
      `die` for a one-line failure.
- [ ] With no flag and a path, it verifies the image and runs the container, exiting on
      pytest's code unchanged. `--check` verifies the digest and writes nothing.
      `--recreate` builds with `--no-cache`. A missing image is a `die` naming the script
      with no arguments, never an implicit build.
- [ ] A row for it in [`../scripts/README.md`](../scripts/README.md), and a line saying it
      is the image's half of what `scripts/image.sh` is for the eval image. The name carries
      the `cowork_` prefix the other two runtime scripts carry, so it is not read as a
      sibling of `scripts/test.sh`, which runs this repository's own tests.
- [ ] `tests/unit/test_environments.py` grows a row for the new script, alongside the ones it
      already asserts.

## Phase 5: The fixture

`plugins/smoke/tests/`. It is what the integration tier runs, and it exists to prove the
container is the CoWork image and not a plain Python container.

- [ ] `plugins/smoke/tests/test_runtime.py`: `sys.version_info[:2] == (3, 10)`, an import of
      `uno`, which resolves only from the LibreOffice deb set's own program directory, and an
      import of one wheel from `requirements.txt` that no plain image carries.
- [ ] `plugins/smoke/tests/test_fails.py`: one test that fails on purpose, used by the
      integration tier to prove exit 1. It is outside `testpaths`, so `scripts/test.sh` never
      collects it.
- [ ] The directory sits in the plugin that already holds `evals/`, so one plugin root
      carries both and the target resolution reaches each without a rule of its own.
- [ ] A line in [`../plugins/README.md`](../plugins/README.md) saying what the directory is
      and that it is a fixture, not a suite.

## Phase 6: The integration tier

`tests/integration/test_pytest_image.py`. It needs a reachable daemon and the test image
already built by `scripts/cowork_pytest.sh`. It builds nothing, and a missing precondition
fails it rather than skipping it. It spends nothing and is not `live`: there is no model in
it.

- [ ] The passing fixture returns 0, and its output names the three assertions.
- [ ] The failing fixture returns 1.
- [ ] A path that collects no test returns 5, pytest's own code for it, and not 1.
- [ ] `python3 -V` inside the container reports the version
      [`../docs/runtime.md`](../docs/runtime.md) records.
- [ ] A test that writes a file into the tree succeeds, and the file is on the host owned by
      the developer, not by root.
- [ ] `-- --junitxml=report.xml` in the tail leaves the report in the plugin root on the
      host. Nothing in this package arranged for it.
- [ ] The test image's `pip freeze`, minus exactly the names in `requirements_test.txt`,
      equals the eval image's `pip freeze`. This is the assertion the whole plan rests on.
- [ ] A row for the file in [`../tests/README.md`](../tests/README.md)'s table, and its
      preconditions in the section that holds the container tier's.

## Phase 7: Documentation

One commit. Every decision above lands in a file that owns it, and nothing is restated.

- [ ] `docs/cowork_test.md`, new. What the verb is for, the two images and the rule that
      splits them, the pinned list and the phase 1 snapshot with its capture date, the
      container's mounts and what is deliberately absent from them, the exit codes, and the
      rule that keeps the mirror and CoWork out of it. It links
      [`../docs/docker.md`](../docs/docker.md) for the base image and
      [`../docs/runtime.md`](../docs/runtime.md) for the inventory, and restates neither.
- [ ] `docs/README.md`: a row for `cowork_test.md` in the index table, and a sentence in
      "The run, and the mechanisms" placing it as a mechanism file. The opening paragraph
      says this repository runs evals; it gains the second thing it runs.
- [ ] `docs/cli.md` is not touched here. The verb's surface is written by
      [`plan_cli.md`](plan_cli.md)'s phase 8, which owns that file, and the statements it
      writes are the `test` rows of this plan's decision table.
- [ ] `docs/docker.md`: one sentence saying the eval image carries no pytest and why, linking
      `cowork_test.md`. The parity section is unchanged and says so.
- [ ] `docs/environments.md`: "Two requirements files" becomes three, and the table gains
      `requirements_test.txt` with what it pins and what reads it. That section owns the
      split, so the rule deciding which of the three a new pin goes in is written there and
      nowhere else.
- [ ] `docs/approaches.md`: one sentence saying `test` is not a fourth backend, and why.
- [ ] `docs/running_evals.md`: two rows in the status table, for the test image and for the
      `test` verb, the second reading `no` until `plan_cli.md` builds it.
- [ ] `docs/library.md`: `requirements_test.txt`, `Dockerfile.pytest` and `pytest_image.py`
      in the "What ships" table, and a row in "Where state lives" for the test image tag.
      The "Where the restrictions are" table gains the consumer's `tests/`, which the wheel
      set does not bind.
- [ ] `CLAUDE.md`: the "Two kinds of code, two sets of rules" table gains a third row for a
      consumer's `tests/`, which runs in the test image on 3.10 and may import pytest. The
      "Two tiers of test" rule is about this repository's own tests and gains one sentence
      saying so, because the new verb runs a consumer's.
- [ ] `../README.md`, the repository index: the opening line and the "Using it" block. The
      package runs evals and runs a consumer's tests in the same runtime, and both go
      through one command.
- [ ] [`README.md`](README.md), the plan index: its row, its section and the renumbering are
      already written, ahead of this plan, so the index says what is being built while it is
      built. What is left here is the link to `docs/cowork_test.md`, which that file
      describes without linking until this phase creates it. The status becomes
      `implemented` when the branch merges.
