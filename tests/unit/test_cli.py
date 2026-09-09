"""The parser, the refusals and the exit codes.

The parser under test is the real one, built by `build_parser`. `argparse` raises
`SystemExit(2)` from inside `parse_args`, and the rows that reach it assert on that; every
other refusal is a value `main` returns. The surface is docs/cli.md. See ../README.md.
"""

from __future__ import annotations

import pytest

from cowork_evals import logs
from cowork_evals.cli import USAGE, build_parser, main


def parse(*argv: str):
    return build_parser().parse_args(list(argv))


# Each verb's parse tree.


def test_run_takes_a_backend_a_path_and_every_option() -> None:
    args = parse(
        "run",
        "--docker",
        "plugin/evals",
        "--runs",
        "2",
        "--model",
        "sonnet",
        "--judge-model",
        "haiku",
        "--allow-tools",
        "Bash",
        "Write",
        "--max-cost-usd",
        "3",
        "--tag",
        "greeter",
        "--tag",
        "writer",
        "--case",
        "hello-*",
        "--out",
        "elsewhere",
        "--build-missing",
        "--require-coverage",
        "--dry-run",
    )
    assert args.verb == "run"
    assert args.backend == "docker"
    assert args.path == "plugin/evals"
    assert args.runs == 2
    assert args.model == "sonnet"
    assert args.judge_model == "haiku"
    assert args.allow_tools == ["Bash", "Write"]
    assert args.max_cost_usd == 3.0
    assert args.tag == ["greeter", "writer"]
    assert args.case == "hello-*"
    assert args.out == "elsewhere"
    assert args.build_missing
    assert args.require_coverage
    assert args.dry_run


def test_run_defaults_every_option_to_nothing() -> None:
    args = parse("run", "--cowork", "plugin/evals")
    assert (args.runs, args.timeout_seconds, args.model, args.judge_model) == (
        None,
        None,
        None,
        None,
    )
    assert (args.allow_tools, args.max_cost_usd, args.tag, args.case, args.out) == (
        None,
        None,
        None,
        None,
        None,
    )
    assert not args.build_missing
    assert not args.require_coverage
    assert not args.dry_run


def test_test_takes_a_path_two_flags_and_a_tail() -> None:
    args = parse("test", "--docker", "plugin/tests", "--build-missing", "--dry-run")
    assert (args.verb, args.backend, args.path) == ("test", "docker", "plugin/tests")
    assert args.build_missing
    assert args.dry_run
    assert args.pytest_args == []


def test_setup_takes_docker_alone() -> None:
    assert parse("setup", "--docker").backend == "docker"


def test_check_takes_both_backends_and_all() -> None:
    assert parse("check", "--docker").backend == "docker"
    assert parse("check", "--cowork").backend == "cowork"
    assert parse("check", "--all").backend == "all"


def test_prune_takes_any_combination_of_its_selection_flags() -> None:
    args = parse("prune", "--docker", "--logs", "--older-than", "7", "--out", "elsewhere")
    assert args.docker and args.logs
    assert args.older_than == 7
    assert args.out == "elsewhere"


def test_prune_defaults_to_the_same_age_run_prunes_at() -> None:
    assert parse("prune", "--logs").older_than == logs.RUN_PRUNE_DAYS


def test_older_than_is_a_prune_flag_only() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("run", "--docker", "plugin/evals", "--older-than", "7")
    assert raised.value.code == USAGE


def test_out_is_on_run_and_prune_and_nowhere_else() -> None:
    assert parse("run", "--docker", "p", "--out", "x").out == "x"
    assert parse("prune", "--logs", "--out", "x").out == "x"
    with pytest.raises(SystemExit):
        parse("test", "--docker", "p", "--out", "x")


# The pytest tail.


def test_the_tail_begins_at_the_separator_and_survives_token_for_token() -> None:
    args = parse("test", "--docker", "plugin/tests", "--", "-k", "parser", "-v", "--tb=short")
    assert args.pytest_args == ["-k", "parser", "-v", "--tb=short"]


def test_argparse_claims_no_token_after_the_separator() -> None:
    """`--dry-run` after `--` is pytest's argument and never this command's."""
    args = parse("test", "--docker", "plugin/tests", "--", "--dry-run", "--build-missing")
    assert args.pytest_args == ["--dry-run", "--build-missing"]
    assert not args.dry_run
    assert not args.build_missing


def test_run_takes_no_raw_tail() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("run", "--docker", "plugin/evals", "--", "-k", "parser")
    assert raised.value.code == USAGE


# The backend is required, and its members differ per verb.


def test_a_verb_with_no_backend_is_a_usage_error() -> None:
    for argv in (("run", "plugin/evals"), ("test", "plugin/tests"), ("setup",), ("check",)):
        with pytest.raises(SystemExit) as raised:
            parse(*argv)
        assert raised.value.code == USAGE


def test_run_with_no_path_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("run", "--docker")
    assert raised.value.code == USAGE


def test_two_backends_at_once_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("run", "--docker", "--cowork", "plugin/evals")
    assert raised.value.code == USAGE


def test_run_all_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("run", "--all", "plugin/evals")
    assert raised.value.code == USAGE


def test_test_cowork_is_a_usage_error() -> None:
    """That backend is not a member of the group, so there is no refusal message."""
    with pytest.raises(SystemExit) as raised:
        parse("test", "--cowork", "plugin/tests")
    assert raised.value.code == USAGE


def test_setup_cowork_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("setup", "--cowork")
    assert raised.value.code == USAGE


def test_venv_is_an_unknown_option_on_every_verb() -> None:
    for argv in (
        ("run", "--venv", "plugin/evals"),
        ("test", "--venv", "plugin/tests"),
        ("setup", "--venv"),
        ("check", "--venv"),
        ("prune", "--venv"),
    ):
        with pytest.raises(SystemExit) as raised:
            parse(*argv)
        assert raised.value.code == USAGE


def test_an_unknown_option_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as raised:
        parse("run", "--docker", "plugin/evals", "--invented")
    assert raised.value.code == USAGE


# The refusals a backend makes, which are values main returns.


def test_the_cowork_backend_accepts_runs_judge_model_and_timeout_seconds() -> None:
    args = parse(
        "run",
        "--cowork",
        "plugin/evals",
        "--runs",
        "2",
        "--judge-model",
        "haiku",
        "--timeout-seconds",
        "900",
    )
    assert (args.runs, args.judge_model, args.timeout_seconds) == (2, "haiku", 900.0)


@pytest.mark.parametrize(
    ("option", "value"),
    [("--model", "sonnet"), ("--allow-tools", "Bash"), ("--max-cost-usd", "3")],
)
def test_an_option_the_cowork_backend_refuses_returns_two(option, value, capsys) -> None:
    assert main(["run", "--cowork", "plugin/evals", option, value]) == USAGE
    assert f"{option} is not accepted on --cowork" in capsys.readouterr().err


def test_build_missing_is_refused_on_cowork(capsys) -> None:
    assert main(["run", "--cowork", "plugin/evals", "--build-missing"]) == USAGE
    assert "--build-missing is not accepted on --cowork" in capsys.readouterr().err


def test_timeout_seconds_is_refused_on_docker(capsys) -> None:
    assert main(["run", "--docker", "plugin/evals", "--timeout-seconds", "900"]) == USAGE
    assert "--timeout-seconds is not accepted on --docker" in capsys.readouterr().err


def test_require_coverage_is_accepted_on_both_backends() -> None:
    """It reads the tree and not a backend, so no backend refuses it."""
    for backend in ("--docker", "--cowork"):
        assert parse("run", backend, "plugin/evals", "--require-coverage").require_coverage


# The version, and no verb at all.


def test_the_version_is_the_installed_distribution_version(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == logs.distribution_version()


def test_no_verb_at_all_is_a_usage_error(capsys) -> None:
    assert main([]) == USAGE
    assert "a verb is required" in capsys.readouterr().err
