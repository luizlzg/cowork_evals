"""The CoWork driver: submit one prompt, wait for the run, collect what it produced.

The behaviour is [docs/cowork_driver.md](../../docs/cowork_driver.md) and the record shapes
are [docs/cowork_desktop.md](../../docs/cowork_desktop.md). Nothing here writes anywhere
under the CoWork profile.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import Config, CoWorkError, _override

# A session directory is exactly three levels below the sessions root and holds an
# audit.jsonl. docs/cowork_desktop.md.
SESSION_DEPTH = 3
AUDIT = "audit.jsonl"
TRANSCRIPTS = Path(".claude") / "projects" / "session"
OUTPUTS = "outputs"


class CoWork:
    """The driver. One instance holds one resolved configuration."""

    def __init__(
        self,
        config: Config | None = None,
        *,
        runner: Any = None,
        **overrides: Any,
    ) -> None:
        config = Config.load(**overrides) if config is None else _override(config, overrides)
        self._config = config
        self._runner = runner
        self._log_file: Path | None = None

    @classmethod
    def from_file(cls, path: Path | str, **overrides: Any) -> CoWork:
        """Build from a named configuration file rather than the working directory's."""
        return cls(Config.load(path, **overrides))

    @property
    def config(self) -> Config:
        return self._config

    # Reading. None of these fires anything, and none needs a profile except through
    # the configured sessions root.

    def sessions(self, root: Path | None = None) -> list[Path]:
        """Every session directory under a root, sorted."""
        base = Path(root) if root is not None else self._config.sessions_root
        if not base.is_dir():
            return []
        pattern = "/".join(["*"] * SESSION_DEPTH)
        return sorted(d for d in base.glob(pattern) if d.is_dir() and (d / AUDIT).is_file())

    def collect(self, session_dir: Path | str, *, prompt: str | None = None) -> dict[str, Any]:
        """Build the result document from one session directory already on disk."""
        directory = Path(session_dir)
        audit = _read_jsonl(directory / AUDIT)
        transcript, other, subagents = _transcripts(directory)
        records = _read_jsonl(transcript) if transcript is not None else []

        turns = _turns(records)
        final_text = _final_text(turns)
        if final_text is None:
            raise CoWorkError(8, f"{directory}: the run produced no assistant text", directory)

        audit_prompt = _audit_prompt(audit)
        submitted = prompt if prompt is not None else audit_prompt
        return {
            "prompt": submitted,
            "prompt_sha256": _digest(submitted),
            "session_dir": str(directory),
            "submitted_at": _submitted_at(audit),
            "collected_at": _now(),
            "transcript": None if transcript is None else str(transcript),
            "other_transcripts": [str(path) for path in other],
            "subagent_transcripts": [str(path) for path in subagents],
            "audit_prompt": audit_prompt,
            "lifecycle": _lifecycle(audit),
            "turns": turns,
            "tool_calls": _tool_calls(records),
            "tool_names": [call["name"] for call in _tool_calls(records)],
            "final_text": final_text,
            "outputs": _outputs(directory),
            "log_file": None if self._log_file is None else str(self._log_file),
        }


# Readers. Each takes what it reads, so a test drives it over a fixture directory.


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse a JSON Lines file, skipping an unparsable line.

    Both audit.jsonl and the transcript are appended while the run is live, so the last
    line can be partial.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _transcripts(session_dir: Path) -> tuple[Path | None, list[Path], list[Path]]:
    """The main transcript, the other top level ones, and the subagent sidechains.

    The main transcript is the newest top level file by modification time. A session
    directory with no transcript directory yet is tolerated.
    """
    root = session_dir / TRANSCRIPTS
    if not root.is_dir():
        return None, [], []
    top = sorted(path for path in root.glob("*.jsonl") if path.is_file())
    subagents = sorted(path for path in root.glob("*/subagents/*.jsonl") if path.is_file())
    if not top:
        return None, [], subagents
    main = max(top, key=lambda path: path.stat().st_mtime)
    return main, [path for path in top if path != main], subagents


def _content_blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    """The content of a transcript record, always as a list of blocks."""
    message = record.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def _text_of(record: dict[str, Any]) -> str:
    """The turn text of a record. A thinking block is not turn text."""
    parts = [
        block.get("text", "")
        for block in _content_blocks(record)
        if block.get("type") == "text" and isinstance(block.get("text"), str)
    ]
    return "\n".join(part for part in parts if part)


def _turns(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Role and text per turn. Only user and assistant records carry a message."""
    turns = []
    for record in records:
        if record.get("type") not in ("user", "assistant"):
            continue
        message = record.get("message")
        role = message.get("role") if isinstance(message, dict) else None
        text = _text_of(record)
        if not text:
            continue
        if not isinstance(role, str):
            role = str(record.get("type"))
        turns.append({"role": role, "text": text})
    return turns


def _final_text(turns: list[dict[str, str]]) -> str | None:
    for turn in reversed(turns):
        if turn["role"] == "assistant":
            return turn["text"]
    return None


def _tool_calls(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every tool_use, paired to its tool_result by tool_use_id.

    A result whose call is absent from this transcript belongs to a subagent and is
    dropped. Positional pairing is wrong: results arrive in later records, and parallel
    calls interleave.
    """
    calls: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        for block in _content_blocks(record):
            if block.get("type") != "tool_use":
                continue
            call = {
                "id": block.get("id"),
                "name": block.get("name"),
                "input": block.get("input"),
                "mcp_server": record.get("attributionMcpServer"),
                "mcp_tool": record.get("attributionMcpTool"),
                "timestamp": record.get("timestamp"),
                "result": None,
            }
            calls.append(call)
            if isinstance(block.get("id"), str):
                index[block["id"]] = call

    for record in records:
        for block in _content_blocks(record):
            if block.get("type") != "tool_result":
                continue
            call = index.get(block.get("tool_use_id"))
            if call is not None:
                call["result"] = block.get("content")
    return calls


def _lifecycle(audit: list[dict[str, Any]]) -> list[str]:
    return [
        record["state"]
        for record in audit
        if record.get("type") == "command_lifecycle" and isinstance(record.get("state"), str)
    ]


def _audit_prompt(audit: list[dict[str, Any]]) -> str | None:
    """The submitted prompt as the application recorded it, verbatim."""
    for record in audit:
        if record.get("type") != "user":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text = "\n".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
            if text:
                return text
    return None


def _submitted_at(audit: list[dict[str, Any]]) -> str | None:
    """When the prompt reached the application, from its first user record."""
    for record in audit:
        if record.get("type") == "user" and isinstance(record.get("timestamp"), str):
            return record["timestamp"]
    return None


def _outputs(session_dir: Path) -> list[str]:
    root = session_dir / OUTPUTS
    if not root.is_dir():
        return []
    return sorted(str(path.relative_to(session_dir)) for path in root.rglob("*") if path.is_file())


def _digest(prompt: str | None) -> str | None:
    if prompt is None:
        return None
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()
