"""The command: the parser, the five verbs, the dispatch and the exit codes.

The surface is [docs/cli.md](../../docs/cli.md), and this module is the whole of it. There
is no second entry point and no per-backend executable.

Printing happens here and nowhere else, and `sys.exit` is called in `console_main` alone.
`main` returns a code. The one exit it does not return is `SystemExit(2)`, which `argparse`
raises from inside `parse_args` for an unknown option or a missing path.

The venv backend is not built, so `--venv` is an unknown option on every verb and
`argparse` exits 2. Its design stays in
[docs/staged_runtime.md](../../docs/staged_runtime.md).
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from . import logs
from .preflight import COWORK, DOCKER

# `check --all`, the one selection that is not a backend.
ALL = "all"

# The exit codes. docs/cli.md. `test` is the one verb that returns a code from below
# unchanged, and it returns pytest's.
OK = 0
GATE_FAILED = 1
USAGE = 2
PREFLIGHT_FAILED = 3
INTERRUPTED = 130

# Each option, and the attribute `argparse` stores it under. The refusal table below names
# options, because that is what an operator typed and what a message has to say back.
OPTION_ATTRIBUTES = {
    "--runs": "runs",
    "--timeout-seconds": "timeout_seconds",
    "--model": "model",
    "--judge-model": "judge_model",
    "--allow-tools": "allow_tools",
    "--max-cost-usd": "max_cost_usd",
    "--build-missing": "build_missing",
}

# What each backend cannot honour. An option here is an operator mistake, so it is a usage
# error. A *case* that needs a field the backend cannot honour is reported skipped and
# fails the gate instead, and the two are never conflated. docs/cli.md.
REFUSED = {
    DOCKER: ("--timeout-seconds",),
    COWORK: ("--model", "--allow-tools", "--max-cost-usd", "--build-missing"),
}

# Why each is refused, so a message says more than that it was.
REFUSAL_REASONS = {
    "--timeout-seconds": "claude plugin eval has no timeout flag to map it onto",
    "--model": "the session decides its model",
    "--allow-tools": "the session decides its tools",
    "--max-cost-usd": "the session is billed to the account and is not observable here",
    "--build-missing": "there is nothing to build on that backend",
}


def build_parser() -> argparse.ArgumentParser:
    """The whole surface. Every option a verb takes is added here and nowhere else."""
    parser = argparse.ArgumentParser(
        prog="cowork_evals",
        description="Run evals for Claude CoWork skills and plugins.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the installed cowork_evals version and exit",
    )
    verbs = parser.add_subparsers(dest="verb")

    _run_parser(verbs)
    _test_parser(verbs)
    _setup_parser(verbs)
    _check_parser(verbs)
    _prune_parser(verbs)
    return parser


def _backend_group(
    verb: argparse.ArgumentParser, *backends: str
) -> argparse._MutuallyExclusiveGroup:
    """The backend flag: mutually exclusive, required, and with no default.

    Its members differ per verb, so a backend a verb does not carry is an unknown option
    and `argparse` exits 2. There is no refusal message to write for one.
    """
    group = verb.add_mutually_exclusive_group(required=True)
    for backend in backends:
        group.add_argument(
            f"--{backend}",
            dest="backend",
            action="store_const",
            const=backend,
            help=f"the {backend} backend",
        )
    return group


def _run_parser(verbs: Any) -> None:
    verb = verbs.add_parser("run", help="run a suite and gate what it produced")
    _backend_group(verb, DOCKER, COWORK)
    verb.add_argument("path", help="a case, a skill, an evals/ tree, a plugin root or a sweep")
    verb.add_argument("--runs", type=int, help="how many times each case runs")
    verb.add_argument("--timeout-seconds", type=float, help="each run's timeout, on --cowork")
    verb.add_argument("--model", help="the model under test, on --docker")
    verb.add_argument("--judge-model", help="the model behind llm and baseline graders")
    verb.add_argument("--allow-tools", nargs="+", help="the tool grant, on --docker")
    verb.add_argument("--max-cost-usd", type=float, help="one suite's ceiling, on --docker")
    verb.add_argument("--tag", action="append", help="keep cases carrying this tag, repeatable")
    verb.add_argument("--case", help="a glob over the case name")
    verb.add_argument("--out", help="the log root, replacing logs/evals")
    verb.add_argument(
        "--build-missing", action="store_true", help="build an absent image instead of failing"
    )
    verb.add_argument(
        "--require-coverage",
        action="store_true",
        help="fail the preflight when a skill has no eval directory",
    )
    verb.add_argument("--dry-run", action="store_true", help="print what would run, and exit 0")


def _test_parser(verbs: Any) -> None:
    """`test` carries a path, two flags and a pytest tail, and no other option.

    Every option it does not carry configures a harness run, and `test` runs no harness. A
    raw tail is allowed here and forbidden on `run`, because pytest is the only thing
    behind this verb and the harness runs on two backends. docs/cowork_test.md.

    The tail begins at `--`, and `argparse` claims no token after it: `--dry-run` there is
    pytest's argument and never this verb's. It is a plain variadic positional and not
    `argparse.REMAINDER`, which would swallow this verb's own two flags whenever they were
    typed after the path.
    """
    verb = verbs.add_parser("test", help="run a consumer's pytest suite on the CoWork runtime")
    _backend_group(verb, DOCKER)
    verb.add_argument("path", help="a path inside one plugin root")
    verb.add_argument(
        "--build-missing", action="store_true", help="build an absent image instead of failing"
    )
    verb.add_argument("--dry-run", action="store_true", help="print the container argument list")
    verb.add_argument(
        "pytest_args",
        nargs="*",
        metavar="-- PYTEST_ARGS",
        help="everything after -- reaches pytest in order and unmodified",
    )


def _setup_parser(verbs: Any) -> None:
    verb = verbs.add_parser("setup", help="build what a backend needs")
    _backend_group(verb, DOCKER)


def _check_parser(verbs: Any) -> None:
    verb = verbs.add_parser("check", help="report what a backend is missing")
    _backend_group(verb, DOCKER, COWORK, ALL)


def _prune_parser(verbs: Any) -> None:
    """`prune` takes any combination of its selection flags, and requires at least one.

    They are not a mutually exclusive group: pruning images and logs in one invocation is
    ordinary. `argparse` cannot express `at least one`, so the refusal is the verb's and
    returns 2.
    """
    verb = verbs.add_parser("prune", help="delete artefacts this command created")
    verb.add_argument("--docker", action="store_true", help="images this command built")
    verb.add_argument("--logs", action="store_true", help="run directories under the log root")
    verb.add_argument(
        "--older-than", type=int, default=logs.RUN_PRUNE_DAYS, help="restrict every selection"
    )
    verb.add_argument("--out", help="the log root, replacing logs/evals")


# The refusals.


def _given(args: argparse.Namespace, attribute: str) -> bool:
    """Whether an option was typed. Every default is `None` or `False`."""
    value = getattr(args, attribute, None)
    return value is not None and value is not False


def refusal(args: argparse.Namespace) -> str | None:
    """The one line naming an option the chosen backend refuses, or `None`."""
    backend = getattr(args, "backend", None)
    for option in REFUSED.get(backend, ()):
        if _given(args, OPTION_ATTRIBUTES[option]):
            return f"{option} is not accepted on --{backend}: {REFUSAL_REASONS[option]}"
    return None


# The entry points.


def main(argv: list[str] | None = None) -> int:
    """Parse, refuse, dispatch, and return an exit code. Nothing here calls `sys.exit`."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(logs.distribution_version())
        return OK
    if args.verb is None:
        parser.print_usage(sys.stderr)
        print("cowork_evals: a verb is required", file=sys.stderr)
        return USAGE

    refused = refusal(args)
    if refused is not None:
        print(refused, file=sys.stderr)
        return USAGE

    try:
        return _dispatch(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return INTERRUPTED


def _dispatch(args: argparse.Namespace) -> int:
    raise NotImplementedError(f"the {args.verb} verb is phase 6")


def console_main() -> None:
    """The `[project.scripts]` entry point, and the one place `sys.exit` is called."""
    sys.exit(main())
