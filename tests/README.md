# tests

Deterministic tests for this repository's own code. Python 3.14 under `.venv`, run by
`scripts/test.sh`. Scope as each piece is built: the environments, the CLI's option surface
and backend mapping, the result gate, the case validator, the CoWork driver and its grader.

These are not evals. An eval needs a model in the loop. If a failure can be caught by
pytest, it is not an eval.

| File                   | Covers                                                     |
| ---------------------- | ---------------------------------------------------------- |
| `test_environments.py` | Both interpreters, the two requirements files, the scripts |

One file per unit under test, named after the unit and not after the scenario. Fixtures go
under `tests/data/`. A test never starts a live eval run, a container, or a CoWork session:
it asserts over recorded output, and `--dry-run` is how the command line is asserted over
without spending money.

Shipped code is 3.10 compatible while the test environment is 3.14. Ruff's
`target-version` carries that constraint, because the test run alone cannot.
