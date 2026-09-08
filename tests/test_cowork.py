"""The driver reads a session as docs/cowork_driver.md says it does.

Every assertion is over a hand-written fixture under tests/data/cowork/. No test starts a
CoWork session.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cowork_evals import Config, CoWork, CoWorkError

ROOT = Path(__file__).resolve().parent / "data" / "cowork" / "sessions"
PROFILE = ROOT / "acct0000" / "prof0000"

# Every key the result document carries, and no other. docs/cowork_driver.md.
DOCUMENT_KEYS = {
    "prompt",
    "prompt_sha256",
    "session_dir",
    "submitted_at",
    "collected_at",
    "transcript",
    "other_transcripts",
    "subagent_transcripts",
    "audit_prompt",
    "lifecycle",
    "turns",
    "tool_calls",
    "tool_names",
    "final_text",
    "outputs",
    "log_file",
}


@pytest.fixture
def driver() -> CoWork:
    """A driver with no profile, which is what an archived session is read with."""
    return CoWork(Config())


@pytest.fixture(autouse=True)
def transcript_ages() -> None:
    """Order the two tool_call transcripts by modification time.

    git does not carry modification times, so the fixture's ordering is set here rather
    than left to checkout order.
    """
    session = PROFILE / "tool_call" / ".claude" / "projects" / "session"
    os.utime(session / "t-0002-old.jsonl", (1_800_000_000, 1_800_000_000))
    os.utime(session / "t-0002-new.jsonl", (1_800_000_100, 1_800_000_100))


def test_sessions_finds_every_session_and_nothing_else(driver: CoWork) -> None:
    found = driver.sessions(ROOT)
    assert [path.name for path in found] == [
        "no_output",
        "no_transcript",
        "one_turn",
        "partial_line",
        "subagent",
        "tool_call",
    ]
    assert all(path.parent.parent.parent == ROOT for path in found)


def test_sessions_on_an_absent_root_is_empty(driver: CoWork, tmp_path: Path) -> None:
    assert driver.sessions(tmp_path / "absent") == []


def test_sessions_defaults_to_the_configured_root(tmp_path: Path) -> None:
    """A driver with no profile refuses at the call that needs one, not at construction."""
    driver = CoWork(Config())
    with pytest.raises(CoWorkError) as raised:
        driver.sessions()
    assert raised.value.code == 2


def test_the_document_carries_exactly_the_documented_keys(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "one_turn")
    assert set(document) == DOCUMENT_KEYS
    assert "exit_code" not in document


def test_the_document_is_json_serializable_with_no_profile(driver: CoWork) -> None:
    assert driver.config.profile is None
    text = json.dumps(driver.collect(PROFILE / "one_turn"))
    assert json.loads(text)["final_text"] == "PONG"


def test_a_one_turn_session(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "one_turn")
    assert document["prompt"] == "Reply with exactly: PONG"
    assert document["audit_prompt"] == "Reply with exactly: PONG"
    assert document["prompt_sha256"] == (
        "0fb5aed1b51b28b04409b7963b2453fe1597d198c3b8396fc8ebd072104511de"
    )
    assert document["submitted_at"] == "2026-09-08T10:00:00.000Z"
    assert document["lifecycle"] == ["queued", "started", "completed"]
    assert document["turns"] == [
        {"role": "user", "text": "Reply with exactly: PONG"},
        {"role": "assistant", "text": "PONG"},
    ]
    assert document["final_text"] == "PONG"
    assert document["tool_calls"] == []
    assert document["tool_names"] == []
    assert document["outputs"] == ["outputs/marker.txt"]
    assert document["other_transcripts"] == []
    assert document["subagent_transcripts"] == []
    assert document["log_file"] is None


def test_a_thinking_block_is_not_turn_text(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "one_turn")
    assert "the marker is PONG" not in json.dumps(document["turns"])


def test_the_main_transcript_is_the_newest_top_level_file(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "tool_call")
    assert Path(document["transcript"]).name == "t-0002-new.jsonl"
    assert [Path(p).name for p in document["other_transcripts"]] == ["t-0002-old.jsonl"]
    assert "an earlier run" not in json.dumps(document["turns"])


def test_a_tool_result_pairs_by_id_and_not_by_position(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "tool_call")
    calls = {call["id"]: call for call in document["tool_calls"]}
    assert set(calls) == {"call-a", "call-b"}
    assert calls["call-a"]["input"] == {"command": "cat /etc/os-release"}
    assert calls["call-a"]["result"] == 'NAME="Ubuntu"'
    assert calls["call-b"]["input"] == {"command": "uname -r"}
    assert calls["call-b"]["result"] == "6.8.0-136-generic"
    assert document["tool_names"] == ["mcp__workspace__bash", "mcp__workspace__bash"]


def test_a_tool_call_carries_its_mcp_attribution(driver: CoWork) -> None:
    call = driver.collect(PROFILE / "tool_call")["tool_calls"][0]
    assert call["mcp_server"] == "workspace"
    assert call["mcp_tool"] == "bash"
    assert call["timestamp"] == "2026-09-08T11:00:05.000Z"


def test_an_orphan_tool_result_is_dropped(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "tool_call")
    assert "belongs to a subagent" not in json.dumps(document["tool_calls"])


def test_string_content_is_read_as_turn_text(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "tool_call")
    assert document["final_text"] == "The guest kernel is 6.8.0-136-generic."


def test_a_subagent_transcript_is_recorded_and_never_merged(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "subagent")
    assert [Path(p).name for p in document["subagent_transcripts"]] == ["agent-0001.jsonl"]
    assert document["other_transcripts"] == []
    assert document["final_text"] == "There are three notes, all about the mirror."
    assert "Read every note" not in json.dumps(document["turns"])


def test_a_partial_last_line_is_skipped(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "partial_line")
    assert document["lifecycle"] == ["queued", "started"]
    assert document["final_text"] == "Ubuntu 22.04.5 LTS"


def test_a_session_with_no_assistant_output_raises_code_8(driver: CoWork) -> None:
    with pytest.raises(CoWorkError) as raised:
        driver.collect(PROFILE / "no_output")
    assert raised.value.code == 8
    assert raised.value.session_dir == PROFILE / "no_output"


def test_a_session_with_no_transcript_directory_raises_code_8(driver: CoWork) -> None:
    with pytest.raises(CoWorkError) as raised:
        driver.collect(PROFILE / "no_transcript")
    assert raised.value.code == 8


def test_a_known_prompt_beats_the_audit_record(driver: CoWork) -> None:
    document = driver.collect(PROFILE / "one_turn", prompt="what the caller submitted")
    assert document["prompt"] == "what the caller submitted"
    assert document["audit_prompt"] == "Reply with exactly: PONG"


def test_the_configuration_is_frozen_and_overridable_at_construction() -> None:
    driver = CoWork(Config(profile="Fixture"), max_runs=3)
    assert driver.config.max_runs == 3
    assert driver.config.profile == "Fixture"


def test_an_unknown_constructor_override_raises() -> None:
    with pytest.raises(CoWorkError) as raised:
        CoWork(Config(), nonsense=1)
    assert raised.value.code == 2
