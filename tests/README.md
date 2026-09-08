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
under `tests/data/`. A test never starts a live eval run, a container, or a CoWork session:
it asserts over recorded output, and `--dry-run` is how the command line is asserted over
without spending money.

A CoWork session fixture is written by hand, never copied from a profile. A copied session
directory carries an account identifier, a profile identifier, a session identifier and the
prompts of a real account, and the public repository rule in [../README.md](../README.md)
covers all four. The record shapes a fixture imitates are in
[../docs/cowork_desktop.md](../docs/cowork_desktop.md).

The CoWork driver is tested through its `runner` seam, a callable the constructor takes.
Mocking and patching are not used.

Everything in this repository is 3.14, tests included, and ruff targets `py314`. The 3.10
constraint belongs to the code a consumer points the command at, not to anything here. See
[../docs/library.md](../docs/library.md).
