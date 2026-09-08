# tests

Tests for this repository's own code. Python 3.14 under `.venv`, run by `scripts/test.sh`.
Scope as each piece is built: the environments, the CLI's option surface and backend
mapping, the result gate, the case validator, the CoWork driver and its grader.

These are not evals. An eval needs a model in the loop. If a failure can be caught by
pytest, it is not an eval.

## Two tiers

| Tier        | Lives in             | Selection        | Needs                                              | Cost                              |
| ----------- | -------------------- | ---------------- | -------------------------------------------------- | --------------------------------- |
| Unit        | `tests/unit/`        | the default      | the two built environments, nothing else           | under a second, spends nothing    |
| Integration | `tests/integration/` | `-m integration` | a real CoWork profile, or a daemon and the built image | a VM boot and a permanent session, or an eval run |

The directory is the tier. `tests/integration/conftest.py` marks everything under it
`integration`, so a new file there cannot be left unmarked and cannot land in the default
selection by accident.

```sh
scripts/test.sh                                # unit
scripts/test.sh -m integration                 # every real-system test, the live run included
scripts/test.sh -m "integration and not live"  # the real-system tests that spend nothing
```

Run the integration tier at the end of a plan, and after a merge into `main`. The
deselection is in `pyproject.toml`.

No test is skipped, in either tier. A selected test runs and either passes or fails. An
unbuilt environment, an unconfigured profile and an empty profile are failures, not skips.
A skipped test reports as a pass and hides the thing it was written to catch.

| File                              | Covers                                                     | Exists |
| --------------------------------- | ---------------------------------------------------------- | ------ |
| `unit/test_environments.py`       | Both interpreters, the two requirements files, the scripts | yes    |
| `unit/test_config.py`             | `cowork_evals.yaml` and the `Config` it produces           | yes    |
| `unit/test_cowork.py`             | The CoWork driver: reading, refusing, submitting, waiting  | yes    |
| `unit/test_env.py`                | `.env` and the three settings layers                       | yes    |
| `unit/test_harness.py`            | The `claude plugin eval` argument list                     | yes    |
| `unit/test_docker.py`             | The image digest, and the build, login and run argument lists | yes |
| `unit/test_parity.py`             | Recorded container probes against the image inventory      | yes    |
| `integration/test_cowork.py`      | The same driver against a real profile and a real run      | yes    |
| `integration/test_docker.py`      | The built image, its mounts, its sandbox and one real eval run | yes |

One file per unit under test, named after the unit and not after the scenario. A unit tested
in both tiers keeps its name in both directories, which is why `pyproject.toml` sets
`--import-mode=importlib`: two files may share a basename, and neither directory carries an
`__init__.py`. Fixtures go under `tests/data/`, and `tests/conftest.py` holds what both
tiers share. No test in the default selection starts a live eval run, a container or a
CoWork session: it asserts over recorded output, and `--dry-run` is how the command line is
asserted over without spending money.

A CoWork session fixture is written by hand, never copied from a profile. A copied session
directory carries an account identifier, a profile identifier, a session identifier and the
prompts of a real account, and the public repository rule in [../README.md](../README.md)
covers all four. The record shapes a fixture imitates are in
[../docs/cowork_desktop.md](../docs/cowork_desktop.md).

## No mocks

No mock, fake, stub, patch or injected seam appears anywhere in this repository, and no
production parameter exists to accept one. A test that asserts against a stand-in asserts
against itself.

A hand-written session directory is not a mock. It is input on disk, and the reader that
parses it is the real one: it picks the newest transcript by modification time, pairs a
`tool_use` to its `tool_result` by id, drops an orphan result, excludes a `thinking` block
from turn text, reads `message.content` as either a string or a list, and tolerates a
partial last line. Every expected value in a unit test is a literal, never a value computed
by the code that wrote the fixture.

What a fixture cannot prove is that the application still writes that shape. The record
shapes come from a probe recorded in [../docs/cowork_desktop.md](../docs/cowork_desktop.md),
and a release can change them. The integration tier is what closes that gap:

| Cannot be reached without the application | Paid by |
| ------------------------------------------ | --------- |
| That the reader matches a real profile    | `test_the_reader_handles_every_session_in_a_real_profile`, marked `integration` |
| That the deep link prefills, that the Return submits, that `completed` is written | `test_a_live_run_returns_the_marker`, marked `integration` and `live` |

Everything else is real code over real files: the loader parses YAML written to disk, and
the readers, the discovery, the attribution, the completion signal and the run log all run
against session directories the test writes and then reads back.

### The container tier's preconditions

`integration/test_docker.py` needs a reachable daemon, the image already built by
`scripts/image.sh`, and the login already made by `scripts/login.sh`. Nothing there builds
or logs in: a test that builds its own subject reports a build as a pass, and hides a long
build inside a test run. Three of its tests read the credential, and a missing one fails
them rather than skipping them.

### The live marker

Three integration tests submit a real run. The CoWork one costs a VM boot, counts against
the driver's rate ceiling and leaves a permanent session in the signed-in account. The two
container ones cost the model calls their case makes. All three carry `live` as well as
`integration`. An integration run that must not spend selects
`-m "integration and not live"`.

The CoWork one needs the macOS Accessibility grant, a signed-in CoWork, the desktop
application already running, and `cowork_evals.yaml` naming the active profile. It fails,
and does not skip, when no profile is configured. Nothing steals focus while it runs. See
[../docs/cowork_desktop.md](../docs/cowork_desktop.md) for the authorizations. The two
container ones need a credential route, and fail without one.

Everything in this repository is 3.14, tests included, and ruff targets `py314`. The 3.10
constraint belongs to the code a consumer points the command at, not to anything here. See
[../docs/library.md](../docs/library.md).
