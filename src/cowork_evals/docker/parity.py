"""Compare a probe document against the image inventory. Runs on the host.

The delta table in [docs/docker.md](../../../docs/docker.md) is applied exactly, and four
things fail: a pin that is missing or at another version, one of the five tools recorded as
absent turning up present, `import uno`, because unoserver and headless conversion are the
capability the container exists to prove, and a tool probe.py probes that no table here
records, whose result would otherwise be read by nothing.

No page under `docs/` is parsed. The pins come from the shipped `requirements.txt`, and
the expected non-Python versions are the table below, which cites docs/runtime.md.

    python3 -m cowork_evals.docker.parity probe.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from packaging.utils import canonicalize_name

from . import probe

REQUIREMENTS = Path(__file__).parent.parent / "data" / "requirements.txt"

# Every tool probe.py probes is in exactly one of the three tables below, and compare()
# fails when one is in none of them. Which table a new tool goes in is decided by what is
# recorded for it: a version, presence alone, or absence.

# The five docs/runtime.md records as not present. A skill can call one here and not in a
# session, so finding one is a failure.
ABSENT = ("wkhtmltopdf", "weasyprint", "exiftool", "docker", "sqlite3")

# Recorded present with no version to compare. docs/runtime.md lists `ssh` without one, and
# `bwrap` and `socat` are the two harness deltas docs/docker.md records: neither is a
# fidelity claim about the CoWork image, and neither fails.
PRESENT = ("ssh", "bwrap", "socat")

# What docs/runtime.md records for each tool, for the report. A difference is printed and
# does not fail: a jammy point release moves a patch version and must not block.
EXPECTED_VERSIONS = {
    "python3": "3.10.12",
    "pip": "25.3",
    "uv": "0.12.3",
    "node": "22.23.2",
    "npm": "10.9.8",
    "java": "11.0.31",
    "git": "2.34.1",
    "soffice": "26.2.5.2",
    "unoserver": "3.7",
    "pandoc": "2.9.2.1",
    "pdftoppm": "22.02.0",
    "gs": "9.55.0",
    "qpdf": "10.6.3",
    "tesseract": "4.1.1",
    "convert": "6.9.11-60",
    "ffmpeg": "4.4.2",
    "curl": "7.81.0",
    "wget": "1.21.2",
    "jq": "1.6",
}

# docs/runtime.md, the fonts section. Printed, never failed.
EXPECTED_FONT_FAMILIES = 118
EXPECTED_OS_ID = "ubuntu"
EXPECTED_OS_VERSION_ID = "22.04"
EXPECTED_ARCHITECTURE = "aarch64"


def pins(text: str) -> dict[str, str]:
    """A requirements file or a `pip freeze`, as canonical name to version."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if "==" in line and not line.startswith("#"):
            name, _, version = line.partition("==")
            out[canonicalize_name(name)] = version.strip()
    return out


def compare(document: dict, expected: dict[str, str]) -> tuple[list[str], list[str]]:
    """The failures and the notes, in the order docs/docker.md's delta table lists them."""
    failures: list[str] = []
    notes: list[str] = []

    found = pins("\n".join(document.get("pip_freeze", [])))
    for name, version in sorted(expected.items()):
        if name not in found:
            failures.append(f"pin missing: {name}=={version}")
        elif found[name] != version:
            failures.append(f"pin moved: {name}=={found[name]}, expected {version}")
    for name in sorted(set(found) - set(expected)):
        notes.append(f"extra package: {name}=={found[name]}")

    tools = document.get("tools", {})
    unlisted = sorted(
        set(probe.VERSION_COMMANDS) - set(EXPECTED_VERSIONS) - set(ABSENT) - set(PRESENT)
    )
    if unlisted:
        failures.append(f"tool probed and never compared: {', '.join(unlisted)}")
    for name in ABSENT:
        if tools.get(name, {}).get("present"):
            failures.append(f"tool recorded as absent is present: {name}")

    uno = document.get("uno", {})
    if not uno.get("imports"):
        failures.append(f"import uno failed: {uno.get('error') or 'no detail reported'}")

    for name, version in sorted(EXPECTED_VERSIONS.items()):
        reported = tools.get(name, {})
        if not reported.get("present"):
            notes.append(f"tool absent: {name}, expected {version}")
        # The probe parses a dotted version out of the tool's own line. A build suffix
        # such as ImageMagick's `-60` is in that line and not in the parsed version, so
        # the line is the second place to look before calling it a difference.
        elif reported.get("version") != version and version not in (reported.get("output") or ""):
            notes.append(
                f"tool version differs: {name} {reported.get('version')}, expected {version}"
            )

    for name in PRESENT:
        if not tools.get(name, {}).get("present"):
            notes.append(f"tool absent: {name}, no version recorded")

    families = document.get("font_families")
    if families != EXPECTED_FONT_FAMILIES:
        notes.append(f"font families: {families}, expected {EXPECTED_FONT_FAMILIES}")

    release = document.get("os_release", {})
    if release.get("ID") != EXPECTED_OS_ID or release.get("VERSION_ID") != EXPECTED_OS_VERSION_ID:
        notes.append(
            f"OS: {release.get('ID')} {release.get('VERSION_ID')}, "
            f"expected {EXPECTED_OS_ID} {EXPECTED_OS_VERSION_ID}"
        )
    if document.get("architecture") != EXPECTED_ARCHITECTURE:
        notes.append(
            f"architecture: {document.get('architecture')}, expected {EXPECTED_ARCHITECTURE}"
        )

    return failures, notes


def report(document: dict, failures: list[str], notes: list[str]) -> None:
    """The platform the probe actually ran on comes first.

    An x86 run is never read as an aarch64 one.
    """
    release = document.get("os_release", {})
    print(
        f"probed: {release.get('PRETTY_NAME', 'unknown OS')} "
        f"{document.get('architecture', 'unknown architecture')}, "
        f"{len(document.get('pip_freeze', []))} packages, "
        f"{document.get('font_families')} font families"
    )
    for note in notes:
        print(f"note: {note}")
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"{len(failures)} failures, {len(notes)} notes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("probe", type=Path, help="the JSON document docker/probe.py wrote")
    arguments = parser.parse_args(argv)

    document = json.loads(arguments.probe.read_text())
    expected = pins(REQUIREMENTS.read_text())
    failures, notes = compare(document, expected)
    report(document, failures, notes)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
