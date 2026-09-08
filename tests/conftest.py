"""What both tiers share: the result document contract from docs/cowork_driver.md."""

from __future__ import annotations

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
