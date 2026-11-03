"""Probe how a CoWork session waits for the user, and which keys answer it. See the .md beside it.

A question (AskUserQuestion) or an approval box writes a `permission_request` record to
audit.jsonl and nothing else until it is answered. This probe submits one prompt through the
driver, logs every change in the session directory, and when a request stands presses the
scenario's key, behind the driver's frontmost check and without activating CoWork: activating
moves the keyboard to the composer, away from the box. It asks nothing while it runs, and one
question at the end.

None of the scenarios needs a plugin: the question tool and the folder box are CoWork's own.

It writes interaction_probe_<scenario>_<stamp>.log, one JSON object per line, with the user name,
home folder and computer name replaced. Text is cut to its first characters, and the content of
records other than user and assistant (for example a plugin's injected context) is not written.

    uv run python scripts/interaction_probe.py question [--key KEY] [--config cowork_evals.yaml]
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cowork_evals import CoWork, CoWorkError
from cowork_evals import cowork as driver

FOLDER_PROMPT = (
    "Connect my Downloads folder (~/Downloads) to this chat, then tell me how many files are at "
    "its top level. Do not open or change any file."
)
# Each scenario: the prompt, and the key pressed when its request stands.
SCENARIOS = {
    "question": (
        "Use the AskUserQuestion tool to ask me one question: do I prefer red or blue? Offer "
        "exactly two options, Red and Blue. After I answer, write only my answer to colour.txt "
        "in the outputs folder and reply with one sentence.",
        "1",
    ),
    "questions": (
        "Use the AskUserQuestion tool once, with two questions in that one call: do I prefer red "
        "or blue (options Red, Blue), and small or large (options Small, Large). After I answer, "
        "write my two answers to answers.txt in the outputs folder and reply with one sentence.",
        "1_each",
    ),
    # 1 ticks a multi-choice option and sends nothing; the second key is the send.
    "multiselect": (
        "Use the AskUserQuestion tool to ask me one question with multiSelect set to true: which "
        "colours do I like? Options Red, Blue, Green. After I answer, reply with only my answer.",
        "1_approve",
    ),
    "folder_allow": (FOLDER_PROMPT, "approve"),
    "folder_deny": (FOLDER_PROMPT, "esc"),
}

# A key, or a digit for each question then a key. `approve` is Cmd+Return on macOS and Ctrl+Enter
# on Windows: allow once on every approval box (on Windows the connector box's 2 is "allow for
# this task", so digits are not used to approve).
KEYS = ("esc", "enter", "approve", "1_each", "1_approve", "1_enter", *"123456789")
SYSTEM_EVENTS = 'tell application "System Events" to '
MAC_KEYS = {
    "esc": [SYSTEM_EVENTS + "key code 53"],
    "enter": [SYSTEM_EVENTS + "key code 36"],
    "approve": [
        SYSTEM_EVENTS + "key down command",
        "delay 0.1",
        SYSTEM_EVENTS + "key code 36",
        "delay 0.1",
        SYSTEM_EVENTS + "key up command",
    ],
}
VK_CONTROL, VK_RETURN, VK_ESCAPE, VK_DIGIT_0 = 0x11, 0x0D, 0x1B, 0x30
WIN_KEYS = {
    "esc": [(VK_ESCAPE, False), (VK_ESCAPE, True)],
    "enter": [(VK_RETURN, False), (VK_RETURN, True)],
    "approve": [(VK_CONTROL, False), (VK_RETURN, False), (VK_RETURN, True), (VK_CONTROL, True)],
}

RUN_SECONDS = 600.0
TEXT_CHARS = 200
# Record types whose text is the probe's own prompt and the model's reply. Every other record
# type is logged by its keys and sizes only.
TEXT_RECORDS = {"user", "assistant"}
PERMISSION_REQUEST, PERMISSION_RESPONSE = "permission_request", "permission_response"
PERMISSION_FIELDS = ("tool_name", "tool_input", "decision", "granted")
# How long a request stands before the first press, how long between presses while it still
# stands (a box can show before it takes a key), and how many presses in all. A digit is pressed
# once: a second 1 unticks a multi-choice option.
FIRST_SECONDS = 2.0
RETRY_SECONDS = 3.0
PRESSES = 4


class Log:
    """One flushed line per record, so a probe that stops halfway still helps."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = path.open("w", encoding="utf-8")
        values = {
            str(Path.home()): "~",
            getpass.getuser(): "<user>",
            socket.gethostname(): "<host>",
        }
        values |= {
            os.environ[n]: f"%{n}%" for n in ("LOCALAPPDATA", "APPDATA") if os.environ.get(n)
        }
        pairs = [(value, label) for value, label in values.items() if len(value) >= 3]
        self._replace = sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)

    def write(self, step: str, **fields: Any) -> None:
        # Milliseconds, so the order of a press and the records after it shows.
        stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        line = json.dumps({"t": stamp, "step": step, **fields}, ensure_ascii=False, default=str)
        for value, label in self._replace:
            for form in (value, value.replace("\\", "\\\\")):
                line = line.replace(form, label)
        self._file.write(line + "\n")
        self._file.flush()
        print(f"[{step}] {line[:160]}")

    def close(self) -> None:
        self._file.close()


def _cut(value: Any) -> Any:
    if isinstance(value, str):
        return (
            value if len(value) <= TEXT_CHARS else f"{value[:TEXT_CHARS]}... ({len(value)} chars)"
        )
    if isinstance(value, dict):
        return {key: _cut(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_cut(item) for item in value]
    return value


def _blocks(content: Any) -> list[dict[str, Any]]:
    """Each content block by type, with the fields that tell a pending tool call apart."""
    if isinstance(content, str):
        return [{"type": "text", "text": _cut(content)}]
    shown = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        entry: dict[str, Any] = {"type": kind}
        if kind == "text":
            entry["text"] = _cut(block.get("text", ""))
        elif kind == "tool_use":
            entry |= {
                "id": block.get("id"),
                "name": block.get("name"),
                "input": _cut(block.get("input")),
            }
        elif kind == "tool_result":
            entry |= {
                "tool_use_id": block.get("tool_use_id"),
                "is_error": block.get("is_error"),
                "content": _cut(block.get("content")),
            }
        else:
            entry["keys"] = sorted(block)
        shown.append(entry)
    return shown


def _shape(record: dict[str, Any]) -> dict[str, Any]:
    """A record as the log keeps it: every key name, and text only for user and assistant."""
    kind = record.get("type")
    shown: dict[str, Any] = {"type": kind, "keys": sorted(record)}
    for key in ("subtype", "state", "operation", "permissionMode", "stop_reason", "is_error"):
        if key in record:
            shown[key] = record[key]
    for key in PERMISSION_FIELDS:
        if key in record:
            shown[key] = _cut(record[key])
    message = record.get("message")
    if kind in TEXT_RECORDS and isinstance(message, dict):
        shown["role"] = message.get("role")
        shown["blocks"] = _blocks(message.get("content"))
    if "toolUseResult" in record:
        shown["toolUseResult"] = _cut(record["toolUseResult"])
    return shown


class Watcher:
    """New lines in every .jsonl under the session, and every file added or grown."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self._offsets: dict[str, int] = {}
        self._sizes: dict[str, int] = {}
        self.waiting: str | None = None
        self.waiting_input: dict[str, Any] = {}
        self.waiting_since = 0.0

    def poll(self, log: Log) -> None:
        # CoWork writes while this reads: a temporary file (.claude.json.tmp.<n>) is renamed and
        # a lock directory removed between the listing and the read. os.walk skips a directory
        # that is gone, a temporary file is not looked at, and a file gone by its stat is skipped.
        for directory, _, names in os.walk(self.session_dir):
            for name in sorted(names):
                if ".tmp." in name:
                    continue
                path = os.path.join(directory, name)
                try:
                    size = os.stat(path).st_size
                except OSError:
                    continue
                relative = Path(path).relative_to(self.session_dir).as_posix()
                if self._sizes.get(path) != size:
                    log.write("file", path=relative, size=size, new=path not in self._sizes)
                    self._sizes[path] = size
                if name.endswith(".jsonl"):
                    self._lines(path, relative, log)

    def _lines(self, path: str, relative: str, log: Log) -> None:
        try:
            with open(path, "rb") as handle:
                handle.seek(self._offsets.get(path, 0))
                data = handle.read()
        except OSError:
            return
        end = data.rfind(b"\n") + 1
        self._offsets[path] = self._offsets.get(path, 0) + end
        for raw in data[:end].splitlines():
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                log.write("unparsed", path=relative, length=len(raw))
                continue
            if isinstance(record, dict):
                self._track(record)
                log.write("record", path=relative, record=_shape(record))

    def _track(self, record: dict[str, Any]) -> None:
        """The permission request not yet answered."""
        if record.get("type") != "system":
            return
        if record.get("subtype") == PERMISSION_REQUEST:
            self.waiting = str(record.get("tool_name"))
            self.waiting_input = record.get("tool_input") or {}
            self.waiting_since = time.monotonic()
        elif record.get("subtype") == PERMISSION_RESPONSE:
            self.waiting = None


def _press_one(probe: CoWork, key: str) -> None:
    """One key, behind the frontmost check and with no activation. Code 9 types nothing."""
    probe._settle_front()
    probe._guard()
    if driver.WINDOWS:
        from cowork_evals import windows

        events = WIN_KEYS.get(key) or [
            (VK_DIGIT_0 + int(key), False),
            (VK_DIGIT_0 + int(key), True),
        ]
        probe._native(windows._send, events)
    else:
        lines = MAC_KEYS.get(key) or [f'{SYSTEM_EVENTS}keystroke "{key}"']
        probe._fire(["osascript", *(part for line in lines for part in ("-e", line))])


def _questions(request: dict[str, Any]) -> int:
    questions = request.get("questions")
    return len(questions) if isinstance(questions, list) and questions else 1


def _press(probe: CoWork, key: str, request: dict[str, Any], *, again: bool) -> str:
    """Press a scenario key. On a retry only its last key: a digit again would untick. Returns
    what was pressed."""
    if key in ("1_each", "1_approve", "1_enter"):
        last = {"1_each": None, "1_approve": "approve", "1_enter": "enter"}[key]
        if again:
            if last is not None:
                _press_one(probe, last)
            return last or ""
        for position in range(_questions(request)):
            if position:
                time.sleep(0.5)
            _press_one(probe, "1")
        if last is not None:
            time.sleep(0.5)
            _press_one(probe, last)
        return key
    _press_one(probe, key)
    return key


def _retries(key: str) -> bool:
    """Whether a key is pressed again while its request stands. A lone digit is not."""
    return not key.isdigit() and key != "1_each"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--key", choices=KEYS, help="the key to press instead of the scenario's")
    parser.add_argument(
        "--config", help="cowork_evals.yaml to read, default the working directory's"
    )
    args = parser.parse_args()
    prompt, key = SCENARIOS[args.scenario]
    key = args.key or key

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = Log(Path(f"interaction_probe_{args.scenario}_{stamp}.log").resolve())
    probe = CoWork.from_file(args.config) if args.config else CoWork()
    log.write(
        "start",
        scenario=args.scenario,
        platform=sys.platform,
        os=platform.platform(),
        python=platform.python_version(),
        prompt=prompt,
        key=key,
    )
    try:
        session_dir = probe.submit(prompt)
    except CoWorkError as error:
        log.write("submit_failed", code=error.code, message=str(error))
        log.close()
        return 1
    log.write("submitted", session=session_dir.name)

    watcher = Watcher(session_dir)
    deadline = time.monotonic() + RUN_SECONDS
    presses, last_press = 0, 0.0
    try:
        while time.monotonic() < deadline:
            watcher.poll(log)
            if driver.TERMINAL_STATE in _states(session_dir):
                log.write("completed")
                break
            now = time.monotonic()
            if watcher.waiting is None:
                presses = 0
            elif presses == 0 and now - watcher.waiting_since >= FIRST_SECONDS:
                pressed = _press(probe, key, watcher.waiting_input, again=False)
                presses, last_press = 1, time.monotonic()
                log.write(
                    "pressed",
                    key=pressed,
                    tool=watcher.waiting,
                    count=presses,
                    since_request=round(last_press - watcher.waiting_since, 1),
                )
            elif 0 < presses < PRESSES and _retries(key) and now - last_press >= RETRY_SECONDS:
                pressed = _press(probe, key, watcher.waiting_input, again=True)
                presses, last_press = presses + 1, time.monotonic()
                log.write(
                    "pressed",
                    key=pressed,
                    tool=watcher.waiting,
                    count=presses,
                    since_request=round(last_press - watcher.waiting_since, 1),
                )
            elif presses and now - last_press >= RETRY_SECONDS * 3:
                log.write("still_waiting", tool=watcher.waiting, presses=presses)
                break
            time.sleep(driver.POLL_SECONDS)
        else:
            log.write("timeout", seconds=RUN_SECONDS)
        answer = input("\n>>> What does Claude show now? Describe it in a few words\n>>> ").strip()
        log.write("operator", answer=answer)
    except CoWorkError as error:
        log.write("failed", code=error.code, message=str(error))
    except KeyboardInterrupt:
        log.write("interrupted")
    finally:
        log.close()
    print(f"\nLog: {log.path}")
    return 0


def _states(session_dir: Path) -> list[str]:
    states = []
    audit = session_dir / driver.AUDIT
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return states
    for raw in lines:
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("type") == "command_lifecycle":
            states.append(record.get("state"))
    return states


if __name__ == "__main__":
    sys.exit(main())
