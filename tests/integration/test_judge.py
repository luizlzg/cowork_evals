"""The judge against the real `claude -p`. Six short calls, no CoWork session.

It proves what a recorded reply document cannot: that the composed text reaches the model
on stdin, and that the reply parses. Deselected by default; `live` because it spends. It
costs no ceiling entry, because nothing here submits to CoWork. See ../README.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cowork_evals.cases import Grader
from cowork_evals.judge import grade, resolve_model

RUBRIC = "PASS if the material is exactly the word PONG. FAIL for anything else."


def rubric_grader() -> Grader:
    return Grader(
        name="is-pong",
        type="llm",
        weight=1,
        config={"focus": "last_message"},
        markdown=RUBRIC,
        path=Path("is-pong.md"),
    )


def answering(text: str) -> dict[str, Any]:
    """The one field an `llm` grader on `last_message` reads."""
    return {"final_text": text, "turns": [], "tool_calls": [], "outputs": [], "session_dir": ""}


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.timeout(600)
def test_the_judge_passes_a_string_that_satisfies_the_rubric(tmp_path: Path) -> None:
    judged = grade(rubric_grader(), answering("PONG"), tmp_path, model=resolve_model())
    assert judged.result.skipped is False
    assert judged.result.judge_votes is not None, judged.result.explanation
    assert judged.result.passed is True, judged.result.explanation
    assert judged.result.explanation.startswith("judge votes: ")
    assert judged.result.evidence == "PONG"
    assert judged.cost_usd >= 0.0


@pytest.mark.integration
@pytest.mark.live
@pytest.mark.timeout(600)
def test_the_judge_fails_a_string_that_does_not(tmp_path: Path) -> None:
    judged = grade(
        rubric_grader(),
        answering("The kernel is 6.8.0-136-generic."),
        tmp_path,
        model=resolve_model(),
    )
    assert judged.result.judge_votes is not None, judged.result.explanation
    assert judged.result.passed is False, judged.result.explanation
