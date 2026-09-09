"""One test that fails on purpose.

`tests/integration/test_pytest_image.py` runs this file alone to prove that pytest's
exit 1 reaches the caller unchanged. It is outside `testpaths`, so `scripts/test.sh`
never collects it, and it is never run alongside `test_runtime.py`.
"""


def test_this_one_fails_on_purpose():
    assert 1 == 2, "this failure is the fixture"
