"""Every test under tests/integration/ is integration, whether or not it says so.

The marker is applied here so it cannot be forgotten on a new file. Selection stays
`-m integration`, which is what pyproject.toml deselects by default.

pytest_collection_modifyitems in a subdirectory conftest still receives every collected
item, so the hook filters by path.

It also asks for the keyboard once per run that takes it, and holds the one configuration file every
CoWork test that fires reads. See ../README.md.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
import yaml

from cowork_evals import cowork as driver_module
from cowork_evals.config import CONFIG_FILENAME, CONSENT_DIALOG, Config, CoWorkSection

HERE = Path(__file__).parent
REPOSITORY = HERE.parent.parent


def pytest_collection_modifyitems(items) -> None:
    for item in items:
        if HERE in Path(str(item.path)).parents:
            item.add_marker("integration")


@pytest.fixture(scope="session")
def keyboard() -> None:
    """Ask for the keyboard once, before the first test that takes it.

    A test takes the keyboard in one of two ways, and each goes through a fixture that
    requests this one: `attended`, which every test that submits through the driver reads,
    and `activate` in test_cowork.py, which drives another application through `osascript`.
    A run that selects neither, a Docker-only one for example, shows no dialog.

    Session-scoped, so one run asks once: `cowork.consent` sets a module flag, and the
    driver's ask is a no-op after this one.

    `consent` is forced to `dialog` rather than copied from this machine's file, so a
    developer whose own file carries `none` is still warned by a test run. It reads
    `consent` and `consent_timeout` and nothing else, so a machine with no profile
    configured still gets the dialog, which is right: activating Finder needs no profile.

    Cancel raises code 2 here, so every integration test errors. The developer said no to
    the keyboard, so the tier cannot run.
    """
    source = REPOSITORY / CONFIG_FILENAME
    section = Config.load(source).cowork if source.is_file() else CoWorkSection()
    driver_module.consent(dataclasses.replace(section, consent=CONSENT_DIALOG))


@pytest.fixture
def attended(keyboard: None, tmp_path: Path) -> Path:
    """This machine's configuration with `cowork.consent` set to `dialog`, in a new file.

    `dialog` is forced rather than copied, so a developer whose own file carries `none` is
    still warned. The `keyboard` fixture above has already asked by the time a test runs, so
    the driver's ask inside the submission shows nothing and the value proves the driver
    asks rather than refuses.

    It is a configuration value and not a seam: this writes a file exactly as a consumer
    would, and no parameter injects an answer.

    Every other key is copied from this machine's own `cowork_evals.yaml`, so a developer
    who raised a timeout there still gets it here. Nothing prints the file or the profile
    it names. Public repository rule, in ../../README.md.
    """
    source = REPOSITORY / CONFIG_FILENAME
    assert source.is_file(), f"{CONFIG_FILENAME} is not in the repository root"
    document = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    assert document.get("cowork", {}).get("profile"), f"{CONFIG_FILENAME} names no profile"
    document["cowork"]["consent"] = CONSENT_DIALOG

    path = tmp_path / CONFIG_FILENAME
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path
