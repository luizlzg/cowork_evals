"""The CoWork backend over hand-written case trees. Nothing here starts a session.

The skip rule is docs/running_evals.md, one assertion per row of it. See ../README.md.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from cowork_evals.cases import read
from cowork_evals.cowork_backend import skips

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
