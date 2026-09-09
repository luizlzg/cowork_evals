"""The judge behind the `llm` and `baseline` graders: `claude -p`, three votes, majority.

The rubric and the material go to the model as one text on stdin, three times, and the
grader passes on two `PASS` votes. There is no SDK and no second credential route: the
signed-in `claude` on `PATH` is the one route, and `docs/cli.md` makes it part of the
`--cowork` preflight.

A judged grader never gates, which is the gate table in
[docs/running_evals.md](../../docs/running_evals.md), so nothing here raises. A file the
judge cannot be shown is a failed grader naming it, except an image, which is a grader skip:
the harness shows the judge the image, and one text call cannot.

`CLAUDE_CODE_WALNUT_SPIRE` is not exported here. It gates `claude plugin eval`, and this is
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

# Three votes, and a majority of them. docs/eval_format.md.
VOTES = 3
MAJORITY = 2

# What the judge is shown, and what is recorded of it. The first is what the harness shows
# a judge; the second is what a result document keeps as `evidence`.
MATERIAL_LIMIT = 100_000
EVIDENCE_LIMIT = 2_000
ELISION = "\n...\n"

# The two words a vote is, and what a reply that is neither is called.
PASS_WORD = "PASS"
FAIL_WORD = "FAIL"
LOST_WORD = "LOST"

# The composed text. The rubric first, the material fenced, the instruction last.
MATERIAL_OPEN = "--- MATERIAL ---"
MATERIAL_CLOSE = "--- END MATERIAL ---"
INSTRUCTION = f"Answer with exactly one word: {PASS_WORD} or {FAIL_WORD}."

# A baseline grader shows the judge two trajectories, and says which is which.
BASELINE_HEADING = "BASELINE TRAJECTORY:"
NEW_HEADING = "NEW TRAJECTORY:"

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
    """One vote, read from one `claude -p --output-format json` document."""

    vote: bool | None = None
    cost_usd: float = 0.0
    error: str | None = None

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


def judge_argv(model: str) -> list[str]:
    """One vote's command line. The composed text goes on stdin, never in the argument list.

    `--strict-mcp-config` keeps the developer's own MCP servers out of a text vote.
    """
    return [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--model",
        model,
        "--strict-mcp-config",
    ]


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
    """One vote and its spend, from one `--output-format json` document.

    A reply that is neither word is a lost vote, and a lost vote is not a `PASS`.
    """
    try:
        payload = json.loads(stdout)
    except ValueError:
        return Reply(error="the judge printed no JSON document")
    if not isinstance(payload, dict):
        return Reply(error="the judge printed no JSON document")
    cost = payload.get("total_cost_usd")
    spent = float(cost) if isinstance(cost, int | float) else 0.0
    answer = payload.get("result")
    if not isinstance(answer, str):
        return Reply(cost_usd=spent, error="the judge document carries no result")
    word = answer.strip().upper()
    if word == PASS_WORD:
        return Reply(vote=True, cost_usd=spent)
    if word == FAIL_WORD:
        return Reply(vote=False, cost_usd=spent)
    return Reply(cost_usd=spent, error=f"the judge answered neither word: {answer.strip()[:80]!r}")


def tally(grader: Grader, replies: list[Reply], evidence: str) -> Judged:
    """The verdict over the votes cast. Every reply's spend counts, lost or not."""
    cost = sum(reply.cost_usd for reply in replies)
    votes = [reply.vote for reply in replies]
    words = " ".join(reply.word for reply in replies)
    if all(vote is None for vote in votes):
        reasons = sorted({reply.error for reply in replies if reply.error})
        return Judged(failed(grader, f"the judge could not be asked: {'; '.join(reasons)}"), cost)
    return Judged(
        GraderResult(
            name=grader.name,
            passed=sum(1 for vote in votes if vote) >= MAJORITY,
            weight=grader.weight,
            explanation=f"judge votes: {words}",
            judge_votes=tuple(bool(vote) for vote in votes),
            evidence=truncate(evidence, EVIDENCE_LIMIT),
        ),
        cost,
    )


def grade(grader: Grader, document: dict[str, Any], case_dir: Path | str, *, model: str) -> Judged:
    """One judged grader: compose once, vote three times, count."""
    shown = material(grader, document, Path(case_dir))
    if shown.skip_reason is not None:
        return Judged(skipped(grader, shown.skip_reason))
    if shown.error is not None:
        return Judged(failed(grader, shown.error))

    text = compose(criteria(grader), shown.text)
    replies = [_vote(model, text) for _ in range(VOTES)]
    return tally(grader, replies, shown.text)


def _vote(model: str, text: str) -> Reply:
    """One `claude -p` call. A process that will not run is a lost vote, never a raise."""
    try:
        completed = subprocess.run(
            judge_argv(model), input=text, capture_output=True, text=True, check=False
        )
    except OSError as error:
        return Reply(error=f"claude could not be run: {error}")
    if completed.returncode != 0:
        return Reply(error=f"claude exited {completed.returncode}")
    return read_reply(completed.stdout)
