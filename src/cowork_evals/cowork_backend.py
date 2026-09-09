"""The CoWork backend: which case this backend can run, and what running one produces.

The layer above the driver. It reads the case tree `cases.py` produced, submits each case's
prompt through `CoWork`, grades the session document, and writes the same
`aggregate-result.json` v1 document every other backend writes.

The skip rule is docs/running_evals.md: a key the case wrote out is honoured when this backend's
behaviour already satisfies it, and skipped otherwise. A key the case left to its default is not
a request and is not a skip, which is why this reads `Case.frontmatter_keys` and
`Case.case_yaml_keys` and never a merged value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .cases import EVAL_DIR, JUDGED, Case, CaseError, discover, plugin_roots
from .config import Config, CoWorkError
from .cowork import CoWork
from .grader import grade as grade_structural
from .grader import skipped as skipped_result
from .judge import grade as grade_judged
from .judge import resolve_model
from .results import CaseResult, Run, build, write

# The MCP stand-in directory. Its three layers, suite, group and case, are
# docs/claude_code/plugin_eval_reference.md.
MOCKS_DIR = "mocks"

# The grader target and focus value that names those stand-ins.
MOCK_CALLS = "mock_calls"

# Case keys this backend cannot honour, each with why. The session decides its own model,
# its own tools and its own system prompt, and no turn cap reaches it.
# docs/approaches.md.
UNHONOURED_CASE_KEYS = {
    "max_turns": "no turn cap reaches a CoWork session",
    "model": "the session decides its model",
    "allowed_tools": "the session decides its tools",
    "append_system_prompt": "the session decides its system prompt",
    "env": "nothing sets an environment variable in the VM",
}

# The `case.yaml` keys, which are all of one shape and share one reason.
CONTEXT_PREFIX = "context."
CONTEXT_REASON = "nothing stages files into the VM"


@dataclass(frozen=True, slots=True)
class Skips:
    """Why a case submits nothing, and why a grader is not scored.

    The two are never one list. A `case` reason submits nothing and leaves `arms.with`
    empty. A `graders` entry runs the case and drops that grader from the score, so a case
    does not fail for a grader that was never asked.
    """

    case: tuple[str, ...] = ()
    graders: dict[str, str] = field(default_factory=dict)

    @property
    def skipped(self) -> bool:
        return bool(self.case)

    @property
    def reason(self) -> str:
        """Every case reason as one line, for the result document's `skipReason`."""
        return "; ".join(self.case)


def skips(case: Case, plugin_root: Path | str) -> Skips:
    """What this backend cannot honour in one case. It reads files and submits nothing.

    `plugin_root` is where the `evals/` tree starts, which is what makes a suite-wide
    `evals/mocks/` reach a case several directories below it.
    """
    reasons = [
        f"{key}: {why}" for key, why in UNHONOURED_CASE_KEYS.items() if key in case.frontmatter_keys
    ]
    reasons += [
        f"{key}: {CONTEXT_REASON}" for key in case.case_yaml_keys if key.startswith(CONTEXT_PREFIX)
    ]
    reasons += [
        f"{directory / MOCKS_DIR}: stand-ins are the harness's, and the MCP servers here are real"
        for directory in _mock_layers(case.directory, Path(plugin_root))
    ]
    return Skips(case=tuple(reasons), graders=_grader_skips(case))


def _grader_skips(case: Case) -> dict[str, str]:
    """The one grader skip that is decided before a run.

    The other one, an `llm` grader whose focus turns out to be an image, is read from the
    file's bytes and so exists only after the run. `judge.py` decides that one.
    """
    skipped = {}
    for grader in case.graders:
        for key in ("target", "focus"):
            if grader.config.get(key) == MOCK_CALLS:
                skipped[grader.name] = f"{key}: {MOCK_CALLS}, and no stand-in serves a CoWork run"
                break
    return skipped


def _mock_layers(case_dir: Path, plugin_root: Path) -> list[Path]:
    """Every directory from `evals/` down to the case that carries a `mocks/`.

    `evals/mocks/` skips every case in the plugin and a case's own `mocks/` skips that case
    alone, which are the layers the harness adds up.
    """
    case_dir = case_dir.resolve()
    evals = (plugin_root.resolve() / EVAL_DIR).resolve()
    above = [case_dir, *case_dir.parents]
    chain = above[: above.index(evals) + 1] if evals in above else [case_dir]
    return [directory for directory in reversed(chain) if (directory / MOCKS_DIR).is_dir()]


# A case that writes no `runs` key runs once here. docs/running_evals.md.
DEFAULT_RUNS = 1

# The driver failure that is collected rather than discarded: the run timed out, the session
# kept going in the VM, and what it produced up to that point is still graded. That is what
# the harness does. docs/cowork_driver.md.
RUN_TIMEOUT_CODE = 7


@dataclass(frozen=True, slots=True)
class Entry:
    """One case as this backend will run it: what it can honour, how often, how long."""

    case: Case
    skips: Skips
    runs: int
    timeout_seconds: float

    @property
    def name(self) -> str:
        return self.case.name

    @property
    def submissions(self) -> int:
        """What this case costs the ceiling. A skipped case submits nothing."""
        return 0 if self.skips.skipped else self.runs


@dataclass(frozen=True, slots=True)
class Plan:
    """What a suite will do, decided without submitting anything.

    `run` calls this, and so does `--dry-run --cowork`, which prints exactly these and would
    otherwise re-derive them. It carries the case skips and the grader skips `skips` decides,
    and not the image-focus skip the judge decides after a run.
    """

    root: Path
    entries: tuple[Entry, ...]
    recent: int
    max_runs: int

    @property
    def submissions(self) -> int:
        return sum(entry.submissions for entry in self.entries)

    @property
    def over_ceiling(self) -> bool:
        return self.submissions + self.recent > self.max_runs

    @property
    def arithmetic(self) -> str:
        """The three numbers the ceiling compares. `--dry-run --cowork` prints it."""
        return (
            f"{self.submissions} submissions planned, "
            f"{self.recent} already made in the last 24 hours, max_runs is {self.max_runs}"
        )

    @property
    def refusal(self) -> str:
        return f"the rate ceiling would be exceeded: {self.arithmetic}"


def plan(
    target: Path | str,
    *,
    config: Config | None = None,
    runs: int | None = None,
    timeout_seconds: float | None = None,
    judge_model: str | None = None,
    tags: tuple[str, ...] = (),
    case_glob: str | None = None,
) -> Plan:
    """What `run` would do. It reads files, submits nothing and raises only `CaseError`.

    `judge_model` is accepted here so that one signature covers both calls; it changes
    nothing a plan reports, and reaches the judge and `suite.judgeModel` through `run`.
    """
    del judge_model
    settings = (config if config is not None else Config.load()).cowork
    root = _one_plugin_root(target)
    entries = tuple(
        Entry(
            case=case,
            skips=skips(case, root),
            runs=_effective_runs(case, runs),
            timeout_seconds=_effective_timeout(case, timeout_seconds, settings.run_timeout),
        )
        for case in discover(target, tags=tags, case_glob=case_glob)
    )
    return Plan(
        root=root,
        entries=entries,
        recent=CoWork(settings).recent(),
        max_runs=settings.max_runs,
    )


def run(
    target: Path | str,
    output_dir: Path | str,
    *,
    config: Config | None = None,
    runs: int | None = None,
    timeout_seconds: float | None = None,
    judge_model: str | None = None,
    tags: tuple[str, ...] = (),
    case_glob: str | None = None,
) -> Path:
    """Run every selected case and return the path of the result document written.

    Cases run in sequence, and the runs of a case run in sequence: there is one desktop
    application and one composer. The caller created `output_dir`, as it does for
    `Docker.run`. Nothing here names a run directory, writes a `latest` symlink, writes an
    `env.txt`, prunes, prints, or decides pass or fail. docs/cli.md.
    """
    resolved = config if config is not None else Config.load()
    prepared = plan(
        target,
        config=resolved,
        runs=runs,
        timeout_seconds=timeout_seconds,
        tags=tags,
        case_glob=case_glob,
    )
    if prepared.over_ceiling:
        raise CoWorkError(2, prepared.refusal)

    model = resolve_model(judge_model, resolved)
    started = datetime.now(UTC)
    results = [_run_case(entry, resolved, model) for entry in prepared.entries]
    document = build(
        root=prepared.root,
        cases=results,
        started_at=started.isoformat(),
        duration_seconds=(datetime.now(UTC) - started).total_seconds(),
        judge_model=model,
        case_filter=case_glob,
        tag_filters=tags,
    )
    return write(output_dir, document)


# One case, and one run of it.


def _run_case(entry: Entry, config: Config, model: str) -> CaseResult:
    """Every run of one case. A skipped case submits nothing and leaves `arms.with` empty."""
    if entry.skips.skipped:
        return CaseResult(case=entry.case, skipped=True, skip_reason=entry.skips.reason)

    # `Config` is frozen, so a differing timeout is a differing `CoWork`. The ceiling and
    # the run log are files, and still count across instances.
    driver = CoWork(config.cowork, run_timeout=entry.timeout_seconds)
    return CaseResult(
        case=entry.case, runs=tuple(_one_run(driver, entry, model) for _ in range(entry.runs))
    )


def _one_run(driver: CoWork, entry: Entry, model: str) -> Run:
    """One submission. A `CoWorkError` becomes this run's error, and the suite continues."""
    try:
        session = driver.run(entry.case.prompt)
    except CoWorkError as error:
        return _after_failure(driver, entry, model, error)
    return _graded(session, entry, model)


def _after_failure(driver: CoWork, entry: Entry, model: str, error: CoWorkError) -> Run:
    """What is still readable after the driver raised.

    A run timeout is collected: the error carries the session directory, the CoWork session
    keeps running in the VM, and the run is graded on what it produced up to that point,
    with `error` recording the timeout. A `collect` that then raises code 8, meaning the
    session wrote no assistant text before the timeout, leaves the run with the timeout as
    its error, score 0 and no graders.
    """
    message = _message(error)
    session_dir = None if error.session_dir is None else str(error.session_dir)
    if error.code == RUN_TIMEOUT_CODE and error.session_dir is not None:
        try:
            session = driver.collect(error.session_dir, prompt=entry.case.prompt)
        except CoWorkError:
            return Run(
                session_dir=session_dir, timeout_seconds=entry.timeout_seconds, error=message
            )
        return _graded(session, entry, model, error=message)
    return Run(session_dir=session_dir, timeout_seconds=entry.timeout_seconds, error=message)


def _graded(session: dict[str, Any], entry: Entry, model: str, *, error: str | None = None) -> Run:
    """Every grader of one case against one session document, structural then judged."""
    results = []
    judge_cost = 0.0
    for grader in entry.case.graders:
        reason = entry.skips.graders.get(grader.name)
        if reason is not None:
            results.append(skipped_result(grader, reason))
        elif grader.type in JUDGED:
            judged = grade_judged(grader, session, entry.case.directory, model=model)
            results.append(judged.result)
            judge_cost += judged.cost_usd
        else:
            results.append(grade_structural(grader, session))
    return Run.collected(
        session,
        tuple(results),
        timeout_seconds=entry.timeout_seconds,
        judge_cost_usd=judge_cost,
        error=error,
    )


def _message(error: CoWorkError) -> str:
    return f"{error.code}: {error}"


# What a target selects, and what a case asked for.


def _one_plugin_root(target: Path | str) -> Path:
    """The one plugin root the target covers.

    A target covering more than one is a usage error in docs/cli.md, and the CLI is what
    exits: there is no sweep on this backend, for the reason in docs/running_evals.md.
    """
    resolved = Path(target).resolve()
    roots = plugin_roots(resolved)
    if len(roots) > 1:
        named = ", ".join(str(root) for root in roots)
        raise CaseError(f"{resolved} covers more than one plugin root: {named}")
    return roots[0]


def _effective_runs(case: Case, override: int | None) -> int:
    if override is not None:
        return override
    declared = case.frontmatter_keys.get("runs")
    if isinstance(declared, int) and not isinstance(declared, bool):
        return declared
    return DEFAULT_RUNS


def _effective_timeout(case: Case, override: float | None, configured: float) -> float:
    if override is not None:
        return float(override)
    declared = case.frontmatter_keys.get("timeout_seconds")
    if isinstance(declared, int | float) and not isinstance(declared, bool):
        return float(declared)
    return float(configured)
