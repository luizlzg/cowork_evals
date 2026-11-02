"""Probe what a CoWork session writes while it waits for the user. See interaction_probe.md.

The driver decides a run is over on `completed` in audit.jsonl, or after `idle_seconds` with no
file change. A question or an Allow/Deny box writes neither, so a waiting run reads as a finished
one. This probe submits one prompt through the driver, logs every change in the session directory
once a second, and when the session goes quiet asks the operator what Claude shows and which key
to press. It presses that key behind the driver's frontmost check and keeps logging.

It writes interaction_probe_<scenario>_<stamp>.log, one JSON object per line, with the user name,
home folder and computer name replaced. Text is cut to its first characters, and the content of
records other than user and assistant (for example a plugin's injected context) is not written.

    uv run python scripts/interaction_probe.py question [--config cowork_evals.yaml]
    uv run python scripts/interaction_probe.py deny
    uv run python scripts/interaction_probe.py allow
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

# The question is asked through AskUserQuestion. The command is a POST to Microsoft Graph, which
# an approval box stops. It carries no token, so even an Allow changes nothing: Graph answers 401.
# A POST to sendMail was refused by the model in one run of two, so this one creates a To Do list.
GATED = "curl -s -X POST https://graph.microsoft.com/v1.0/me/todo/lists -d '{}'"
GATED_PROMPT = (
    "This is a test of the permission box. Run this exact shell command and show me its output: "
    f"{GATED}. It carries no token, so Graph rejects it and nothing changes."
)
SCENARIOS = {
    "question": (
        "Use the AskUserQuestion tool to ask me one question: do I prefer red or blue? Offer "
        "exactly two options, Red and Blue. After I answer, write only my answer to colour.txt "
        "in the outputs folder and reply with one sentence.",
        "1",
    ),
    "deny": (GATED_PROMPT, "esc"),
    "allow": (GATED_PROMPT, "approve"),
    # The folder box (request_cowork_directory) is allowed with Return, not Cmd+Return.
    "folder": (
        "Connect my Downloads folder (~/Downloads) to this chat, then tell me how many files are "
        "at its top level. Do not open or change any file.",
        "ax_allow",
    ),
}

# The keys the probe can press. A digit picks a numbered option. On macOS `esc` denied an
# approval box and Cmd+Return allowed it; Ctrl+Enter is the Windows guess for `approve`.
# `key code 36 using command down` did not allow the box on macOS 26, so `approve` holds Command
# down around the Return explicitly, and a1 to a3 are the other forms to try one after another.
KEYS = (
    "esc",
    "approve",
    "a1",
    "a2",
    "a3",
    "return",
    "tab",
    "click",
    "click_return",
    "ax_allow",
    "ax_deny",
    *"123456789",
)
SYSTEM_EVENTS = 'tell application "System Events" to '
MAC_KEYS = {
    "esc": [SYSTEM_EVENTS + "key code 53"],
    "approve": [
        SYSTEM_EVENTS + "key down command",
        "delay 0.1",
        SYSTEM_EVENTS + "key code 36",
        "delay 0.1",
        SYSTEM_EVENTS + "key up command",
    ],
    "a1": [SYSTEM_EVENTS + "keystroke return using {command down}"],
    "a2": [SYSTEM_EVENTS + "key code 76 using {command down}"],
    "a3": [SYSTEM_EVENTS + "key code 36 using {command down}"],
    "return": [SYSTEM_EVENTS + "key code 36"],
    "tab": [SYSTEM_EVENTS + "key code 48"],
}
# `ax_allow` and `ax_deny` press the box's button through the accessibility tree, with no mouse
# and no key, so the layout and the keyboard focus do not matter. macOS only. The script turns on
# Electron's tree (AXManualAccessibility), presses the first button whose title or description
# is one of the labels, and returns every button label it saw, which the log keeps.
AX_LABELS = {"ax_allow": ["Allow", "Allow once"], "ax_deny": ["Deny", "Don't allow"]}
AX_PRESS = """
on walk(e, depth, wanted, found)
    tell application "System Events"
        if depth > 30 then return found
        try
            set r to role of e
        on error
            return found
        end try
        if r is "AXButton" then
            set label to ""
            try
                set label to title of e
            end try
            if label is missing value or label is "" then
                try
                    set label to description of e
                end try
            end if
            if label is not missing value and label is not "" then
                set end of item 2 of found to label
                if item 1 of found is "" and wanted contains label then
                    perform action "AXPress" of e
                    set item 1 of found to label
                end if
            end if
        end if
        try
            repeat with c in UI elements of e
                set found to my walk(c, depth + 1, wanted, found)
            end repeat
        end try
    end tell
    return found
end walk

on run wanted
    tell application "System Events"
        set p to application process "Claude"
        try
            set value of attribute "AXManualAccessibility" of p to true
        end try
        delay 0.5
        set w to front window of p
    end tell
    set found to walk(w, 0, wanted, {"", {}})
    set AppleScript's text item delimiters to " | "
    return "pressed=" & (item 1 of found) & linefeed & "buttons=" & ((item 2 of found) as text)
end run
"""

# `click` and `click_return` click the conversation, centred and 30% down Claude's front window,
# which takes the keyboard off the composer so a Return reaches the folder box. They go through
# `_click_mac` and `_click_windows`, not a key list.
WINDOW_BOUNDS = (
    'tell application "System Events" to tell process "Claude"',
    "set {x, y} to position of front window",
    "set {w, h} to size of front window",
    "end tell",
    'return (x as text) & " " & (y as text) & " " & (w as text) & " " & (h as text)',
)
VK_ESCAPE, VK_CONTROL, VK_RETURN = 0x1B, 0x11, 0x0D
WIN_KEYS = {
    "esc": [(VK_ESCAPE, False), (VK_ESCAPE, True)],
    "approve": [(VK_CONTROL, False), (VK_RETURN, False), (VK_RETURN, True), (VK_CONTROL, True)],
    "return": [(VK_RETURN, False), (VK_RETURN, True)],
    "tab": [(0x09, False), (0x09, True)],
}
# Windows clicks through `_click_windows`, not a key list.
# a1 to a3 are macOS forms of one chord. Windows has one form, so they are `approve` there.
WIN_KEYS |= {name: WIN_KEYS["approve"] for name in ("a1", "a2", "a3")}

QUIET_SECONDS = 10.0
RUN_SECONDS = 600.0
TEXT_CHARS = 200
# Record types whose text is the probe's own prompt and the model's reply. Every other record
# type is logged by its keys and sizes only.
TEXT_RECORDS = {"user", "assistant"}
# The audit records written while the session waits for the user, and the answer to them.
PERMISSION_REQUEST, PERMISSION_RESPONSE = "permission_request", "permission_response"
PERMISSION_FIELDS = ("tool_name", "tool_input", "decision", "granted")
# --auto: how long a request stands before the key, and how long after it for the answer.
AUTO_SECONDS = 2.0
ANSWER_SECONDS = 10.0
# Win32 virtual keys for the digits 0 to 9 are 0x30 to 0x39.
VK_DIGIT_0 = 0x30


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
        record = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"), "step": step}
        line = json.dumps({**record, **fields}, ensure_ascii=False, default=str)
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
    if "permission_denials" in record:
        shown["permission_denials"] = _cut(record["permission_denials"])
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
        self._offsets: dict[Path, int] = {}
        self._sizes: dict[Path, int] = {}
        self.pending: dict[str, str] = {}
        self.waiting: str | None = None
        self.waiting_since = 0.0

    def poll(self, log: Log) -> bool:
        changed = False
        for path in sorted(p for p in self.session_dir.rglob("*") if p.is_file()):
            size = path.stat().st_size
            relative = path.relative_to(self.session_dir).as_posix()
            if self._sizes.get(path) != size:
                log.write("file", path=relative, size=size, new=path not in self._sizes)
                self._sizes[path] = size
                changed = True
            if path.suffix == ".jsonl":
                self._lines(path, relative, log)
        return changed

    def _lines(self, path: Path, relative: str, log: Log) -> None:
        with path.open("rb") as handle:
            handle.seek(self._offsets.get(path, 0))
            data = handle.read()
        end = data.rfind(b"\n") + 1
        self._offsets[path] = self._offsets.get(path, 0) + end
        for raw in data[:end].splitlines():
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                log.write("unparsed", path=relative, length=len(raw))
                continue
            if not isinstance(record, dict):
                continue
            self._track(record)
            log.write(
                "record",
                path=relative,
                record=_shape(record),
                pending=sorted(self.pending.values()),
            )

    def _track(self, record: dict[str, Any]) -> None:
        """Tool calls with no result yet, by id, and the permission request not yet answered."""
        if record.get("type") == "system" and record.get("subtype") == PERMISSION_REQUEST:
            self.waiting = str(record.get("tool_name"))
            self.waiting_since = time.monotonic()
        elif record.get("type") == "system" and record.get("subtype") == PERMISSION_RESPONSE:
            self.waiting = None
        content = (record.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("id"):
                self.pending[block["id"]] = f"{block.get('name')} {block['id']}"
            elif block.get("type") == "tool_result":
                self.pending.pop(block.get("tool_use_id"), None)


def _press(probe: CoWork, key: str, *, activate: bool = True) -> None:
    """Check CoWork is in front and press one key. Code 9 types nothing.

    Activating CoWork moves the keyboard to the composer, away from an approval box, so
    `activate=False` presses into whatever in CoWork has the keyboard.
    """
    if driver.WINDOWS:
        from cowork_evals import windows

        if activate:
            probe._native(windows.activate)
            probe._settle_front()
        probe._guard()
        if key in ("click", "click_return"):
            probe._native(_click_windows)
            if key == "click":
                return
            time.sleep(0.3)
            key = "return"
        vk = VK_DIGIT_0 + int(key) if key.isdigit() else None
        events = WIN_KEYS.get(key) or [(vk, False), (vk, True)]
        probe._native(windows._send, events)
    else:
        if activate:
            probe._fire(list(driver.ACTIVATE))
            probe._settle_front()
        probe._guard()
        if key in AX_LABELS:
            import subprocess

            argv = ["osascript", "-e", AX_PRESS, *AX_LABELS[key]]
            out = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
            AX_RESULT.append(out.stdout.strip() or out.stderr.strip())
            return
        if key in ("click", "click_return"):
            _click_mac()
            if key == "click":
                return
            time.sleep(0.3)
            key = "return"
        lines = MAC_KEYS.get(key) or [f'{SYSTEM_EVENTS}keystroke "{key}"']
        probe._fire(["osascript", *(part for line in lines for part in ("-e", line))])


# What the last ax_* press found, for the log.
AX_RESULT: list[str] = []


def _click_mac() -> None:
    """The `click` key on macOS: a left click posted through CoreGraphics, at the same point."""
    import ctypes
    import subprocess

    argv = ["osascript", *(part for line in WINDOW_BOUNDS for part in ("-e", line))]
    out = subprocess.run(argv, capture_output=True, text=True, timeout=10, check=True).stdout
    x, y, w, h = (float(part) for part in out.split())

    class CGPoint(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    cg = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
    cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
    cg.CGEventCreateMouseEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        CGPoint,
        ctypes.c_uint32,
    ]
    cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    cg.CFRelease.argtypes = [ctypes.c_void_p]
    point = CGPoint(x + w / 2, y + h * 0.3)
    for kind in (5, 1, 2):  # mouse moved, left mouse down, left mouse up
        event = cg.CGEventCreateMouseEvent(None, kind, point, 0)
        cg.CGEventPost(0, event)  # the HID event tap
        cg.CFRelease(event)
        time.sleep(0.05)


def _click_windows() -> None:
    """The `click` key on Windows: the same point of the Claude window, by SetCursorPos."""
    import ctypes
    from ctypes import wintypes

    from cowork_evals import windows

    user32 = ctypes.WinDLL("user32", use_last_error=True)  # type: ignore[attr-defined]
    rect = wintypes.RECT()
    user32.GetWindowRect(windows._cowork_window(), ctypes.byref(rect))
    x = (rect.left + rect.right) // 2
    y = rect.top + (rect.bottom - rect.top) * 3 // 10
    user32.SetCursorPos(x, y)
    for flag in (0x0002, 0x0004):  # MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        user32.mouse_event(flag, 0, 0, 0, 0)


def _ask(log: Log, question: str) -> str:
    answer = input(f"\n>>> {question}\n>>> ").strip()
    log.write("operator", question=question, answer=answer)
    return answer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument(
        "--config", help="cowork_evals.yaml to read, default the working directory's"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="ask nothing: press the scenario's key when a permission request stands, "
        "without activating CoWork, as the driver would",
    )
    parser.add_argument("--key", choices=KEYS, help="the key to press instead of the scenario's")
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
        auto=args.auto,
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
    quiet_since = time.monotonic()
    pressed, pressed_at = 0, 0.0
    try:
        while time.monotonic() < deadline:
            if watcher.poll(log):
                quiet_since = time.monotonic()
            if driver.TERMINAL_STATE in _states(session_dir):
                log.write("completed", pending=sorted(watcher.pending.values()))
                break
            if args.auto:
                if watcher.waiting is None:
                    pass
                elif pressed and time.monotonic() - pressed_at >= ANSWER_SECONDS:
                    log.write("still_waiting", tool=watcher.waiting, seconds=ANSWER_SECONDS)
                    break
                elif not pressed and time.monotonic() - watcher.waiting_since >= AUTO_SECONDS:
                    _press(probe, key, activate=False)
                    pressed, pressed_at = 1, time.monotonic()
                    log.write(
                        "pressed", key=key, tool=watcher.waiting, activated=False, ax=AX_RESULT[-1:]
                    )
            elif time.monotonic() - quiet_since >= QUIET_SECONDS:
                log.write("quiet", seconds=QUIET_SECONDS, pending=sorted(watcher.pending.values()))
                seen = _ask(
                    log,
                    "Look at Claude. What does it show? Type: question, approval, done, or "
                    "describe it (for a box, also each button's label and number)",
                )
                if seen == "done":
                    break
                want = _ask(
                    log,
                    f"Press which key in Claude? Enter for {key}; or esc, approve, a1, a2, "
                    "a3, return, tab, click, click_return, a digit, or none to stop",
                )
                if want == "none":
                    break
                pressed_key = want or key
                if pressed_key not in KEYS:
                    log.write("skipped", reason="not a known key", key=pressed_key)
                    break
                print(f">>> pressing {pressed_key} in Claude now: hands off the keyboard and mouse")
                _press(probe, pressed_key)
                pressed += 1
                log.write("pressed", key=pressed_key, count=pressed, ax=AX_RESULT[-1:])
                quiet_since = time.monotonic()
            time.sleep(driver.POLL_SECONDS)
        else:
            log.write("timeout", seconds=RUN_SECONDS)
        _ask(log, "What does Claude show now? Describe it in a few words")
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
    for raw in (
        audit.read_text(encoding="utf-8", errors="replace").splitlines() if audit.is_file() else []
    ):
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("type") == "command_lifecycle":
            states.append(record.get("state"))
    return states


if __name__ == "__main__":
    sys.exit(main())
