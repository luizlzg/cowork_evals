"""Every test under tests/integration/ is integration, whether or not it says so.

The marker is applied here so it cannot be forgotten on a new file. Selection stays
`-m integration`, which is what pyproject.toml deselects by default.

pytest_collection_modifyitems in a subdirectory conftest still receives every collected
item, so the hook filters by path.

It also holds the one configuration file every CoWork test that fires reads. See ../README.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cowork_evals.config import CONFIG_FILENAME, CONSENT_NONE

HERE = Path(__file__).parent
REPOSITORY = HERE.parent.parent


def pytest_collection_modifyitems(items) -> None:
    for item in items:
        if HERE in Path(str(item.path)).parents:
            item.add_marker("integration")


@pytest.fixture
def unattended(tmp_path: Path) -> Path:
    """This machine's configuration with `cowork.consent` set to `none`, in a new file.

    `consent: none` is what an unattended run sets, and it is why no modal appears in a
    test run. It is a configuration value and not a seam: this writes a file exactly as a
    consumer would, and no parameter injects an answer.

    Every other key is copied from this machine's own `cowork_evals.yaml`, so a developer
    who raised a timeout there still gets it here. Nothing prints the file or the profile
    it names. Public repository rule, in ../../README.md.
    """
    source = REPOSITORY / CONFIG_FILENAME
    assert source.is_file(), f"{CONFIG_FILENAME} is not in the repository root"
    document = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    assert document.get("cowork", {}).get("profile"), f"{CONFIG_FILENAME} names no profile"
    document["cowork"]["consent"] = CONSENT_NONE

    path = tmp_path / CONFIG_FILENAME
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path
