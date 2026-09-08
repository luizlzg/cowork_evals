"""What both tiers share: the result document contract, and the environment helper."""

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
def environment() -> Callable[..., contextlib.AbstractContextManager[None]]:
    """Set the real process environment for a block, and restore it after.

    Not a stand-in. `env.py` reads the process environment, and this sets the one it
    reads. A name given None is removed for the block.
    """

    @contextlib.contextmanager
    def _set(**names: str | None) -> Iterator[None]:
        previous = {name: os.environ.get(name) for name in names}
        try:
            for name, value in names.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            yield
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    return _set


@pytest.fixture
def working_directory() -> Callable[..., contextlib.AbstractContextManager[None]]:
    """Run a block in another working directory, and return to this one after.

    `.env` is resolved from the working directory, so a test of that rule moves there.
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
