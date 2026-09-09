"""A pinned requirements file, read one way.

The mirror, the container and the tests all compare the same two files in
[data/](data/) against what an environment actually holds, so all three normalize a
distribution name here and nowhere else. `scripts/cowork_venv.sh` calls this through
`uv run` for the same reason: a shell that folds `foo__bar` to `foo--bar` reports drift
that is not there.

The convention is PEP 503, applied by `packaging`, which is this package's dependency and
not a second implementation of it.
"""

from __future__ import annotations

from packaging.utils import canonicalize_name


def normalize(name: str) -> str:
    """One distribution name, PEP 503 canonical: lower case, every run of `-_.` one `-`."""
    return str(canonicalize_name(name))


def pins(text: str) -> dict[str, str]:
    """A requirements file or a `pip freeze`, as canonical name to version.

    A line with no `==` is not a pin and is dropped, a comment included.
    """
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if "==" in line and not line.startswith("#"):
            name, _, version = line.partition("==")
            out[normalize(name)] = version.strip()
    return out
