"""The two environments are what docs/environments.md says they are.

These tests read the environments on disk. An unbuilt environment fails them. Build both
with scripts/init.sh before running the suite.
"""

from __future__ import annotations

import subprocess
import sys
from importlib.resources import files
from pathlib import Path

from cowork_evals.requirements import pins as read_pins

ROOT = Path(__file__).resolve().parent.parent.parent
VENV = ROOT / ".venv"
COWORK = ROOT / ".venv_cowork"
DATA = ROOT / "src" / "cowork_evals" / "data"
REQUIREMENTS = DATA / "requirements.txt"
INSTALLABLE = DATA / "requirements_installable.txt"
TEST_ONLY = DATA / "requirements_test.txt"

# The nine pins that cannot install off the CoWork VM. docs/environments.md.
NOT_INSTALLABLE = {
    "command-not-found",
    "dbus-python",
    "distro-info",
    "pipx",
    "pygobject",
    "pyinotify",
    "python-apt",
    "ufw",
    "unattended-upgrades",
}


def pins(path: Path) -> dict[str, str]:
    """The package's own reader, over a path. scripts/cowork_venv.sh calls the same one."""
    return read_pins(path.read_text())


def interpreter(venv: Path) -> str:
    return subprocess.run(
        [str(venv / "bin" / "python"), "-c", 'import sys; print("%d.%d" % sys.version_info[:2])'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_requirements_files_exist():
    assert REQUIREMENTS.is_file()
    assert INSTALLABLE.is_file()
    assert TEST_ONLY.is_file()


def test_requirements_files_resolve_as_package_data():
    """How a build reaches them from an installed wheel, with no checkout in sight."""
    data = files("cowork_evals") / "data"
    for name in ("requirements.txt", "requirements_installable.txt"):
        assert (data / name).read_text().count("==") > 100


def test_installable_is_the_freeze_minus_the_nine():
    full = pins(REQUIREMENTS)
    installable = pins(INSTALLABLE)
    assert set(full) - set(installable) == NOT_INSTALLABLE
    # Every shared pin is at the same version. A drift here silently changes the mirror.
    assert {k: full[k] for k in installable} == installable


def test_the_test_layer_adds_packages_and_moves_none():
    """No pin of `requirements_test.txt` is already in the image.

    The test image installs it with `--no-deps`, so a name on both lists would either be
    reinstalled at the wrong version or silently do nothing. docs/environments.md owns
    which of the three files a pin goes in.
    """
    assert set(pins(TEST_ONLY)) & set(pins(REQUIREMENTS)) == set()


def test_repo_venv_is_python_310():
    assert (VENV / "bin" / "python").exists(), ".venv not built. Run scripts/venv.sh"
    assert interpreter(VENV) == "3.10"


def test_cowork_mirror_is_python_310():
    built = (COWORK / "bin" / "python").exists()
    assert built, ".venv_cowork not built. Run scripts/cowork_venv.sh"
    assert interpreter(COWORK) == "3.10"


def test_tests_run_under_the_repo_venv_not_the_mirror():
    """Both environments are 3.10, so the prefix is what tells them apart, not the version.

    A run under the mirror would carry the CoWork wheel set and not the dev group, so the
    suite would collect against the wrong dependencies. docs/environments.md.
    """
    assert Path(sys.prefix).resolve() == VENV.resolve(), f"suite ran under {sys.prefix}"


def test_scripts_readme_carries_a_row_for_every_script():
    """The index owns the task list, so a new script cannot be reachable and unlisted."""
    index = (ROOT / "scripts" / "README.md").read_text()
    for script in sorted((ROOT / "scripts").glob("*.sh")):
        assert f"`{script.name}`" in index, f"{script.name} has no row in scripts/README.md"


def test_every_script_is_executable_and_parses():
    """Every `*.sh` in the repository, outside a dot directory.

    `scripts/lint.sh` selects by the same rule, so no shell file is checked here and
    unlinted there. The rule excludes `.venv_cowork/`, which carries a vendored one.
    """
    scripts = sorted(
        path
        for path in ROOT.rglob("*.sh")
        if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    )
    assert scripts, "no shell files found"
    for script in scripts:
        # lib.sh is sourced, never executed, so it needs no executable bit.
        if script.name != "lib.sh":
            assert script.stat().st_mode & 0o111, f"{script.name} is not executable"
        subprocess.run(["bash", "-n", str(script)], check=True)
