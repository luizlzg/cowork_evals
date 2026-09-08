"""The deny-list prompt linter that protects a live CoWork account.

The rule it enforces, the patterns, the exemptions and the limits are in
[docs/cowork_driver.md](../../docs/cowork_driver.md). This module holds no policy of its
own, and there is no flag, argument or configuration key that disables it.
"""

from __future__ import annotations

import re

# Rule name to the phrasings a mutating prompt actually uses. docs/cowork_driver.md.
RULES: dict[str, tuple[str, ...]] = {
    "send": ("send", "reply to", "forward", "post to", "publish", "share", "notify", "invite"),
    "create": ("create", "add", "schedule", "book", "draft", "file a", "submit"),
    "modify": ("update", "edit", "rename", "move", "assign", "enable", "disable", "mark"),
    "destroy": (
        "delete",
        "remove",
        "cancel",
        "decline",
        "archive",
        "trash",
        "revoke",
        "unsubscribe",
    ),
    "deploy": (
        "install",
        "deploy",
        "commit",
        "push",
        "merge",
        "upload",
        "rm -",
        "mv ",
        "git push",
        r"curl -X (POST|PUT|PATCH|DELETE)",
    ),
    "transact": (
        "approve",
        "pay",
        "purchase",
        "order a",
        "place an order",
        "authorize",
        "sign",
    ),
}

# A sentence naming one of these targets a session-local path, and is not a mutation.
EXEMPTIONS: tuple[str, ...] = ("outputs/", "/sessions/", "/tmp", "TMPDIR", "the session")

_SENTENCE = re.compile(r"[.;?!\n]")


def _bounded(pattern: str) -> re.Pattern[str]:
    """Anchor a pattern on word boundaries, on whichever end carries a word character."""
    if pattern[0].isalnum():
        pattern = r"\b" + pattern
    if pattern[-1].isalnum() or pattern[-1] == ")":
        pattern = pattern + r"\b"
    return re.compile(pattern, re.IGNORECASE)


_COMPILED: dict[str, tuple[re.Pattern[str], ...]] = {
    rule: tuple(_bounded(pattern) for pattern in patterns) for rule, patterns in RULES.items()
}


def lint(prompt: str) -> str | None:
    """Return why the prompt is refused, or None when it passes.

    A prompt is refused when any of its sentences matches a rule and names no
    session-local target.
    """
    for sentence in _SENTENCE.split(prompt):
        sentence = sentence.strip()
        if not sentence:
            continue
        lowered = sentence.lower()
        if any(exemption.lower() in lowered for exemption in EXEMPTIONS):
            continue
        for rule, patterns in _COMPILED.items():
            for pattern in patterns:
                match = pattern.search(sentence)
                if match:
                    return f"rule {rule} matched {match.group(0)!r} in sentence {sentence!r}"
    return None
