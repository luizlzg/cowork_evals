"""The CoWork backend over hand-written case trees. Nothing here starts a session.

The skip rule is docs/running_evals.md, one assertion per row of it. See ../README.md.
"""

from __future__ import annotations

import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

from cowork_evals.cases import CaseError, read
from cowork_evals.config import Config, CoWorkError, CoWorkSection
from cowork_evals.cowork_backend import plan, run, skips
from cowork_evals.harness import RESULT_NAME

MANIFEST = '{"name": "skips-fixture", "description": "A fixture.", "version": "0.0.1"}\n'


def build(
    tmp_path: Path,
    *,
    frontmatter: str = "",
    case_yaml: str | None = None,
    graders: dict[str, str] | None = None,
    mocks_at: tuple[str, ...] = (),
) -> tuple[Path, Path]:
    """One plugin root with one case under `evals/skill/case/`. Returns both paths."""
    root = tmp_path / "plugin"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(MANIFEST, encoding="utf-8")

    case_dir = root / "evals" / "skill" / "case"
    case_dir.mkdir(parents=True)
    block = textwrap.dedent(frontmatter).strip("\n")
    (case_dir / "prompt.md").write_text(
        f"---\nname: one-case\n{block}\n---\n\nReply with exactly: PONG\n", encoding="utf-8"
    )
    if case_yaml is not None:
        (case_dir / "case.yaml").write_text(textwrap.dedent(case_yaml).lstrip("\n"), "utf-8")
    for name, body in (graders or {}).items():
        directory = case_dir / "graders"
        directory.mkdir(exist_ok=True)
        (directory / f"{name}.md").write_text(textwrap.dedent(body).lstrip("\n"), "utf-8")
    for relative in mocks_at:
        (root / relative / "mocks" / "workspace").mkdir(parents=True)
        (root / relative / "mocks" / "workspace" / "bash.md").write_text("ok\n", "utf-8")
    return root, case_dir


def skips_of(tmp_path: Path, **kwargs: object) -> object:
    root, case_dir = build(tmp_path, **kwargs)  # type: ignore[arg-type]
    return skips(read(case_dir), root)


# The rows the backend honours.


def test_a_written_out_runs_key_is_honoured(tmp_path: Path) -> None:
    assert skips_of(tmp_path, frontmatter="runs: 3").case == ()


def test_a_written_out_timeout_seconds_is_honoured(tmp_path: Path) -> None:
    assert skips_of(tmp_path, frontmatter="timeout_seconds: 600").case == ()


def test_a_case_writing_no_optional_key_is_not_skipped(tmp_path: Path) -> None:
    result = skips_of(tmp_path)
    assert result.case == ()
    assert result.graders == {}
    assert result.skipped is False


def test_an_arm_on_a_grader_is_honoured(tmp_path: Path) -> None:
    """One arm runs, it is the with-arm, and every grader is scored in it."""
    graders = {
        "with-only": "---\ntype: regex\npattern: PONG\narm: with-only\n---\n",
        "both": "---\ntype: regex\npattern: PONG\narm: both\n---\n",
    }
    result = skips_of(tmp_path, graders=graders)
    assert result.case == ()
    assert result.graders == {}


# The rows that skip the case.


def test_a_written_out_max_turns_skips_the_case(tmp_path: Path) -> None:
    result = skips_of(tmp_path, frontmatter="max_turns: 12")
    assert result.skipped is True
    assert result.case == ("max_turns: no turn cap reaches a CoWork session",)


def test_each_execution_key_skips_the_case(tmp_path: Path) -> None:
    for key, written in (
        ("model", "model: sonnet"),
        ("allowed_tools", "allowed_tools: [Read]"),
        ("append_system_prompt", "append_system_prompt: Be brief."),
        ("env", "env:\n  EVAL_ONE: two"),
    ):
        result = skips_of(tmp_path / key, frontmatter=written)
        assert len(result.case) == 1
        assert result.case[0].startswith(f"{key}: ")


def test_a_context_key_in_case_yaml_skips_the_case(tmp_path: Path) -> None:
    result = skips_of(
        tmp_path,
        case_yaml="""
        schema_version: "1.1"
        name: one-case
        context:
          add_dirs: [resources]
        """,
    )
    assert result.case == ("context.add_dirs: nothing stages files into the VM",)


def test_a_suite_wide_mocks_directory_skips_the_case(tmp_path: Path) -> None:
    result = skips_of(tmp_path, mocks_at=("evals",))
    assert len(result.case) == 1
    assert result.case[0].startswith(str(tmp_path / "plugin" / "evals" / "mocks"))


def test_a_group_mocks_directory_skips_the_case(tmp_path: Path) -> None:
    result = skips_of(tmp_path, mocks_at=("evals/skill",))
    assert len(result.case) == 1
    assert "evals/skill/mocks" in result.case[0]


def test_a_case_mocks_directory_skips_that_case_alone(tmp_path: Path) -> None:
    result = skips_of(tmp_path, mocks_at=("evals/skill/case",))
    assert len(result.case) == 1
    assert "evals/skill/case/mocks" in result.case[0]


def test_every_mocks_layer_is_reported(tmp_path: Path) -> None:
    result = skips_of(tmp_path, mocks_at=("evals", "evals/skill", "evals/skill/case"))
    assert len(result.case) == 3


def test_a_mocks_directory_beside_the_plugin_root_is_not_a_layer(tmp_path: Path) -> None:
    """The layers run from `evals/` down. Nothing above it is one."""
    root, case_dir = build(tmp_path)
    (root / "mocks").mkdir()
    assert skips(read(case_dir), root).case == ()


# The one grader skip decided before a run.


def test_a_grader_reading_mock_calls_is_skipped_and_the_case_still_runs(tmp_path: Path) -> None:
    graders = {
        "asked-the-server": "---\ntype: regex\ntarget: mock_calls\npattern: posted\n---\n",
        "answered": "---\ntype: regex\ntarget: last_message\npattern: PONG\n---\n",
    }
    result = skips_of(tmp_path, graders=graders)
    assert result.case == ()
    assert list(result.graders) == ["asked-the-server"]
    assert "mock_calls" in result.graders["asked-the-server"]


def test_a_judged_grader_focusing_mock_calls_is_skipped(tmp_path: Path) -> None:
    graders = {"judged": "---\ntype: llm\nfocus: mock_calls\n---\n\nThe server was asked.\n"}
    result = skips_of(tmp_path, graders=graders)
    assert result.case == ()
    assert list(result.graders) == ["judged"]


# The plan. Nothing below starts a session, and none of it needs a profile.


SMOKE = Path(__file__).resolve().parent.parent.parent / "plugins" / "smoke"
TREE = Path(__file__).resolve().parent.parent / "data" / "cases" / "tree"


def settings(tmp_path: Path, **overrides: object) -> Config:
    """A configuration whose run log is a file this test owns."""
    values: dict[str, object] = {"run_log": str(tmp_path / "runs.jsonl"), "log_dir": None}
    values.update(overrides)
    return Config(cowork=CoWorkSection(**values))  # type: ignore[arg-type]


def log(path: Path, submissions: int) -> None:
    """A hand-written run log, `submissions` entries inside the trailing 24 hours."""
    stamp = datetime.now(UTC).isoformat()
    path.write_text(
        "".join(
            json.dumps({"timestamp": stamp, "outcome": "submitted"}) + "\n"
            for _ in range(submissions)
        ),
        encoding="utf-8",
    )


def test_the_smoke_fixture_is_found_and_reports_no_skip(tmp_path: Path) -> None:
    prepared = plan(SMOKE, config=settings(tmp_path))
    assert prepared.root == SMOKE.resolve()
    assert [entry.name for entry in prepared.entries] == ["python-version"]
    entry = prepared.entries[0]
    assert entry.skips.case == ()
    assert entry.skips.graders == {}
    assert entry.runs == 1, "the case writes runs: 1"
    assert prepared.submissions == 1


def test_a_case_that_writes_no_runs_key_runs_once(tmp_path: Path) -> None:
    prepared = plan(TREE / "evals" / "greeter" / "no-frontmatter", config=settings(tmp_path))
    assert prepared.entries[0].runs == 1


def test_a_declared_runs_key_is_the_run_count(tmp_path: Path) -> None:
    prepared = plan(TREE / "evals" / "greeter" / "every-key", config=settings(tmp_path))
    assert prepared.entries[0].runs == 2
    assert prepared.entries[0].timeout_seconds == 600.0


def test_an_override_replaces_what_the_case_declared_and_never_multiplies_it(
    tmp_path: Path,
) -> None:
    prepared = plan(
        TREE / "evals" / "greeter" / "every-key",
        config=settings(tmp_path),
        runs=3,
        timeout_seconds=120,
    )
    assert prepared.entries[0].runs == 3
    assert prepared.entries[0].timeout_seconds == 120.0


def test_a_case_declaring_no_timeout_runs_under_the_configured_one(tmp_path: Path) -> None:
    prepared = plan(SMOKE, config=settings(tmp_path, run_timeout=900))
    assert prepared.entries[0].timeout_seconds == 900.0


def test_a_skipped_case_costs_no_ceiling_entry(tmp_path: Path) -> None:
    root, _ = build(tmp_path, frontmatter="max_turns: 12\nruns: 4")
    prepared = plan(root, config=settings(tmp_path))
    assert prepared.entries[0].skips.skipped is True
    assert prepared.entries[0].runs == 4
    assert prepared.entries[0].submissions == 0
    assert prepared.submissions == 0


def test_the_ceiling_arithmetic_is_the_plan_plus_the_run_log(tmp_path: Path) -> None:
    config = settings(tmp_path, max_runs=3)
    log(tmp_path / "runs.jsonl", 2)
    prepared = plan(SMOKE, config=config, runs=1)
    assert prepared.recent == 2
    assert prepared.max_runs == 3
    assert prepared.submissions == 1
    assert prepared.over_ceiling is False

    prepared = plan(SMOKE, config=config, runs=2)
    assert prepared.over_ceiling is True
    assert "max_runs is 3" in prepared.refusal


def test_run_refuses_above_the_ceiling_before_submitting_anything(tmp_path: Path) -> None:
    log(tmp_path / "runs.jsonl", 5)
    output = tmp_path / "out"
    output.mkdir()
    with pytest.raises(CoWorkError) as raised:
        run(SMOKE, output, config=settings(tmp_path, max_runs=3), runs=1)
    assert raised.value.code == 2
    assert list(output.iterdir()) == [], "nothing was written"


def test_a_tag_filter_and_a_case_glob_reach_discovery(tmp_path: Path) -> None:
    config = settings(tmp_path)
    assert plan(TREE, config=config, tags=("greeter",)).entries[0].name == "greets-alex"
    assert plan(TREE, config=config, case_glob="inner-*").entries[0].name == "inner-case"
    assert plan(TREE, config=config, case_glob="no-such-case").entries == ()


# What the target selects.


def test_a_target_covering_two_plugin_roots_raises(tmp_path: Path) -> None:
    for name in ("one", "two"):
        manifest = tmp_path / "marketplace" / name / ".claude-plugin"
        manifest.mkdir(parents=True)
        (manifest / "plugin.json").write_text(MANIFEST, encoding="utf-8")
    with pytest.raises(CaseError) as raised:
        plan(tmp_path / "marketplace", config=settings(tmp_path))
    assert "more than one plugin root" in str(raised.value)


def test_a_target_under_no_plugin_root_raises(tmp_path: Path) -> None:
    (tmp_path / "loose").mkdir()
    with pytest.raises(CaseError):
        plan(tmp_path / "loose", config=settings(tmp_path))


# The document a suite of skipped cases produces.


def test_a_suite_of_skipped_cases_writes_a_document_and_submits_nothing(tmp_path: Path) -> None:
    root, _ = build(tmp_path, frontmatter="model: sonnet")
    output = tmp_path / "out"
    output.mkdir()
    written = run(root, output, config=settings(tmp_path))
    assert written == output / RESULT_NAME

    document = json.loads(written.read_text(encoding="utf-8"))
    assert document["schemaVersion"] == 1
    assert document["partial"] is False
    assert document["costUsd"] == 0.0
    assert document["suite"]["root"] == str(root.resolve())
    assert document["suite"]["judgeModel"] == "haiku"
    assert document["aggregates"] == {
        "casesTotal": 1,
        "casesPassed": 0,
        "overallScore": 0.0,
        "overallPassRate": 0.0,
    }
    entry = document["cases"][0]
    assert entry["skipped"] is True
    assert entry["skipReason"] == "model: the session decides its model"
    assert entry["arms"]["with"] == []
    assert driver_log_is_empty(tmp_path)


def test_the_judge_model_override_reaches_the_suite(tmp_path: Path) -> None:
    root, _ = build(tmp_path, frontmatter="model: sonnet")
    output = tmp_path / "out"
    output.mkdir()
    written = run(root, output, config=settings(tmp_path), judge_model="opus")
    assert json.loads(written.read_text(encoding="utf-8"))["suite"]["judgeModel"] == "opus"


def driver_log_is_empty(tmp_path: Path) -> bool:
    """No submission was made, so the driver's run log was never written."""
    return not (tmp_path / "runs.jsonl").exists()
