# tests

Deterministic tests for this repository's own code: the environments, the result gate, the
CoWork driver, the scripts. Python 3.14 under `.venv`, run by `scripts/test.sh`.

These are not evals. An eval needs a model in the loop and costs money. A test does not. If
a failure can be caught by pytest, it is not an eval.

| File                    | Covers                                                |
| ----------------------- | ----------------------------------------------------- |
| `test_environments.py`  | Both interpreters, the two requirements files, the scripts |

One file per unit under test, named after the unit and not after the scenario. Fixtures go
under `tests/data/`. A test never starts a live eval run, a container, or a CoWork session:
it asserts over recorded output.
