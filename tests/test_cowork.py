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


# The run log, the rate ceiling and the diagnostic log.


def build(tmp_path: Path, **overrides: object) -> CoWork:
    """A driver over a temporary profile, run log and log directory."""
    profile = tmp_path / "profile"
    (profile / "local-agent-mode-sessions").mkdir(parents=True, exist_ok=True)
    values: dict[str, object] = {
        "profile": str(profile),
        "run_log": str(tmp_path / "runs.jsonl"),
        "log_dir": str(tmp_path / "logs"),
    }
    values.update(overrides)
    return CoWork(Config(**values))  # type: ignore[arg-type]


def test_an_unset_profile_is_refused_before_anything_fires(tmp_path: Path) -> None:
    driver = CoWork(Config(run_log=tmp_path / "runs.jsonl"))
    with pytest.raises(CoWorkError) as raised:
        driver._check("Reply with exactly: PONG")
    assert raised.value.code == 2
    assert driver.history() == []


def test_an_unreadable_profile_is_refused(tmp_path: Path) -> None:
    driver = CoWork(Config(profile=str(tmp_path / "absent"), run_log=tmp_path / "runs.jsonl"))
    with pytest.raises(CoWorkError) as raised:
        driver._check("Reply with exactly: PONG")
    assert raised.value.code == 2


def test_a_prompt_above_the_cap_is_refused(tmp_path: Path) -> None:
    driver = build(tmp_path)
    with pytest.raises(CoWorkError) as raised:
        driver._check("x" * 14337)
    assert raised.value.code == 2
    assert "14336" in str(raised.value)


def test_a_prompt_at_the_cap_is_allowed(tmp_path: Path) -> None:
    build(tmp_path)._check("x" * 14336)


def test_a_linted_prompt_is_refused(tmp_path: Path) -> None:
    driver = build(tmp_path)
    with pytest.raises(CoWorkError) as raised:
        driver._check("Send an email to the team")
    assert raised.value.code == 2
    assert "rule send" in str(raised.value)


def test_the_rate_ceiling_is_refused(tmp_path: Path) -> None:
    driver = build(tmp_path, max_runs=3)
    for _ in range(3):
        driver._record("Reply with exactly: PONG", None, "submitted")
    with pytest.raises(CoWorkError) as raised:
        driver._check("Reply with exactly: PONG")
    assert raised.value.code == 2
    assert "rate ceiling" in str(raised.value)


def test_the_ceiling_counts_only_the_trailing_24_hours(tmp_path: Path) -> None:
    driver = build(tmp_path, max_runs=2)
    old = {"timestamp": "2020-01-01T00:00:00+00:00", "outcome": "submitted"}
    driver.config.run_log.write_text(json.dumps(old) + "\n", encoding="utf-8")
    driver._record("Reply with exactly: PONG", None, "submitted")
    driver._check("Reply with exactly: PONG")


def test_a_failed_submission_leaves_a_line_history_reads_back(tmp_path: Path) -> None:
    driver = build(tmp_path)
    driver._record("first", None, "failed:4")
    driver._record("second", tmp_path / "session", "submitted")
    entries = driver.history()
    assert [entry["outcome"] for entry in entries] == ["failed:4", "submitted"]
    assert entries[0]["session_dir"] is None
    assert entries[1]["session_dir"] == str(tmp_path / "session")
    assert set(entries[0]) == {"timestamp", "prompt_sha256", "session_dir", "outcome"}


def test_history_reads_a_named_run_log(tmp_path: Path) -> None:
    other = tmp_path / "other.jsonl"
    other.write_text('{"outcome":"submitted"}\n{"outcome":"fail\n', encoding="utf-8")
    assert build(tmp_path).history(other) == [{"outcome": "submitted"}]


def test_history_of_an_absent_run_log_is_empty(tmp_path: Path) -> None:
    assert build(tmp_path).history() == []


def test_two_calls_leave_two_log_files_and_no_duplicated_handler(tmp_path: Path) -> None:
    from cowork_evals.cowork import LOGGER

    driver = build(tmp_path)
    before = len(LOGGER.handlers)
    paths = []
    for _ in range(2):
        with driver._diagnostics() as path:
            assert len(LOGGER.handlers) == before + 1
            paths.append(path)
    assert len(LOGGER.handlers) == before
    assert paths[0] != paths[1]
    assert all(path is not None and path.is_file() for path in paths)
    assert sorted(p.name for p in (tmp_path / "logs").iterdir()) == sorted(p.name for p in paths)


def test_the_handler_is_closed_when_the_call_raises(tmp_path: Path) -> None:
    from cowork_evals.cowork import LOGGER

    driver = build(tmp_path)
    before = len(LOGGER.handlers)
    with pytest.raises(RuntimeError), driver._diagnostics():
        raise RuntimeError("the call failed")
    assert len(LOGGER.handlers) == before


def test_log_dir_null_writes_no_file(tmp_path: Path) -> None:
    from cowork_evals.cowork import LOGGER

    driver = build(tmp_path, log_dir=None)
    before = len(LOGGER.handlers)
    with driver._diagnostics() as path:
        assert path is None
        assert len(LOGGER.handlers) == before
    assert not (tmp_path / "logs").exists()


def test_the_document_names_the_diagnostic_log(tmp_path: Path) -> None:
    driver = build(tmp_path)
    with driver._diagnostics() as path:
        document = driver.collect(PROFILE / "one_turn")
    assert document["log_file"] == str(path)
    assert driver.collect(PROFILE / "one_turn")["log_file"] is None


# Submitting. Every firing test drives a recording fake through the runner seam.


class Runner:
    """Records every argument list, and plants session directories when asked to.

    The plant stands in for the application: the deep link and the Return produce
    session directories on the filesystem, and nothing else about them is simulated.
    """

    def __init__(
        self, plant: list[dict[str, object]] | None = None, codes: list[int] | None = None
    ):
        self.calls: list[list[str]] = []
        self.plant = plant or []
        self.codes = codes or []

    def __call__(self, argv: list[str]) -> int:
        self.calls.append(argv)
        code = self.codes.pop(0) if self.codes else 0
        if argv[0] == "osascript" and code == 0:
            for session in self.plant:
                write_session(**session)  # type: ignore[arg-type]
        return code


def write_session(
    root: Path,
    name: str,
    prompt: str | None = "Reply with exactly: PONG",
    states: tuple[str, ...] = ("queued", "started", "completed"),
    final: str | None = "PONG",
) -> Path:
    """One hand-written session directory, three levels below a root."""
    session = root / "acct" / "prof" / name
    session.mkdir(parents=True, exist_ok=True)
    lines = []
    if prompt is not None:
        lines.append(
            {
                "type": "user",
                "session_id": name,
                "timestamp": "2026-09-08T16:00:00.000Z",
                "message": {"role": "user", "content": prompt},
            }
        )
    lines += [{"type": "command_lifecycle", "command_uuid": name, "state": s} for s in states]
    (session / "audit.jsonl").write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8"
    )
    if final is not None:
        transcripts = session / ".claude" / "projects" / "session"
        transcripts.mkdir(parents=True, exist_ok=True)
        (transcripts / f"{name}.jsonl").write_text(
            json.dumps(
                {
                    "type": "assistant",
                    "timestamp": "2026-09-08T16:00:30.000Z",
                    "message": {"role": "assistant", "content": [{"type": "text", "text": final}]},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    return session


def firing(tmp_path: Path, runner: Runner, **overrides: object) -> CoWork:
    driver = build(tmp_path, settle_seconds=0, session_timeout=0, idle_seconds=0, **overrides)
    return CoWork(driver.config, runner=runner)


def test_deep_link_percent_encodes_the_prompt() -> None:
    driver = CoWork(Config())
    assert driver.deep_link("two words\nand a line") == (
        "claude://claude.ai/new?q=two%20words%0Aand%20a%20line&surface=cowork"
    )


def test_deep_link_omits_an_empty_surface() -> None:
    assert CoWork(Config(surface="")).deep_link("PING") == "claude://claude.ai/new?q=PING"


def test_the_runner_records_the_open_and_osascript_argument_lists(tmp_path: Path) -> None:
    runner = Runner(
        plant=[{"root": tmp_path / "profile" / "local-agent-mode-sessions", "name": "s1"}]
    )
    driver = firing(tmp_path, runner)
    session = driver.submit("Reply with exactly: PONG")
    assert runner.calls[0] == [
        "open",
        "claude://claude.ai/new?q=Reply%20with%20exactly%3A%20PONG&surface=cowork",
    ]
    assert runner.calls[1][0] == "osascript"
    assert "key code 36" in runner.calls[1][-1]
    assert session.name == "s1"


def test_a_non_zero_return_from_open_raises_code_3(tmp_path: Path) -> None:
    runner = Runner(codes=[1])
    with pytest.raises(CoWorkError) as raised:
        firing(tmp_path, runner).submit("Reply with exactly: PONG")
    assert raised.value.code == 3
    assert runner.calls == [runner.calls[0]]


def test_no_session_directory_raises_code_4(tmp_path: Path) -> None:
    with pytest.raises(CoWorkError) as raised:
        firing(tmp_path, Runner()).submit("Reply with exactly: PONG")
    assert raised.value.code == 4


def test_two_new_session_directories_raise_code_5(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    runner = Runner(plant=[{"root": root, "name": "s1"}, {"root": root, "name": "s2"}])
    with pytest.raises(CoWorkError) as raised:
        firing(tmp_path, runner).submit("Reply with exactly: PONG")
    assert raised.value.code == 5


def test_a_session_already_in_the_baseline_is_not_discovered(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    write_session(root, "before")
    runner = Runner(plant=[{"root": root, "name": "after"}])
    assert firing(tmp_path, runner).submit("Reply with exactly: PONG").name == "after"


def test_a_mismatched_audit_prompt_raises_code_6(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    runner = Runner(plant=[{"root": root, "name": "s1", "prompt": "someone else's prompt"}])
    with pytest.raises(CoWorkError) as raised:
        firing(tmp_path, runner).submit("Reply with exactly: PONG")
    assert raised.value.code == 6
    assert raised.value.session_dir == root / "acct" / "prof" / "s1"


def test_a_session_with_no_user_record_raises_code_6(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    runner = Runner(plant=[{"root": root, "name": "s1", "prompt": None}])
    with pytest.raises(CoWorkError) as raised:
        firing(tmp_path, runner).submit("Reply with exactly: PONG")
    assert raised.value.code == 6


def test_a_failed_submission_is_logged_and_counts_against_the_ceiling(tmp_path: Path) -> None:
    driver = firing(tmp_path, Runner())
    with pytest.raises(CoWorkError):
        driver.submit("Reply with exactly: PONG")
    assert [entry["outcome"] for entry in driver.history()] == ["failed:4"]


def test_a_refusal_before_firing_leaves_no_run_log_line(tmp_path: Path) -> None:
    runner = Runner()
    driver = firing(tmp_path, runner)
    with pytest.raises(CoWorkError) as raised:
        driver.submit("Send an email to the team")
    assert raised.value.code == 2
    assert runner.calls == []
    assert driver.history() == []


def test_wait_returns_on_the_terminal_lifecycle_state(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    session = write_session(root, "s1")
    driver = firing(tmp_path, Runner(), run_timeout=0)
    assert driver.wait(session) == session


def test_quiescence_does_not_fire_before_the_run_has_started(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    session = write_session(root, "s1", states=("queued",), final=None)
    driver = firing(tmp_path, Runner(), run_timeout=0)
    with pytest.raises(CoWorkError) as raised:
        driver.wait(session)
    assert raised.value.code == 7
    assert raised.value.session_dir == session


def test_quiescence_fires_once_the_run_has_started(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    session = write_session(root, "s1", states=("queued", "started"), final="PONG")
    driver = firing(tmp_path, Runner(), run_timeout=5)
    assert driver.wait(session) == session


def test_run_submits_waits_and_collects(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    runner = Runner(plant=[{"root": root, "name": "s1"}])
    driver = firing(tmp_path, runner, run_timeout=5)
    document = driver.run("Reply with exactly: PONG")
    assert document["final_text"] == "PONG"
    assert document["prompt"] == "Reply with exactly: PONG"
    assert document["lifecycle"] == ["queued", "started", "completed"]
    assert set(document) == DOCUMENT_KEYS
    assert json.dumps(document)
    assert [entry["outcome"] for entry in driver.history()] == ["submitted"]
    assert document["log_file"] is not None
    assert Path(document["log_file"]).is_file()


def test_the_diagnostic_log_names_the_link_the_session_and_the_signal(tmp_path: Path) -> None:
    root = tmp_path / "profile" / "local-agent-mode-sessions"
    runner = Runner(plant=[{"root": root, "name": "s1"}])
    driver = firing(tmp_path, runner, run_timeout=5)
    document = driver.run("Reply with exactly: PONG")
    written = Path(document["log_file"]).read_text(encoding="utf-8")
    assert "firing the deep link: claude://claude.ai/new?q=" in written
    assert "discovered the session:" in written
    assert "the completion signal fired: lifecycle state completed" in written


def test_a_failure_reaches_the_diagnostic_log_before_it_leaves(tmp_path: Path) -> None:
    driver = firing(tmp_path, Runner())
    with pytest.raises(CoWorkError):
        driver.submit("Reply with exactly: PONG")
    written = sorted((tmp_path / "logs").iterdir())[-1].read_text(encoding="utf-8")
    assert "submission failed with code 4" in written
