# tests

Deterministic tests for this repository's own code. Python 3.14 under `.venv`, run by
`scripts/test.sh`. Scope as each piece is built: the environments, the CLI's option surface
and backend mapping, the result gate, the case validator, the CoWork driver and its grader.

These are not evals. An eval needs a model in the loop. If a failure can be caught by
pytest, it is not an eval.

| File                   | Covers                                                     | Exists |
| ---------------------- | ---------------------------------------------------------- | ------ |
| `test_environments.py` | Both interpreters, the two requirements files, the scripts | yes    |
| `test_config.py`       | `cowork_evals.yaml` and the `Config` it produces           | yes    |
| `test_prompt_lint.py`  | The deny-list linter, one refused prompt per rule          | yes    |
| `test_cowork.py`       | The CoWork driver: reading, refusing, submitting, waiting  | yes    |
| `test_parity.py`       | Recorded container probes against `docs/runtime.md`        | no     |

One file per unit under test, named after the unit and not after the scenario. Fixtures go
under `tests/data/`. No test in the default selection starts a live eval run, a container or
a CoWork session: it asserts over recorded output, and `--dry-run` is how the command line is
asserted over without spending money. The one test that does fire a session carries the
`live` marker and is deselected by default; see below.

A CoWork session fixture is written by hand, never copied from a profile. A copied session
directory carries an account identifier, a profile identifier, a session identifier and the
prompts of a real account, and the public repository rule in [../README.md](../README.md)
covers all four. The record shapes a fixture imitates are in
[../docs/cowork_desktop.md](../docs/cowork_desktop.md).

## No mocks

No mock, fake, stub, patch or injected seam appears anywhere in this repository, and no
production parameter exists to accept one. A test that asserts against a stand-in asserts
against itself.

What that costs, and how each cost is paid:

| Cannot be reached without the application    | Paid by                                    |
| --------------------------------------------- | -------------------------------------------- |
| Whether the reader matches a real profile    | `test_the_reader_handles_every_session_in_a_real_profile`, which reads the configured profile and skips when there is none |
| That the deep link prefills, that the Return submits, that `completed` is written | `test_a_live_run_returns_the_marker`, marked `live` |

Everything else is real code over real files: the loader parses YAML written to disk, the
linter is a pure function, and the readers, the discovery, the attribution, the completion
signal and the run log all run against session directories the test writes and then reads
back.

### The live marker

One test fires a real CoWork run. It costs a VM boot, counts against the driver's rate
ceiling and leaves a permanent session in the signed-in account, so it is deselected by
default in `pyproject.toml`. Run it deliberately:

```sh
scripts/test.sh -m live
```

It needs the macOS Accessibility grant, a signed-in CoWork, the desktop application already
running, and `cowork_evals.yaml` naming the active profile. It skips when no profile is
configured. Nothing steals focus while it runs. See
[../docs/cowork_desktop.md](../docs/cowork_desktop.md) for the authorizations.

Everything in this repository is 3.14, tests included, and ruff targets `py314`. The 3.10
constraint belongs to the code a consumer points the command at, not to anything here. See
[../docs/library.md](../docs/library.md).
