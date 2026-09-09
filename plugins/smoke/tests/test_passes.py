"""The trivial passing case.

`tests/integration/test_pytest_image.py` runs this file alone to prove exit 0 over a suite
that asserts nothing about the runtime. `test_runtime.py` beside it proves the runtime;
this one proves only that a green suite is green.
"""


def test_it_passes():
    assert True
