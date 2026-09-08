"""Report what the container actually holds, as one JSON document on stdout.

It runs inside the container, on that image's Python 3.10, so it is 3.10 syntax, imports
the standard library only, and imports nothing from this package. The comparison against
docs/runtime.md runs on the host and is parity.py.

    python3 probe.py > probe.json
"""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys

# Each tool, and the command that reports its version. Every name is a row of
# docs/runtime.md. The five recorded as absent are here too: the probe reports what it
# finds, and parity.py decides what a finding means.
VERSION_COMMANDS = {
    "python3": ["python3", "-V"],
    "pip": ["python3", "-m", "pip", "--version"],
    "uv": ["uv", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "java": ["java", "-version"],
    "git": ["git", "--version"],
    "soffice": ["soffice", "--version"],
    "unoserver": ["unoserver", "--version"],
    "pandoc": ["pandoc", "--version"],
    "pdftoppm": ["pdftoppm", "-v"],
    "gs": ["gs", "--version"],
    "qpdf": ["qpdf", "--version"],
    "tesseract": ["tesseract", "--version"],
    "convert": ["convert", "--version"],
    "ffmpeg": ["ffmpeg", "-version"],
    "curl": ["curl", "--version"],
    "wget": ["wget", "--version"],
    "jq": ["jq", "--version"],
    "ssh": ["ssh", "-V"],
    "bwrap": ["bwrap", "--version"],
    "wkhtmltopdf": ["wkhtmltopdf", "--version"],
    "weasyprint": ["weasyprint", "--version"],
    "exiftool": ["exiftool", "-ver"],
    "docker": ["docker", "--version"],
    "sqlite3": ["sqlite3", "--version"],
}

VERSION_PATTERN = re.compile(r"\d+(?:\.\d+)+")


def run(argv):
    """The command's combined output, or None when the command is not on PATH."""
    if shutil.which(argv[0]) is None:
        return None
    try:
        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.decode("utf-8", "replace").strip()


def tool(argv):
    """One tool: whether it is present, its first output line, and a version out of it."""
    output = run(argv)
    if output is None:
        return {"present": False, "output": None, "version": None}
    first = output.splitlines()[0] if output else ""
    found = VERSION_PATTERN.search(first) or VERSION_PATTERN.search(output)
    return {"present": True, "output": first, "version": found.group(0) if found else None}


def os_release():
    values = {}
    try:
        with open("/etc/os-release") as handle:
            for line in handle:
                if "=" in line:
                    name, _, value = line.partition("=")
                    values[name.strip()] = value.strip().strip('"')
    except OSError:
        pass
    return values


def font_families():
    """`fc-list : family | sort -u`, counted. The number docs/runtime.md records."""
    output = run(["fc-list", ":", "family"])
    if output is None:
        return None
    return len({line.strip() for line in output.splitlines() if line.strip()})


def uno_import():
    """`import uno` in a child, so a broken binding cannot take the probe down with it."""
    completed = subprocess.run(
        [sys.executable, "-c", "import uno"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "imports": completed.returncode == 0,
        "error": (
            None
            if completed.returncode == 0
            else completed.stdout.decode("utf-8", "replace").strip()
        ),
    }


def pip_freeze():
    output = run(["python3", "-m", "pip", "freeze"])
    if output is None:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def main():
    document = {
        "schema": 1,
        "os_release": os_release(),
        "architecture": platform.machine(),
        "platform": {"system": platform.system(), "release": platform.release()},
        "tools": {name: tool(argv) for name, argv in VERSION_COMMANDS.items()},
        "uno": uno_import(),
        "font_families": font_families(),
        "pip_freeze": pip_freeze(),
    }
    json.dump(document, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
