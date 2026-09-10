"""What one harness run left behind, lifted out of its sandbox and into the log directory.

`claude plugin eval --keep-temp` keeps each run's sandbox under the harness's `TMPDIR`, and
the container backend points that at the run's log mount, so the sandbox lands on the host
rather than inside a container started with `--rm`. This module reads what is there and keeps
the part worth keeping. docs/running_evals.md.

The split against [logs.py](logs.py): that module owns every path an invocation writes and is
the only thing that deletes one, this module owns what is copied out of a harness sandbox into
one of them. The sandbox layout is the harness's, which is why this sits beside
[harness.py](harness.py) and not inside a backend.

Nothing here raises. A sandbox that is not there, a trace that will not read and a document
that will not parse are each a warning line the caller prints, because a collection problem is
not a failed run. Nothing here prints, and nothing here decides pass or fail.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from . import logs, results
from .harness import RESULT_NAME

# The harness's `TMPDIR` inside the log directory, and so the parent of every kept sandbox.
# Short, because a socket path inside it is bounded. It is removed once collection is done,
# so nothing under this name survives an invocation.
SANDBOX_DIR = "tmp"

# What one kept sandbox holds, from docs/claude_code/plugin_eval_reference.md. `home/` and
# `tmp/` are moved under `sealed/` when the plugin under test wrote to either, and stay where
# they are when it wrote to neither, so the workspace is looked for under both names.
SANDBOX_OUT = "out"
SANDBOX_TRACE = "trace.jsonl"
SANDBOX_SEALED = "sealed"
SANDBOX_CWD = Path("home") / "cwd"

# What this module writes, one directory per run. docs/running_evals.md.
TRACES_DIR = "traces"
RUN_PREFIX = "run-"
TRACE_NAME = "trace.jsonl"
LAST_MESSAGE_NAME = "last_message.txt"
WORKSPACE_NAME = "workspace"

# The arm every backend runs. There is no baseline arm here, as in [gate.py](gate.py).
ARM = "with"


def sandbox_root(output_dir: Path | str) -> Path:
    """Where the harness puts its sandboxes when this run is keeping them.

    The container backend creates this before the run and passes the container-side name of
    it as `TMPDIR`; `collect` empties it afterwards.
    """
    return Path(output_dir) / SANDBOX_DIR


def run_dir(output_dir: Path | str, case: str, index: int, *, occurrence: int = 1) -> Path:
    """`<plugin log dir>/traces/<case>/run-<n>`, the directory one run's artefacts go in.

    `index` is 1-based, and is the same number the gate prints as `run N`, so a failure line
    and a directory name name the same run.

    Nothing makes a case name unique inside a plugin: two skills may each hold a case named
    `hello`. `occurrence` is which of them this is, and the second gets `-2`, exactly as
    `logs.plugin_dir` suffixes the second plugin of a name. Without it the second case's runs
    would land on the first's, and the gate would name a directory holding the wrong run.
    """
    name = logs.slug(case)
    if occurrence > 1:
        name = f"{name}-{occurrence}"
    return Path(output_dir) / TRACES_DIR / name / f"{RUN_PREFIX}{index}"


def collect(output_dir: Path | str) -> list[str]:
    """Keep each run's trace, then remove the sandboxes. Returns the warnings to print.

    Every run keeps the same three artefacts, whether it passed or failed: its trace, its
    final assistant message and its workspace. A passing run is what a failing one is read
    against, so keeping less for one than for the other would drop half of every comparison.
    docs/running_evals.md.

    `tracePath` in the result document is rewritten to the host path of the trace this
    kept, so the one field that named the trace still names it and the gate can print it.

    An empty list means there was nothing to collect or everything was collected.
    """
    output_dir = Path(output_dir)
    root = sandbox_root(output_dir)
    if not root.is_dir():
        return []

    warnings: list[str] = []
    document, unreadable = _document(output_dir)
    if unreadable is not None:
        warnings.append(unreadable)
    else:
        warnings += _each_run(output_dir, root, document)
        warnings += _rewrite(output_dir, document)
    warnings += _remove(root)
    return warnings


def last_message(trace: Path | str) -> str | None:
    """The run's final assistant message, as a `target: last_message` grader read it.

    The trace's `result` record carries it verbatim, which is why that record is preferred.
    A run that ended before one was written falls back to the last assistant text block, and
    a run with neither has no final message at all.
    """
    final = None
    fallback = None
    for record in _records(trace):
        kind = record.get("type")
        if kind == "result" and isinstance(record.get("result"), str):
            final = record["result"]
        elif kind == "assistant":
            text = _assistant_text(record)
            if text:
                fallback = text
    return final if final is not None else fallback


# One run.


def _each_run(output_dir: Path, root: Path, document: dict[str, Any]) -> list[str]:
    """Every run of every case, in the order the document lists them.

    `seen` counts the cases carrying each name, which is what `run_dir` suffixes on.
    """
    warnings = []
    seen: dict[str, int] = {}
    for case in document.get("cases") or []:
        if not isinstance(case, dict):
            continue
        name = str(case.get("name"))
        seen[name] = seen.get(name, 0) + 1
        for index, run in enumerate(case.get("arms", {}).get(ARM) or [], start=1):
            if isinstance(run, dict):
                warnings += _one_run(output_dir, root, name, index, run, seen[name])
    return warnings


def _one_run(
    output_dir: Path, root: Path, case: str, index: int, run: dict[str, Any], occurrence: int
) -> list[str]:
    """One run's artefacts, and `tracePath` pointed at where the trace now is."""
    where = f"{case}: run {index}"
    sandbox = _sandbox(root, run.get("tracePath"))
    if sandbox is None:
        return [f"{where}: tracePath names no kept sandbox: {run.get('tracePath')!r}"]
    if not sandbox.is_dir():
        return [f"{where}: {sandbox} was not kept, so there is no trace to collect"]

    logs.unseal(sandbox)
    destination = run_dir(output_dir, case, index, occurrence=occurrence)
    try:
        destination.mkdir(parents=True, exist_ok=True)
        trace = _keep_trace(sandbox, destination)
    except OSError as error:
        return [f"{where}: the trace could not be collected: {error}"]

    run["tracePath"] = str(trace)
    return _keep_last_message(trace, destination, where) + _keep_workspace(
        sandbox, destination, where
    )


def _sandbox(root: Path, trace_path: Any) -> Path | None:
    """The kept sandbox one run's `tracePath` names, on the host.

    The document's path is the container's, `<TMPDIR>/claude-eval-XXXXXX/out/trace.jsonl`,
    and only its sandbox component is read: the host half of the same mount is `root`.
    """
    if not isinstance(trace_path, str) or not trace_path:
        return None
    named = Path(trace_path)
    if named.name != SANDBOX_TRACE or named.parent.name != SANDBOX_OUT:
        return None
    return root / named.parent.parent.name


def _keep_trace(sandbox: Path, destination: Path) -> Path:
    """Move the trace out of the sandbox, and return where it now is."""
    trace = destination / TRACE_NAME
    shutil.move(str(sandbox / SANDBOX_OUT / SANDBOX_TRACE), str(trace))
    return trace


def _keep_last_message(trace: Path, destination: Path, where: str) -> list[str]:
    """Write the final assistant message beside the trace it was read from."""
    try:
        message = last_message(trace)
    except OSError as error:
        return [f"{where}: {trace} is unreadable: {error}"]
    if message is None:
        return [f"{where}: the trace carries no assistant message"]
    try:
        (destination / LAST_MESSAGE_NAME).write_text(message, encoding="utf-8")
    except OSError as error:
        return [f"{where}: the final message could not be written: {error}"]
    return []


def _keep_workspace(sandbox: Path, destination: Path, where: str) -> list[str]:
    """The run's workspace, which is the agent's working directory inside the sandbox."""
    for candidate in (sandbox / SANDBOX_SEALED / SANDBOX_CWD, sandbox / SANDBOX_CWD):
        if candidate.is_dir():
            try:
                shutil.move(str(candidate), str(destination / WORKSPACE_NAME))
            except OSError as error:
                return [f"{where}: the workspace could not be collected: {error}"]
            return []
    return [f"{where}: {sandbox} holds no {SANDBOX_CWD}, so there is no workspace to collect"]


# The document, and the sandboxes afterwards.


def _document(output_dir: Path) -> tuple[dict[str, Any], str | None]:
    """The result document, or the one line saying why the sandboxes cannot be mapped."""
    path = output_dir / RESULT_NAME
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return {}, f"{path}: no result document to map the kept sandboxes onto: {error}"
    if not isinstance(document, dict):
        return {}, f"{path}: expected a mapping at the top level"
    return document, None


def _rewrite(output_dir: Path, document: dict[str, Any]) -> list[str]:
    try:
        results.write(output_dir, document)
    except OSError as error:
        return [f"{output_dir / RESULT_NAME}: the collected paths could not be written: {error}"]
    return []


def _remove(root: Path) -> list[str]:
    try:
        logs.remove_tree(root)
    except OSError as error:
        return [f"{root}: the kept sandboxes could not be removed: {error}"]
    return []


# Reading a trace.


def _records(trace: Path | str) -> list[dict[str, Any]]:
    """Every JSON object in the trace, in order. An unparsable line is skipped.

    The harness writes one object per line and the file is read whole, so a line a
    truncated trace left half written is dropped rather than stopping the read.
    """
    text = Path(trace).read_text(encoding="utf-8", errors="replace")
    found = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            found.append(record)
    return found


def _assistant_text(record: dict[str, Any]) -> str:
    """The text blocks of one assistant record, joined. A thinking block is not text."""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
    )
