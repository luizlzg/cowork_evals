"""The deny-list linter refuses what docs/cowork_driver.md says it refuses."""

from __future__ import annotations

import pytest

from cowork_evals.prompt_lint import EXEMPTIONS, RULES, lint

# One prompt per rule, in the phrasing the rule is written for.
REFUSED = {
    "send": "Send an email to the whole team.",
    "create": "Create a calendar event for tomorrow morning.",
    "modify": "Update the quarterly spreadsheet with the new numbers.",
    "destroy": "Delete the old messages in the inbox.",
    "deploy": "Push the branch to origin.",
    "transact": "Approve the pending expense report.",
}

PASSES = [
    "Reply with exactly: PONG",
    "Read the last three emails in order to summarize them",
    "Write the summary to outputs/summary.md",
    "List every file under /sessions/ and describe it",
    "Copy the report into /tmp and read it back",
    "Report the value of TMPDIR",
    "Describe what the session can reach",
    "Summarize the last three emails",
    "",
]


@pytest.mark.parametrize("rule", sorted(RULES))
def test_one_refused_prompt_per_rule(rule: str) -> None:
    reason = lint(REFUSED[rule])
    assert reason is not None
    assert reason.startswith(f"rule {rule} ")
    assert REFUSED[rule].rstrip(".") in reason


@pytest.mark.parametrize("prompt", PASSES)
def test_a_read_only_prompt_passes(prompt: str) -> None:
    assert lint(prompt) is None


@pytest.mark.parametrize(
    "prompt",
    [f"Send the file listing to {exemption} and stop" for exemption in EXEMPTIONS],
)
def test_an_exempt_sentence_is_not_refused(prompt: str) -> None:
    assert lint(prompt) is None


def test_every_pattern_is_reachable() -> None:
    """Each pattern refuses a sentence built from it, so no pattern is dead."""
    for patterns in RULES.values():
        for pattern in patterns:
            sentence = pattern.replace("(POST|PUT|PATCH|DELETE)", "POST")
            assert lint(f"Please {sentence} the thing") is not None, pattern


def test_any_refused_sentence_refuses_the_prompt() -> None:
    prompt = "Read the inbox. Send a reply to the first message. Then stop."
    reason = lint(prompt)
    assert reason is not None
    assert reason.startswith("rule send ")


def test_a_newline_splits_sentences() -> None:
    assert lint("Read the inbox\nDelete the first message") is not None
    assert lint("Read the inbox\nSummarize it") is None


def test_reply_to_is_a_rule_and_reply_with_is_not() -> None:
    assert lint("Reply to the last email") is not None
    assert lint("Reply with the word PONG") is None


def test_order_a_is_a_rule_and_in_order_to_is_not() -> None:
    assert lint("Order a replacement keyboard") is not None
    assert lint("Read the notes in order to answer") is None


def test_a_listed_verb_is_matched_case_insensitively() -> None:
    assert lint("DELETE the message") is not None
