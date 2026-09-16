"""The judge behind the `llm` and `baseline` graders: `claude -p`, a vote count, a majority.

The rubric and the material go to the model as one text on stdin, once per `eval.judge_votes`,
and the grader passes on a majority of `PASS` votes. There is no SDK and no second credential
route: the signed-in `claude` on `PATH` is the one route, and `docs/cli.md` makes it part of the
`--cowork` preflight.

A vote is read out of the CLI's own structured output rather than parsed out of prose.
`--json-schema` makes the reply carry a `verdict` and the `reasoning` behind it, so a judge asked
about something long can say what decided it and still answer in a field. A reply carrying no
structured output at all is read as the bare word it used to be, which is what a CLI too old for
the flag leaves.

A judged grader never decides the verdict, which is the pass and fail table in
docs/running_evals.md, so nothing here raises. A file the judge cannot be shown is a failed
grader naming it, except an image, which is a grader skip: the harness shows the judge the
image, and one text call cannot.

The check judge is the second caller, and it is this package's own rather than the harness's.
It has its own argument list and its own material rule: it is granted `Read`, `Glob` and
`Grep`, it runs in the run directory, and it is shown paths rather than text. Everything below
those two is shared, the vote count, the majority and the schema included. The `llm` grader is
untouched by any of it, because that grader matches the harness exactly and a check matches nothing
outside this package. docs/checks.md.

`CLAUDE_CODE_WALNUT_SPIRE` is not exported here. It enables `claude plugin eval`, and this is
`claude -p`.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cases import Grader
from .config import Config
from .grader import GraderResult, failed, produced_file, resolve_target, skipped

# How many votes a judged assertion casts, when nothing configures it. `eval.judge_votes` is the
# key, and `resolve_votes` is the one ladder it comes down. docs/running_evals.md.
VOTES = 3

# What the judge is shown, and what is recorded of it. The first is what the harness shows
# a judge; the second is what a result document keeps as `evidence`.
MATERIAL_LIMIT = 100_000
EVIDENCE_LIMIT = 2_000
ELISION = "\n...\n"

# The two words a vote is, and what a reply that is neither is called.
PASS_WORD = "PASS"
FAIL_WORD = "FAIL"
LOST_WORD = "LOST"

# The shape a vote comes back in, enforced by the CLI rather than parsed here. `--json-schema`
# makes `--output-format json` carry a `structured_output` object beside the `result` string, so
# a judge can reason at length and still answer in one field. Measured on CLI 2.1.273, with the
# check judge's tool grant and without it.
VERDICT_KEY = "verdict"
REASONING_KEY = "reasoning"
STRUCTURED_KEY = "structured_output"
VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        REASONING_KEY: {"type": "string"},
        VERDICT_KEY: {"type": "string", "enum": [PASS_WORD, FAIL_WORD]},
    },
    "required": [REASONING_KEY, VERDICT_KEY],
    "additionalProperties": False,
}

# How much of the winning reply's reasoning the explanation carries. The explanation is what a
# `FAIL` or `NOTE` line prints, and a line the length of `EVIDENCE_LIMIT` is not read.
REASONING_HEAD = 400
REASONING_HEADING = "JUDGE REASONING:"

# The composed text. The rubric first, the material fenced, the instruction last.
MATERIAL_OPEN = "--- MATERIAL ---"
MATERIAL_CLOSE = "--- END MATERIAL ---"
INSTRUCTION = (
    f"Say what in the material decided it, then answer {PASS_WORD} or {FAIL_WORD}. "
    f"The schema carries both: the reason in {REASONING_KEY!r}, the answer in {VERDICT_KEY!r}."
)

# A baseline grader shows the judge two trajectories, and says which is which.
BASELINE_HEADING = "BASELINE TRAJECTORY:"
NEW_HEADING = "NEW TRAJECTORY:"

# The check judge's grant, and what it is shown. It reads files and never writes one, so the
# three read-only tools are the whole grant. docs/checks.md.
CHECK_TOOLS = ("Read", "Glob", "Grep")
FILES_OPEN = "--- FILES ---"
FILES_CLOSE = "--- END FILES ---"
CHECK_INSTRUCTION = (
    "Read each file named above. Take as many turns as the question needs. Then say what you "
    f"found that decided it, and answer {PASS_WORD} or {FAIL_WORD}. The schema carries both: the "
    f"reason in {REASONING_KEY!r}, the answer in {VERDICT_KEY!r}."
)

# Image magic, from the file's bytes and never from its name, as the harness detects it.
IMAGE_MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")
RIFF = b"RIFF"
WEBP = b"WEBP"


@dataclass(frozen=True, slots=True)
class Material:
    """What the judge is to be shown, or why it cannot be.

    `error` is a failed grader carrying the reason. `skip_reason` is a grader skip, which
    is excluded from the run's score instead.
    """

    text: str = ""
    error: str | None = None
    skip_reason: str | None = None


@dataclass(frozen=True, slots=True)
class Reply:
    """One vote, read from one `claude -p --output-format json` document.

    `reasoning` is what the judge said decided it. It is empty on a reply that carried no
    `structured_output`, which is the older shape `read_reply` still accepts.
    """

    vote: bool | None = None
    cost_usd: float = 0.0
    error: str | None = None
    reasoning: str = ""

    @property
    def word(self) -> str:
        if self.vote is None:
            return LOST_WORD
        return PASS_WORD if self.vote else FAIL_WORD


@dataclass(frozen=True, slots=True)
class Judged:
    """One judged grader's result, and what asking cost."""

    result: GraderResult
    cost_usd: float = 0.0


def resolve_model(judge_model: str | None = None, config: Config | None = None) -> str:
    """The caller's judge model where one was given, and `eval.judge_model` otherwise."""
    if judge_model is not None:
        return judge_model
    return (config if config is not None else Config.load()).eval.judge_model


def resolve_votes(votes: int | None = None, config: Config | None = None) -> int:
    """The caller's vote count where one was given, and `eval.judge_votes` otherwise."""
    if votes is not None:
        return votes
    return (config if config is not None else Config.load()).eval.judge_votes


def majority(votes: int) -> int:
    """How many passes carry a verdict. One vote needs one, and three need two."""
    return votes // 2 + 1


def judge_argv(model: str) -> list[str]:
    """One vote's command line. The composed text goes on stdin, never in the argument list.

    `--strict-mcp-config` keeps the developer's own MCP servers out of a text vote.

    `--json-schema` is what lets a judge reason and still answer in a field this reads, so it is
    here and not in `check_argv`: one flag serves the check judge and the judged graders both.
    """
    return [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--model",
        model,
        "--strict-mcp-config",
        "--json-schema",
        json.dumps(VERDICT_SCHEMA),
    ]


def check_argv(model: str, add_dirs: tuple[str, ...] = ()) -> list[str]:
    """The check judge's command line: the judge's own, plus a grant and the paths it needs.

    `--allowedTools Read,Glob,Grep` alone lets a non-interactive judge read a file: on CLI
    2.1.270 a `claude -p` granted exactly these three read a file in its working directory and
    answered on what it said, with no permission mode and no cap. So neither is written here:
    a cap is a restriction nobody asked for, and the CLI's own default binds the loop.

    `--add-dir` carries each path outside the working directory, which is the run directory.
    A path under it needs none. docs/checks.md.
    """
    argv = [*judge_argv(model), "--allowedTools", ",".join(CHECK_TOOLS)]
    for directory in add_dirs:
        argv += ["--add-dir", directory]
    return argv


def compose_paths(prompt: str, names: tuple[str, ...]) -> str:
    """The one text a check judge's vote is sent: the prompt, the paths, the instruction.

    The material is never inlined. A PDF, an image and a spreadsheet cannot be shown as text,
    and reading a file is what the judge's `Read` tool is for.
    """
    return "\n".join([prompt.strip(), "", FILES_OPEN, *names, FILES_CLOSE, "", CHECK_INSTRUCTION])


def criteria(grader: Grader) -> str:
    """The rubric: the `criteria:` key where one is written, and the body otherwise."""
    written = grader.config.get("criteria")
    if isinstance(written, str) and written.strip():
        return written
    return grader.markdown


def compose(rubric: str, material: str) -> str:
    """The one text every vote is sent, with the material truncated as the harness truncates it."""
    return "\n".join(
        [
            rubric.strip(),
            "",
            MATERIAL_OPEN,
            truncate(material, MATERIAL_LIMIT),
            MATERIAL_CLOSE,
            "",
            INSTRUCTION,
        ]
    )


def truncate(text: str, limit: int) -> str:
    """Head and tail kept, the middle elided. That is what the harness shows a judge."""
    if len(text) <= limit:
        return text
    head = limit // 2
    tail = limit - head
    return text[:head] + ELISION + text[-tail:]


def material(grader: Grader, document: dict[str, Any], case_dir: Path) -> Material:
    """What this grader's judge is shown.

    An `llm` grader reads `focus`; `target` on one is ignored, because the harness ignores
    it. A `baseline` grader reads `baseline_file` beside the case and shows both
    trajectories.
    """
    if grader.type == "baseline":
        return _baseline_material(grader, document, case_dir)

    focus = grader.config.get("focus")
    if isinstance(focus, dict) and focus.get("source") == "file":
        return _file_material(document, focus.get("path"))
    resolved = resolve_target(document, focus)
    if resolved.error is not None:
        return Material(error=resolved.error)
    return Material(text=resolved.text)


def _baseline_material(grader: Grader, document: dict[str, Any], case_dir: Path) -> Material:
    named = grader.config.get("baseline_file")
    if not isinstance(named, str) or not named:
        return Material(error="baseline grader has no baseline_file")
    root = Path(case_dir).resolve()
    path = (root / named).resolve()
    if not path.is_relative_to(root):
        return Material(error=f"{named} resolves outside the case directory")
    try:
        recorded = path.read_bytes()
    except OSError as error:
        return Material(error=f"{named} is unreadable: {error}")
    text = _as_text(recorded)
    if text is None:
        return Material(error=f"{named} is not UTF-8 text")
    trajectory = resolve_target(document, "trace")
    return Material(text="\n".join([BASELINE_HEADING, text, "", NEW_HEADING, trajectory.text]))


def _file_material(document: dict[str, Any], path: Any) -> Material:
    named, error = produced_file(document, path)
    if named is None:
        return Material(error=error)
    try:
        content = named.read_bytes()
    except OSError as error:
        return Material(error=f"{path} is unreadable: {error}")
    if _is_image(content):
        return Material(
            skip_reason=(
                f"{path} is an image, and the harness shows the judge the image itself, "
                "which one text call cannot"
            )
        )
    text = _as_text(content)
    if text is None:
        return Material(error=f"{path} is not UTF-8 text: render it to an image, or write UTF-8")
    return Material(text=text)


def _is_image(content: bytes) -> bool:
    """PNG, JPEG, GIF or WebP, from the bytes and never from the name."""
    if content.startswith(IMAGE_MAGIC):
        return True
    return content[:4] == RIFF and content[8:12] == WEBP


def _as_text(content: bytes) -> str | None:
    if b"\x00" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_reply(stdout: str) -> Reply:
    """One vote, its reasoning and its spend, from one `--output-format json` document.

    Two shapes, and one rule decides which is read: **a document carrying `structured_output` is
    read from it, and any other document is read from `result` as a bare word.** The first is what
    `--json-schema` produces, and it is the only shape that carries reasoning. The second is what a
    CLI too old for that flag leaves, and it still votes.

    A reply that is neither is a lost vote, and a lost vote is not a `PASS`.
    """
    try:
        payload = json.loads(stdout)
    except ValueError:
        return Reply(error="the judge printed no JSON document")
    if not isinstance(payload, dict):
        return Reply(error="the judge printed no JSON document")
    cost = payload.get("total_cost_usd")
    spent = float(cost) if isinstance(cost, int | float) else 0.0

    structured = payload.get(STRUCTURED_KEY)
    if isinstance(structured, dict):
        return _read_structured(structured, spent)

    answer = payload.get("result")
    if not isinstance(answer, str):
        return Reply(cost_usd=spent, error="the judge document carries no result")
    word = answer.strip().upper()
    if word == PASS_WORD:
        return Reply(vote=True, cost_usd=spent)
    if word == FAIL_WORD:
        return Reply(vote=False, cost_usd=spent)
    return Reply(cost_usd=spent, error=f"the judge answered neither word: {answer.strip()[:80]!r}")


def _read_structured(structured: dict[str, Any], spent: float) -> Reply:
    """One vote out of a `structured_output` object. A verdict outside the schema is a lost vote."""
    verdict = structured.get(VERDICT_KEY)
    reasoning = structured.get(REASONING_KEY)
    said = reasoning.strip() if isinstance(reasoning, str) else ""
    word = verdict.strip().upper() if isinstance(verdict, str) else ""
    if word == PASS_WORD:
        return Reply(vote=True, cost_usd=spent, reasoning=said)
    if word == FAIL_WORD:
        return Reply(vote=False, cost_usd=spent, reasoning=said)
    return Reply(
        cost_usd=spent,
        reasoning=said,
        error=f"the judge's {VERDICT_KEY} was neither word: {str(verdict)[:80]!r}",
    )


def tally(grader: Grader, replies: list[Reply], evidence: str) -> Judged:
    """The verdict over the votes cast, and what the winning side said. Every spend counts.

    The winning reply's reasoning is carried twice, at two lengths, because two readers want it
    differently. `explanation` is a `FAIL` or `NOTE` line and takes a head of it. `evidence` is the
    document's record and takes as much as `EVIDENCE_LIMIT` allows, after the material it already
    held: what the judge was shown and what it made of it are both worth keeping.
    """
    cost = sum(reply.cost_usd for reply in replies)
    votes = [reply.vote for reply in replies]
    words = " ".join(reply.word for reply in replies)
    if all(vote is None for vote in votes):
        reasons = sorted({reply.error for reply in replies if reply.error})
        return Judged(failed(grader, f"the judge could not be asked: {'; '.join(reasons)}"), cost)
    passed = sum(1 for vote in votes if vote) >= majority(len(replies))
    said = _winning_reasoning(replies, passed=passed)
    return Judged(
        GraderResult(
            name=grader.name,
            passed=passed,
            weight=grader.weight,
            explanation=f"judge votes: {words}" + (f". {said[:REASONING_HEAD]}" if said else ""),
            judge_votes=tuple(bool(vote) for vote in votes),
            evidence=truncate(_with_reasoning(evidence, said), EVIDENCE_LIMIT),
        ),
        cost,
    )


def _winning_reasoning(replies: list[Reply], *, passed: bool) -> str:
    """What a reply on the winning side said. A lost vote is on no side."""
    for reply in replies:
        if reply.vote is passed and reply.reasoning:
            return reply.reasoning
    return ""


def _with_reasoning(evidence: str, said: str) -> str:
    """The material the judge was shown, and under it what the judge made of it."""
    if not said:
        return evidence
    return "\n".join([evidence, "", REASONING_HEADING, said])


def grade(
    grader: Grader,
    document: dict[str, Any],
    case_dir: Path | str,
    *,
    model: str,
    votes: int | None = None,
) -> Judged:
    """One judged grader: compose once, vote as many times as configured, count."""
    shown = material(grader, document, Path(case_dir))
    if shown.skip_reason is not None:
        return Judged(skipped(grader, shown.skip_reason))
    if shown.error is not None:
        return Judged(failed(grader, shown.error))

    text = compose(criteria(grader), shown.text)
    replies = [_vote(model, text) for _ in range(resolve_votes(votes))]
    return tally(grader, replies, shown.text)


def _vote(model: str, text: str) -> Reply:
    return ask(judge_argv(model), text)


def ask(argv: list[str], text: str, cwd: Path | str | None = None) -> Reply:
    """One `claude -p` call. A process that will not run is a lost vote, never a raise.

    Public because the check judge casts its votes through it, with an argument list and a
    working directory of its own. A tool-using judge answers with the bare word, measured on
    CLI 2.1.270, so `read_reply` reads a check judge's reply exactly as it reads a grader's.
    """
    try:
        completed = subprocess.run(
            argv,
            input=text,
            capture_output=True,
            text=True,
            check=False,
            cwd=None if cwd is None else str(cwd),
        )
    except OSError as error:
        return Reply(error=f"claude could not be run: {error}")
    if completed.returncode != 0:
        return Reply(error=f"claude exited {completed.returncode}")
    return read_reply(completed.stdout)
