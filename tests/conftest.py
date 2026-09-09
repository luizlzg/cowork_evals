"""What both tiers share: the result document contract, and the working directory helper."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Iterator

import pytest

# Every key the result document carries, and no other.
DOCUMENT_KEYS = {
    "prompt",
    "prompt_sha256",
    "session_dir",
    "submitted_at",
    "collected_at",
    "transcript",
    "other_transcripts",
    "subagent_transcripts",
    "audit_prompt",
    "lifecycle",
    "turns",
    "tool_calls",
    "tool_names",
    "final_text",
    "outputs",
    "log_file",
}


@pytest.fixture
def document_keys() -> set[str]:
    return DOCUMENT_KEYS


@pytest.fixture
def working_directory() -> Callable[..., contextlib.AbstractContextManager[None]]:
    """Run a block in another working directory, and return to this one after.

    `cowork_evals.yaml` is resolved from the working directory, so a test of that rule
    moves there.
    """

    @contextlib.contextmanager
    def _chdir(path) -> Iterator[None]:
        previous = os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(previous)

    return _chdir
