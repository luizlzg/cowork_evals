"""The case validator and the coverage report over hand-written trees.

Every tree is under tests/data/validate/, every expected value is a literal, and nothing
here runs a case. The rules are docs/eval_format.md. See ../README.md.
"""

from __future__ import annotations

from pathlib import Path

from cowork_evals.validate import Violation, uncovered, violations

ROOT = Path(__file__).resolve().parent.parent / "data" / "validate"
CLEAN = ROOT / "clean"
BROKEN = ROOT / "broken"
UNCOVERED = ROOT / "uncovered"
EVALS = BROKEN / "evals" / "greeter"


def rules_at(found: list[Violation], path: Path) -> list[str]:
    return sorted(violation.rule for violation in found if violation.path == path)


# The clean tree.


def test_a_clean_tree_has_no_violation() -> None:
    assert violations(CLEAN) == []


def test_a_clean_tree_covers_every_skill() -> None:
    assert uncovered(CLEAN) == []


def test_a_tree_with_no_eval_directory_has_no_violation(tmp_path: Path) -> None:
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"name": "empty"}')
    assert violations(tmp_path) == []


# The layer directly under evals/.


def test_a_directory_under_evals_naming_no_skill_is_a_violation() -> None:
    found = violations(BROKEN)
    assert rules_at(found, BROKEN / "evals" / "not-a-skill") == ["skill-layer"]


def test_the_skill_layer_names_the_directories_it_admits() -> None:
    only = [
        violation
        for violation in violations(BROKEN)
        if violation.path == BROKEN / "evals" / "not-a-skill"
    ]
    assert only[0].detail == "a directory under evals/ is one of: greeter, mocks, plugin"


def test_a_plugin_with_no_skills_directory_admits_plugin_and_mocks_only(tmp_path: Path) -> None:
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "plugin.json").write_text('{"name": "bare"}')
    for name in ("plugin", "mocks", "greeter"):
        (tmp_path / "evals" / name).mkdir(parents=True)
    found = violations(tmp_path)
    assert [violation.path for violation in found] == [tmp_path / "evals" / "greeter"]


# prompt.md.


def test_a_missing_required_key_is_reported_once_per_key() -> None:
    path = EVALS / "missing-keys" / "prompt.md"
    found = [violation for violation in violations(BROKEN) if violation.path == path]
    assert [violation.rule for violation in found] == ["required-key"] * 3
    assert sorted(violation.detail for violation in found) == [
        "name is required",
        "plugins is required",
        "tags is required",
    ]


def test_a_key_outside_the_format_is_a_violation_including_context() -> None:
    path = EVALS / "unknown-key" / "prompt.md"
    found = [
        violation
        for violation in violations(BROKEN)
        if violation.path == path and violation.rule == "unknown-key"
    ]
    assert [violation.detail for violation in found] == [
        "colour is not a frontmatter key of the format",
        "context.add_dirs is not a frontmatter key of the format",
    ]


def test_every_cap_is_checked_and_an_env_key_carries_its_prefix() -> None:
    path = EVALS / "over-caps" / "prompt.md"
    found = [violation for violation in violations(BROKEN) if violation.path == path]
    assert sorted(violation.detail for violation in found) == [
        "env key NOT_PREFIXED does not start with EVAL_",
        "max_turns is 201, and the cap is 200",
        "runs is 51, and the cap is 50",
        "timeout_seconds is 3601, and the cap is 3600",
    ]


def test_a_value_at_the_cap_is_not_a_violation(tmp_path: Path) -> None:
    case = _one_case(tmp_path, "runs: 50\nmax_turns: 200\ntimeout_seconds: 3600\n")
    assert violations(case) == []


def test_tags_names_the_case_own_skill_directory() -> None:
    path = EVALS / "wrong-tag" / "prompt.md"
    assert rules_at(violations(BROKEN), path) == ["tags"]


def test_plugins_must_resolve_to_the_plugin_root() -> None:
    path = EVALS / "wrong-plugins" / "prompt.md"
    found = [violation for violation in violations(BROKEN) if violation.path == path]
    assert [violation.rule for violation in found] == ["plugins"]
    assert str(BROKEN) in found[0].detail


# case.yaml.


def test_case_yaml_requires_its_two_keys_and_refuses_a_third() -> None:
    path = EVALS / "bad-case-yaml" / "case.yaml"
    found = [violation for violation in violations(BROKEN) if violation.path == path]
    assert sorted(violation.detail for violation in found) == [
        "expected_outcome is not a key of case.yaml",
        "name is required",
        "schema_version is '1.0', and it is '1.1'",
    ]


def test_an_add_dirs_entry_outside_the_case_directory_is_a_violation() -> None:
    path = EVALS / "escaping" / "case.yaml"
    found = [violation for violation in violations(BROKEN) if violation.path == path]
    assert [violation.rule for violation in found] == ["add-dirs"]
    assert str(EVALS / "wrong-tag") in found[0].detail


# Graders.


def test_a_grader_file_with_no_frontmatter_block_is_a_violation() -> None:
    path = EVALS / "bad-graders" / "graders" / "note.md"
    assert rules_at(violations(BROKEN), path) == ["grader-frontmatter"]


def test_an_unknown_grader_type_is_a_violation() -> None:
    path = EVALS / "bad-graders" / "graders" / "unknown-type.md"
    assert rules_at(violations(BROKEN), path) == ["grader-type"]


def test_a_weight_at_or_below_zero_is_a_violation() -> None:
    path = EVALS / "bad-graders" / "graders" / "zero-weight.md"
    assert rules_at(violations(BROKEN), path) == ["grader-weight"]


# The reserved tag, in both directions.


def _runnability_case(
    root: Path,
    *,
    tags: str = "[greeter]",
    extra: str = "",
    case_yaml: str | None = None,
    mocks_at: tuple[str, ...] = (),
    depth: tuple[str, ...] = (),
) -> Path:
    """One plugin root holding one case, with whatever makes it unrunnable on CoWork.

    `depth` is the grouping directories between `evals/greeter/` and the case, which is how
    a case several layers below an `evals/mocks/` is written.
    """
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "one"}')
    (root / "skills" / "greeter").mkdir(parents=True)
    case = root.joinpath("evals", "greeter", *depth, "hello")
    case.mkdir(parents=True)
    up = "/".join([".."] * (3 + len(depth)))
    (case / "prompt.md").write_text(
        f'---\nname: hello\ntags: {tags}\nplugins: ["{up}"]\n{extra}---\n\nSay hello.\n'
    )
    if case_yaml is not None:
        (case / "case.yaml").write_text(case_yaml)
    for relative in mocks_at:
        (root / relative / "mocks" / "mailer").mkdir(parents=True)
        (root / relative / "mocks" / "mailer" / "send.md").write_text("---\ntool: send\n---\n")
    return root


def test_an_unhonoured_key_with_no_tag_is_a_violation_naming_the_key(tmp_path: Path) -> None:
    found = violations(_runnability_case(tmp_path, extra="max_turns: 10\n"))
    assert [violation.rule for violation in found] == ["no-cowork-missing"]
    assert found[0].detail == (
        "max_turns: no turn cap reaches a CoWork session, and tags does not carry no-cowork"
    )


def test_a_context_key_with_no_tag_is_a_violation_naming_the_key(tmp_path: Path) -> None:
    found = violations(
        _runnability_case(
            tmp_path,
            case_yaml='schema_version: "1.1"\nname: hello\ncontext:\n  add_dirs: ["fixtures"]\n',
        )
    )
    assert [violation.rule for violation in found] == ["no-cowork-missing"]
    assert found[0].detail == (
        "context.add_dirs: nothing stages files into the VM, and tags does not carry no-cowork"
    )


def test_a_mocks_directory_with_no_tag_is_a_violation_naming_the_directory(tmp_path: Path) -> None:
    found = violations(_runnability_case(tmp_path, mocks_at=("evals",)))
    assert [violation.rule for violation in found] == ["no-cowork-missing"]
    assert found[0].detail.startswith(str(tmp_path / "evals" / "mocks"))
    assert "and tags does not carry no-cowork" in found[0].detail


def test_the_tag_on_a_case_nothing_stops_is_a_violation(tmp_path: Path) -> None:
    """The second direction, which is what keeps the tag from switching a case off."""
    found = violations(_runnability_case(tmp_path, tags="[greeter, no-cowork]"))
    assert [violation.rule for violation in found] == ["no-cowork-unneeded"]
    assert found[0].detail == "tags carries no-cowork, and a CoWork session can run this case"


def test_an_unhonoured_key_with_the_tag_is_valid(tmp_path: Path) -> None:
    assert (
        violations(
            _runnability_case(tmp_path, tags="[greeter, no-cowork]", extra="max_turns: 10\n")
        )
        == []
    )


def test_a_mocks_directory_several_layers_above_the_case_is_valid_with_the_tag(
    tmp_path: Path,
) -> None:
    """The chain is walked from the plugin root, not from the case's own directory."""
    root = _runnability_case(
        tmp_path, tags="[greeter, no-cowork]", mocks_at=("evals",), depth=("group", "inner")
    )
    assert violations(root) == []


# The whole list.


def test_every_violation_is_sorted_by_path() -> None:
    found = violations(BROKEN)
    assert [str(violation.path) for violation in found] == sorted(
        str(violation.path) for violation in found
    )


def test_a_violation_prints_its_path_its_rule_and_its_detail() -> None:
    violation = Violation(path=Path("a/prompt.md"), rule="tags", detail="something")
    assert str(violation) == "a/prompt.md: tags: something"


# Coverage.


def test_a_skill_with_no_eval_directory_is_reported_and_is_not_a_violation() -> None:
    assert violations(UNCOVERED) == []
    assert uncovered(UNCOVERED) == [
        f"{UNCOVERED / 'skills' / 'writer'}: no eval directory at {UNCOVERED / 'evals' / 'writer'}"
    ]


def test_a_plugin_with_no_skills_directory_reports_no_coverage_gap() -> None:
    assert uncovered(BROKEN.parent / "clean") == []


def _one_case(root: Path, extra: str) -> Path:
    """One plugin root holding one otherwise valid case, for a rule tested on its own."""
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text('{"name": "one"}')
    (root / "skills" / "greeter").mkdir(parents=True)
    case = root / "evals" / "greeter" / "hello"
    case.mkdir(parents=True)
    # The tag, because the one caller writes `max_turns`. docs/eval_format.md.
    (case / "prompt.md").write_text(
        f'---\nname: hello\ntags: [greeter, no-cowork]\nplugins: ["../../.."]\n'
        f"{extra}---\n\nSay hello.\n"
    )
    return root
