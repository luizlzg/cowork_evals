"""The two environments are what docs/environments.md says they are.

These tests read the environments on disk. An unbuilt environment fails them. Build both
with scripts/init.sh before running the suite.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
VENV = ROOT / ".venv"
COWORK = ROOT / ".venv_cowork"
REQUIREMENTS = ROOT / "docs" / "data" / "requirements.txt"
INSTALLABLE = ROOT / "docs" / "data" / "requirements_installable.txt"

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


def normalize(name: str) -> str:
    """PEP 503 name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if "==" in line:
            name, _, version = line.partition("==")
            out[normalize(name)] = version
    return out


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


def test_installable_is_the_freeze_minus_the_nine():
    full = pins(REQUIREMENTS)
    installable = pins(INSTALLABLE)
    assert set(full) - set(installable) == NOT_INSTALLABLE
    # Every shared pin is at the same version. A drift here silently changes the mirror.
    assert {k: full[k] for k in installable} == installable


def test_repo_venv_is_python_314():
    assert (VENV / "bin" / "python").exists(), ".venv not built. Run scripts/venv.sh"
    assert interpreter(VENV) == "3.14"


def test_cowork_mirror_is_python_310():
    built = (COWORK / "bin" / "python").exists()
    assert built, ".venv_cowork not built. Run scripts/cowork_venv.sh"
    assert interpreter(COWORK) == "3.10"


def test_tests_run_under_the_repo_venv_not_the_mirror():
    """A 3.10 interpreter here means the suite was launched through cowork_run.sh."""
    assert sys.version_info[:2] >= (3, 14)


def test_every_script_is_executable_and_parses():
    scripts = sorted(p for p in (ROOT / "scripts").glob("*.sh"))
    assert scripts, "no scripts found"
    for script in scripts:
        # lib.sh is sourced, never executed, so it needs no executable bit.
        if script.name != "lib.sh":
            assert script.stat().st_mode & 0o111, f"{script.name} is not executable"
        subprocess.run(["bash", "-n", str(script)], check=True)
