"""The four structural graders, over one session document.

One `Grader` and one session document in, one `GraderResult` out. Nothing here submits
anything, so a grader re-runs over a stored session document for free.

The semantics are the grader table in
[docs/claude_code/plugin_eval_reference.md](../../docs/claude_code/plugin_eval_reference.md),
and matching them exactly is what makes a case portable between backends. Where this
backend diverges, [docs/cowork_driver.md](../../docs/cowork_driver.md) records it.

No failure here raises. A pattern that will not compile, a file that will not read and a
grader type nothing knows are each a failed grader carrying the reason.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any

from .cases import Grader

# The grader types this module answers for. `llm` and `baseline` are judge.py's.
STRUCTURAL = ("regex", "tool_used", "tool_order", "file_exists")

# The session directory's produced-file directory. `outputs` in the session document is
# relative to the session directory, so every entry carries this prefix. It is stripped
# once, here, and every grader that names a produced file names it relative to this
# directory. That is what makes `path: report.md` mean here what it means under the
# harness, where the created-file list is relative to the workspace.
OUTPUTS = "outputs"

# The values a `target` or a `focus` takes. docs/eval_format.md.
LAST_MESSAGE = "last_message"
TRACE = "trace"
FILES = "files"
FILE_SOURCE = "file"

# `match` on a regex grader.
CONTAINS = "contains"
NOT_CONTAINS = "not_contains"
COUNT_PREFIX = "count:"

# The JavaScript RegExp flags that have a Python equivalent. `d`, `g` and `y` have none and
# change nothing a grader reads, and `u` and `v` only turn off the ASCII default below.
FLAG_MAP = {"i": re.I, "m": re.M, "s": re.S}
UNICODE_FLAGS = "uv"


@dataclass(frozen=True, slots=True)
class GraderResult:
    """One grader's verdict. It is what a run's `graders[]` entry is built from.

    `withOnly` is not a field: it is always false here, because `ablation` is `none` and
    nothing is dropped for an arm. `scored` is `not skipped`, which widens the reference's
    `scored` = `not withOnly` to the one other exclusion this backend has.
    """

    name: str
    passed: bool
    weight: int | float
    explanation: str
    judge_votes: tuple[bool, ...] | None = None
    evidence: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Target:
    """What a grader reads: the text, or the reason there is none."""

    text: str = ""
    error: str | None = None


def skipped(grader: Grader, reason: str) -> GraderResult:
    """A grader that was not asked. It is excluded from the run's score."""
    return GraderResult(
        name=grader.name,
        passed=False,
        weight=grader.weight,
        explanation=reason,
        skipped=True,
        skip_reason=reason,
    )


def failed(grader: Grader, explanation: str) -> GraderResult:
    return GraderResult(
        name=grader.name, passed=False, weight=grader.weight, explanation=explanation
    )


def grade(grader: Grader, document: dict[str, Any]) -> GraderResult:
    """One structural grader. An unknown type is a failed grader naming it."""
    match grader.type:
        case "regex":
            return _regex(grader, document)
        case "tool_used":
            return _tool_used(grader, document)
        case "tool_order":
            return _tool_order(grader, document)
        case "file_exists":
            return _file_exists(grader, document)
        case _:
            return failed(grader, f"unknown grader type: {grader.type or '(none)'}")


# The targets.


def created(document: dict[str, Any]) -> list[str]:
    """The produced files, relative to `outputs/`. The prefix is stripped exactly here."""
    prefix = f"{OUTPUTS}/"
    entries = document.get("outputs") or []
    return [entry[len(prefix) :] if entry.startswith(prefix) else entry for entry in entries]


def resolve_target(document: dict[str, Any], spec: Any) -> Target:
    """What a `target` or a `focus` names, as text.

    It is text every time: a regex and a judge both read text, and the reference makes
    `files` newline-separated. `file_exists` is the one grader that does not come through
    here, because it reads the stripped list rather than a rendering of it.
    """
    if spec is None or spec == LAST_MESSAGE:
        return Target(text=document.get("final_text") or "")
    if spec == TRACE:
        return Target(text=_trace(document))
    if spec == FILES:
        return Target(text="\n".join(created(document)))
    if isinstance(spec, dict) and spec.get("source") == FILE_SOURCE:
        return _produced_file(document, spec.get("path"))
    return Target(error=f"unknown target: {spec!r}")


def _trace(document: dict[str, Any]) -> str:
    """The session as JSON, one object per line: every turn, then every tool call.

    This rendering is this backend's, not the harness's `trace.jsonl`, so a regex grader
    on `target: trace` is not portable between backends. docs/cowork_driver.md.
    """
    entries = [*(document.get("turns") or []), *(document.get("tool_calls") or [])]
    return "\n".join(json.dumps(entry) for entry in entries)


def produced_file(document: dict[str, Any], path: Any) -> tuple[Path | None, str | None]:
    """Where a produced file is on the host, or the reason it cannot be read from here.

    `outputs/` is the workspace on this backend, and the reference confines a file target
    to the workspace, so a path resolving outside it is refused rather than read. This
    resolves the path; `resolve_target` renders the contents and `judge.py` reads the bytes.
    """
    if not isinstance(path, str) or not path:
        return None, "a file target needs a path"
    root = (Path(document.get("session_dir", "")) / OUTPUTS).resolve()
    named = (root / path).resolve()
    if not named.is_relative_to(root):
        return None, f"{path} resolves outside {OUTPUTS}/"
    return named, None


def _produced_file(document: dict[str, Any], path: Any) -> Target:
    named, error = produced_file(document, path)
    if named is None:
        return Target(error=error)
    try:
        return Target(text=named.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return Target(error=f"{path} is unreadable: {error}")


# The patterns.


def compile_pattern(pattern: Any, flags: Any = "") -> re.Pattern[str]:
    """A JavaScript RegExp source, compiled with `re`.

    `re.ASCII` is what makes `\\d` and `\\w` ASCII-only as they are in JavaScript, so it is
    on unless the flags ask for Unicode. Every pattern in the format compiles through this
    one function, `input_match` on `tool_used` and `tool_order` included. The divergence
    between the two engines is docs/cowork_driver.md.
    """
    written = flags if isinstance(flags, str) else ""
    compiled = re.ASCII if not set(written) & set(UNICODE_FLAGS) else 0
    for letter, flag in FLAG_MAP.items():
        if letter in written:
            compiled |= flag
    return re.compile(str(pattern), compiled)


# The four graders.


def _regex(grader: Grader, document: dict[str, Any]) -> GraderResult:
    pattern = grader.config.get("pattern")
    if pattern is None:
        return failed(grader, "regex grader has no pattern")
    try:
        compiled = compile_pattern(pattern, grader.config.get("flags", ""))
    except re.error as error:
        return failed(grader, f"pattern does not compile: {error}")

    target = resolve_target(document, grader.config.get("target"))
    if target.error is not None:
        return failed(grader, target.error)

    hits = len(compiled.findall(target.text))
    match = grader.config.get("match", CONTAINS)
    if match == NOT_CONTAINS:
        return _verdict(grader, hits == 0, f"no match for {pattern}", f"matched {pattern}")
    if isinstance(match, str) and match.startswith(COUNT_PREFIX):
        wanted = match[len(COUNT_PREFIX) :]
        if not wanted.isdigit():
            return failed(grader, f"unreadable match: {match}")
        expected = int(wanted)
        return GraderResult(
            name=grader.name,
            passed=hits == expected,
            weight=grader.weight,
            explanation=f"matched {pattern} {hits}x (expected exactly {expected})",
        )
    if match != CONTAINS:
        return failed(grader, f"unreadable match: {match}")
    return _verdict(grader, hits > 0, f"matched {pattern}", f"no match for {pattern}")


def _tool_used(grader: Grader, document: dict[str, Any]) -> GraderResult:
    tool = grader.config.get("tool")
    if not isinstance(tool, str):
        return failed(grader, "tool_used grader has no tool")
    try:
        calls = _matching_calls(document, tool, grader.config.get("input_match"))
    except re.error as error:
        return failed(grader, f"input_match does not compile: {error}")

    low = grader.config.get("min", 1)
    high = grader.config.get("max")
    count = len(calls)
    within = count >= low and (high is None or count <= high)
    return GraderResult(
        name=grader.name,
        passed=within,
        weight=grader.weight,
        explanation=f"{tool} called {count}x ({_expected(low, high)})",
    )


def _tool_order(grader: Grader, document: dict[str, Any]) -> GraderResult:
    """`before` and `after`, each a tool name or `{tool, input_match}`.

    It reads `tool_calls` and not `tool_names`, because of the object form: a name alone
    cannot carry an `input_match`.
    """
    try:
        first = {key: _first_index(document, grader.config.get(key)) for key in ("before", "after")}
    except re.error as error:
        return failed(grader, f"input_match does not compile: {error}")

    names = {key: _spec_name(grader.config.get(key)) for key in ("before", "after")}
    for key in ("before", "after"):
        if first[key] is None:
            return failed(grader, f"{names[key]} was never called")
    passed = first["before"] < first["after"]
    return _verdict(
        grader,
        passed,
        f"{names['before']} preceded {names['after']}",
        f"{names['before']} did not precede {names['after']}",
    )


def _file_exists(grader: Grader, document: dict[str, Any]) -> GraderResult:
    """`path` as a glob over the produced files, with the harness's glob semantics.

    `PurePath.full_match` is `**/` at any depth and `*` within a segment, which is what the
    reference defines.
    """
    path = grader.config.get("path")
    if not isinstance(path, str) or not path:
        return failed(grader, "file_exists grader has no path")
    wants = grader.config.get("exists", True)
    matched = next((entry for entry in created(document) if PurePath(entry).full_match(path)), None)
    hit = f"created {matched}"
    miss = f"no created file matches {path}"
    if wants:
        return _verdict(grader, matched is not None, hit, miss)
    return _verdict(grader, matched is None, miss, hit)


# What the four share.


def _verdict(grader: Grader, passed: bool, when_passed: str, when_failed: str) -> GraderResult:
    """One result. Both explanations say what was found, never whether the grader passed.

    A `not_contains` grader that passes and a `contains` grader that fails both found
    nothing, so both read `no match for ...`.
    """
    return GraderResult(
        name=grader.name,
        passed=passed,
        weight=grader.weight,
        explanation=when_passed if passed else when_failed,
    )


def _matching_calls(document: dict[str, Any], tool: str, input_match: Any) -> list[int]:
    """The index of every call of `tool` whose JSON-encoded input matches, in call order."""
    compiled = None if input_match is None else compile_pattern(input_match)
    found = []
    for index, call in enumerate(document.get("tool_calls") or []):
        if call.get("name") != tool:
            continue
        if compiled is not None and not compiled.search(json.dumps(call.get("input"))):
            continue
        found.append(index)
    return found


def _first_index(document: dict[str, Any], spec: Any) -> int | None:
    """The first call matching a `tool_order` end, as an index into `tool_calls`."""
    if isinstance(spec, dict):
        tool = spec.get("tool")
        input_match = spec.get("input_match")
    else:
        tool, input_match = spec, None
    if not isinstance(tool, str):
        return None
    calls = _matching_calls(document, tool, input_match)
    return calls[0] if calls else None


def _spec_name(spec: Any) -> str:
    if isinstance(spec, dict):
        return str(spec.get("tool"))
    return str(spec)


def _expected(low: Any, high: Any) -> str:
    if high is None:
        return f"expected {low} or more"
    if low == high:
        return f"expected exactly {low}"
    return f"expected {low} to {high}"
