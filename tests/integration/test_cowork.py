"""The driver against the real thing: a real CoWork profile, and one real run.

Deselected by default. Run with `scripts/test.sh -m integration`. Nothing here is skipped:
an unconfigured profile, a missing profile directory and an empty profile are failures. See
../README.md.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from cowork_evals import Config, CoWork, CoWorkError, CoWorkSection

TAXONOMY = {2, 3, 4, 5, 6, 7, 8}


def real_profile() -> CoWorkSection:
    """The configured profile. Fails when this machine has none, and never skips."""
    section = Config.load().cowork
    assert section.profile is not None, "cowork_evals.yaml names no profile"
    readable = section.profile_dir.is_dir()
    assert readable, "the configured profile directory does not exist"
    return section


@pytest.mark.integration
def test_the_reader_handles_every_session_in_a_real_profile(
    session_document_keys: set[str],
) -> None:
    """Nothing here prints a path, a prompt or an identifier. Public repository rule."""
    driver = CoWork(real_profile())
    found = driver.sessions()
    assert found, "the configured profile holds no sessions"

    for session in found:
        try:
            document = driver.collect(session)
        except CoWorkError as error:
            assert error.code in TAXONOMY
            continue
        assert set(document) == session_document_keys
        json.dumps(document)
        assert isinstance(document["final_text"], str)
        assert document["final_text"]
        for call in document["tool_calls"]:
            assert isinstance(call["name"], str)
        assert document["tool_names"] == [call["name"] for call in document["tool_calls"]]


# The only test that proves the application end of the contract: that the deep link
# prefills, that the synthetic Return submits, and that `completed` is written. It fires a
# real run, so it costs a VM boot, counts against the rate ceiling and leaves one permanent
# session in the signed-in account. It needs the macOS Accessibility grant, a signed-in
# CoWork and the desktop application already running. `live` selects it alone, so an
# integration run that must not spend is `-m "integration and not live"`.


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.timeout(1800)
def test_a_live_run_returns_the_marker(session_document_keys: set[str]) -> None:
    driver = CoWork(real_profile())
    marker = f"MARKER-{uuid.uuid4().hex[:12].upper()}"
    before = len(driver.sessions())
    before_log = len(driver.history())

    document = driver.run(f"Reply with exactly: {marker}")

    assert marker in document["final_text"]
    assert document["lifecycle"][-1] == "completed"
    assert set(document) == session_document_keys
    json.dumps(document)

    assert len(driver.sessions()) == before + 1
    assert Path(document["session_dir"]) in driver.sessions()

    entries = driver.history()
    assert len(entries) == before_log + 1
    assert entries[-1]["outcome"] == "submitted"
    assert entries[-1]["session_dir"] == document["session_dir"]

    written = Path(document["log_file"]).read_text(encoding="utf-8")
    assert "firing the deep link:" in written
    assert "discovered the session:" in written
    assert "the completion signal fired: lifecycle state completed" in written
