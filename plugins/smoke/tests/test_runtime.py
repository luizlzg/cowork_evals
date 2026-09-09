"""What the container is, asserted from inside it.

A fixture for `tests/integration/test_pytest_image.py`, not a suite. It exists to prove
that the container `cowork_evals test` runs is the CoWork image and not a plain Python
one, so each assertion is one that a plain image fails.

This file runs on the container's 3.10 interpreter, never under `.venv`, and is outside
`testpaths`, so `scripts/test.sh` does not collect it. Each import is inside the test that
needs it, so a missing one fails that test by name rather than erroring the collection.
"""

import sys


def test_the_interpreter_is_3_10():
    assert sys.version_info[:2] == (3, 10)


def test_uno_imports_from_the_libreoffice_program_directory():
    """pyuno resolves only from the deb set's own directory, which the image puts on
    PYTHONPATH. See docs/docker.md."""
    import uno

    assert uno.__file__.startswith("/opt/libreoffice/")


def test_a_pinned_cowork_wheel_imports():
    """pikepdf is one of the pins in requirements.txt and binds qpdf. No plain image
    carries it."""
    import pikepdf

    assert hasattr(pikepdf, "Pdf")
