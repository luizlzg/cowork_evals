"""Pass and fail over the result documents one invocation produced.

It reads `<plugin>/aggregate-result.json`, so one verdict covers every backend and a sweep is
decided once rather than once per plugin. The conditions are the pass and fail table in
docs/running_evals.md.

Structural graders decide the verdict. Judged graders are printed and decide nothing, because
a judged grader over a non-deterministic agent is a flaky verdict. A skip fails the run, so a
backend cannot go green by honouring nothing. A case that declared the backend cannot run it
is counted instead, and the summary line says how many, because that is a fact about the case
and not a backend honouring nothing.

Nothing here writes a file or prints. The caller writes `lines` to `verdict.txt` and prints
them, and turns `passed` into an exit code. [cli.py](cli.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cases import JUDGED
from .harness import RESULT_NAME
from .results import DECLARED_UNRUNNABLE
from .traces import DENIED, UNOFFERED

# The one schema this module reads. The contract is additive-only, so an unknown field is
# ignored and a different version is a failure.
# docs/claude_code/plugin_eval_reference.md.
SCHEMA_VERSION = 1

# The arm this module reads. There is no baseline arm on either backend.
# docs/running_evals.md.
ARM = "with"

# The two tags every line carries, so a judged failure is never read as the cause of exit 1.
FAIL = "FAIL"
NOTE = "NOTE"

# How a line names where one run's artefacts are. What is in that directory is
# docs/running_evals.md; the container backend fills it through traces.py.
ARTIFACTS = "artifacts"

# The two validity fields traces.py writes, and what a run carrying each is told. Both say
# the model never had a tool the case was granted, so the score is not a fact about the
# plugin. docs/running_evals.md.
VALIDITY = {
    DENIED: "the permission mode refused",
    UNOFFERED: "the run was never offered",
}


@dataclass(frozen=True, slots=True)
class Verdict:
    """The decision, and every line that explains it. The summary line is the last one."""

    passed: bool
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "".join(f"{line}\n" for line in self.lines)


def decide(run_dir: Path | str, *, found: int, picked: int, extra: tuple[str, ...] = ()) -> Verdict:
    """Read every result document one level under the run directory and decide once.

    `extra` is a failure line the caller already holds, which is how a sweep stopped by the
    total cost ceiling reaches the verdict without a second code path.

    `found` and `picked` are the caller's counts over the case tree it read before it ran
    anything: how many cases are there, and how many the filters kept. This module counts the
    other two, and the summary line prints all four. docs/running_evals.md.
    """
    directory = Path(run_dir)
    failures = [f"{FAIL} {line}" for line in extra]
    notes: list[str] = []
    totals = _Totals(found=found, picked=picked)

    for plugin in sorted(child for child in directory.iterdir() if child.is_dir()):
        document, unreadable = _read(plugin / RESULT_NAME)
        if unreadable is not None:
            failures.append(f"{FAIL} {unreadable}")
            continue
        totals.add(document)
        _judge_document(plugin.name, document, failures, notes, totals)

    return Verdict(passed=not failures, lines=(*failures, *notes, totals.summary))


# Reading one document.


def _read(path: Path) -> tuple[dict[str, Any], None] | tuple[dict[str, Any], str]:
    """The document, or the one line that says why no verdict can be reached on it."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}, f"{path}: no result document"
    except ValueError as error:
        return {}, f"{path}: unparsable result document: {error}"
    if not isinstance(document, dict):
        return {}, f"{path}: expected a mapping at the top level"
    version = document.get("schemaVersion")
    if version != SCHEMA_VERSION:
        return {}, f"{path}: schemaVersion is {version!r}, and this module reads {SCHEMA_VERSION}"
    return document, None


def _judge_document(
    plugin: str, document: dict[str, Any], failures: list[str], notes: list[str], totals: _Totals
) -> None:
    if document.get("partial"):
        reason = document.get("partialReason")
        failures.append(f"{FAIL} {plugin}: partial results: {reason}")
        totals.stopped(reason)
    for case in document.get("cases") or []:
        _judge_case(plugin, case, failures, notes, totals)


def _judge_case(
    plugin: str, case: dict[str, Any], failures: list[str], notes: list[str], totals: _Totals
) -> None:
    """One case, and whether anything about it failed.

    The pass count is this package's own: a case passed when it produced no failure line.
    `aggregates.casesPassed` is the harness's count under `--threshold 0`, which is every
    case always, so reading it back would print a pass beside a failure line.
    docs/running_evals.md.

    A case the backend declared unrunnable is counted and neither passes nor fails. It is out
    of the backend's own `casesTotal` as well, so it is on the summary line and nowhere else.
    """
    before = len(failures)
    where = f"{plugin}/{case.get('name')}"
    if case.get(DECLARED_UNRUNNABLE):
        totals.declare_one()
        return
    if case.get("skipped"):
        failures.append(f"{FAIL} {where}: the case was skipped: {case.get('skipReason')}")
        return
    definitions = {
        definition.get("name"): definition.get("type")
        for definition in case.get("graders") or []
        if isinstance(definition, dict)
    }
    for index, run in enumerate(case.get("arms", {}).get(ARM) or [], start=1):
        _judge_run(f"{where}: run {index}", run, definitions, failures, notes)
    if len(failures) == before:
        totals.pass_one()


def _judge_run(
    where: str,
    run: dict[str, Any],
    definitions: dict[Any, Any],
    failures: list[str],
    notes: list[str],
) -> None:
    """One run of one case. An `error` fails on every backend, and so does either validity
    field.

    On CoWork an `error` is a case the driver could not run or collect. On the harness it is a
    run that timed out, hit the turn cap or exited non-zero, each of which is still graded on
    what it produced, so the score alone does not catch it.

    The two validity fields are the container backend's, written by traces.py out of the
    kept trace. A run that never had a tool the case was granted is scored on what the model
    wrote without it, so the score is not a fact about the plugin and the run fails instead.
    Neither field appears on a CoWork run or on a run that kept no trace.
    """
    kept = artifacts(run)
    error = run.get("error")
    if error:
        failures.append(f"{FAIL} {where}: {error}{kept}")
    for field, what in VALIDITY.items():
        named = run.get(field)
        if named:
            tools = ", ".join(str(tool) for tool in named)
            failures.append(
                f"{FAIL} {where}: {what} {tools}, so the score is not a fact about the plugin{kept}"
            )
    for result in run.get("graders") or []:
        _judge_grader(where, result, definitions, failures, notes, kept)


def _judge_grader(
    where: str,
    result: dict[str, Any],
    definitions: dict[Any, Any],
    failures: list[str],
    notes: list[str],
    kept: str = "",
) -> None:
    """One grader result, joined to its definition by name to learn its class.

    A result carries `name`, `passed` and `scored` and never `type`, so the definition is
    the only route to the class. docs/running_evals.md.

    `kept` is the run's artefact suffix, on every line a person would investigate: a judged
    note needs the transcript as much as a structural failure does. A skip and an undefined
    grader do not carry one, because neither is a verdict about what the model produced.
    """
    name = result.get("name")
    at = f"{where}: {name}"
    if name not in definitions:
        failures.append(f"{FAIL} {at}: no grader of that name is defined in the case")
        return
    if result.get("skipped"):
        failures.append(f"{FAIL} {at}: the grader was skipped: {result.get('skipReason')}")
        return
    if not result.get("scored", True):
        failures.append(f"{FAIL} {at}: not scored, and --ablation none drops no grader")
        return
    if result.get("passed"):
        return
    kind = definitions[name]
    line = f"{at}: the {kind} grader failed: {result.get('explanation')}{kept}"
    if kind in JUDGED:
        notes.append(f"{NOTE} {line}")
    else:
        failures.append(f"{FAIL} {line}")


def artifacts(run: dict[str, Any]) -> str:
    """What one run left on the host, as the suffix a failure line carries.

    `tracePath` is where the trace is, and every other artefact of that run sits beside it,
    so naming its directory names all of them. It is the container backend's collected
    directory once `traces.collect` has rewritten it, and the session's transcript
    directory on CoWork.

    Empty when there is no such directory, which is a run whose trace was not collected and
    a document written before this was built. It never names a path that is not there.
    """
    named = run.get("tracePath")
    if not isinstance(named, str) or not named:
        return ""
    directory = Path(named).parent
    if not directory.is_dir():
        return ""
    return f" [{ARTIFACTS}: {_display(directory)}]"


def _display(directory: Path) -> str:
    """The directory as a person types it: relative to the working directory when it is
    under one, and absolute when it is not."""
    try:
        return str(directory.relative_to(Path.cwd()))
    except ValueError:
        return str(directory)


# The summary.


class _Totals:
    """The five counts on the last line, and the mean of each document's score.

    | Count      | Is                                              | Counted by       |
    | ---------- | ----------------------------------------------- | ---------------- |
    | `found`    | The cases under the path, before any filter     | the caller       |
    | `picked`   | The cases `--tag` and `--case` kept             | the caller       |
    | `ran`      | The cases a backend reported running            | `casesTotal`     |
    | `passed`   | The cases that produced no failure line         | this module      |
    | `declared` | The cases a backend was told it cannot run      | this module      |

    A declared case is why `ran` can be below `picked` on a suite where nothing went wrong,
    which is what putting it on the line rather than leaving it absent says.

    Picked and ran are two counts of two things, the second of which is the harness's. They
    differ when a plugin failed to run, when the sweep stopped early, or when the harness
    picked differently. Both are printed and neither is checked against the other.

    A document whose `casesTotal` is 0 is counted and is not a failure. A `--tag` sweep
    matches no case in most plugins, and failing on that would make every filtered sweep
    red. docs/running_evals.md.
    """

    def __init__(self, *, found: int, picked: int) -> None:
        self.found = found
        self.picked = picked
        self.ran = 0
        self.passed = 0
        self.declared = 0
        self.scores: list[float] = []
        self.reasons: list[str] = []

    def add(self, document: dict[str, Any]) -> None:
        aggregates = document.get("aggregates") or {}
        self.ran += int(aggregates.get("casesTotal") or 0)
        self.scores.append(float(aggregates.get("overallScore") or 0.0))

    def pass_one(self) -> None:
        self.passed += 1

    def declare_one(self) -> None:
        self.declared += 1

    def stopped(self, reason: Any) -> None:
        """Why a document says the sweep stopped early, once per distinct reason."""
        said = str(reason)
        if said not in self.reasons:
            self.reasons.append(said)

    @property
    def summary(self) -> str:
        mean = sum(self.scores) / len(self.scores) if self.scores else 0.0
        line = (
            f"{self.found} found, {self.picked} picked, {self.ran} ran, "
            f"{self.passed} passed, {self.declared} declared unrunnable, "
            f"overall score {mean:.2f}"
        )
        if self.reasons:
            line += f", stopped early: {'; '.join(self.reasons)}"
        return line
