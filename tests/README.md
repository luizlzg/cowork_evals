# tests

Deterministic tests for this repository's own code. Python 3.14 under `.venv`, run by
`scripts/test.sh`. Scope as each piece is built: the environments, the CLI's option surface
and backend mapping, the result gate, the case validator, the CoWork driver and its grader.

These are not evals. An eval needs a model in the loop. If a failure can be caught by
pytest, it is not an eval.

| File                   | Covers                                                     | Exists |
| ---------------------- | ---------------------------------------------------------- | ------ |
| `test_environments.py` | Both interpreters, the two requirements files, the scripts | yes    |
| `test_parity.py`       | Recorded container probes against `docs/runtime.md`        | no     |

One file per unit under test, named after the unit and not after the scenario. Fixtures go
under `tests/data/`. A test never starts a live eval run, a container, or a CoWork session:
it asserts over recorded output, and `--dry-run` is how the command line is asserted over
without spending money.

Everything in this repository is 3.14, tests included, and ruff targets `py314`. The 3.10
constraint belongs to the code a consumer points the command at, not to anything here. See
[../docs/library.md](../docs/library.md).
