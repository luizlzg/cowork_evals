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
# These boxes come from the second-brain plugin's send gate, which must be installed in Cowork:
# Cowork asks for nothing on a shell command or a read by itself. Both requests are harmless: the
# curl has no token and an empty body, and the event is for a probe test.
BASH_PROMPT = (
    "Use the bash tool to run exactly this command and tell me its output: "
    "curl -s -X POST https://graph.microsoft.com/v1.0/me/todo/lists -d '{}'"
)
CONNECTOR_PROMPT = (
    "Use the Microsoft 365 connector's create_event tool to create an event called 'probe test' "
    "tomorrow at 09:00 for 15 minutes, with no attendees. Call the tool directly."
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
    # No key allows the folder box while the keyboard is in the message field, on macOS or
    # Windows: its Allow button is pressed through accessibility instead.
    "folder_allow": (FOLDER_PROMPT, "ax_allow"),
    "folder_deny": (FOLDER_PROMPT, "esc"),
    # Tool boxes. macOS presses the box's own button; the keys are for Windows.
    "bash_allow": (BASH_PROMPT, "approve"),
    "bash_deny": (BASH_PROMPT, "esc"),
    "connector_deny": (CONNECTOR_PROMPT, "esc"),
}
if sys.platform == "darwin":
    # The digit shortcut stopped working in the Cowork update of 10 Nov 2026: press the options.
    for _name in ("question", "questions", "multiselect"):
        SCENARIOS[_name] = (SCENARIOS[_name][0], "ax_option")
    SCENARIOS["bash_allow"] = (BASH_PROMPT, "ax_allow")
    SCENARIOS["bash_deny"] = (BASH_PROMPT, "ax_deny")
    SCENARIOS["connector_deny"] = (CONNECTOR_PROMPT, "ax_deny")

# A key, or a digit for each question then a key. `approve` is Cmd+Return on macOS and Ctrl+Enter
# on Windows: allow once on every approval box (on Windows the connector box's 2 is "allow for
# this task", so digits are not used to approve).
KEYS = (
    "esc",
    "enter",
    "approve",
    "1_each",
    "1_approve",
    "1_enter",
    "ax_allow",
    "ax_deny",
    "ax_focus_enter",
    "ax_dump",
    "space",
    "down_enter",
    "tab_enter",
    "try_keys",
    "ax_option",
    *"123456789",
)
# try_keys presses these in turn, one every few seconds, on one standing request, and the log
# shows which of them answered it. The digit used to be enough; after a Cowork update it is not.
TRY_KEYS = ("1", "enter", "down_enter", "space", "tab_enter")
# ax_allow presses the box's Allow button: through the Accessibility API on macOS, through UI
# Automation on Windows (Windows PowerShell, nothing to install). ax_focus_enter, Windows only,
# gives that button the keyboard and presses Enter: the box's Allow is its default button.
AX_ALLOW = ("Allow once", "Allow")
AX_DENY = ("Deny",)
SYSTEM_EVENTS = 'tell application "System Events" to '
MAC_KEYS = {
    "esc": [SYSTEM_EVENTS + "key code 53"],
    "enter": [SYSTEM_EVENTS + "key code 36"],
    "space": [SYSTEM_EVENTS + "key code 49"],
    "down_enter": [SYSTEM_EVENTS + "key code 125", "delay 0.2", SYSTEM_EVENTS + "key code 36"],
    "tab_enter": [SYSTEM_EVENTS + "key code 48", "delay 0.2", SYSTEM_EVENTS + "key code 36"],
    "approve": [
        SYSTEM_EVENTS + "key down command",
        "delay 0.1",
        SYSTEM_EVENTS + "key code 36",
        "delay 0.1",
        SYSTEM_EVENTS + "key up command",
    ],
}
VK_CONTROL, VK_RETURN, VK_ESCAPE, VK_DIGIT_0 = 0x11, 0x0D, 0x1B, 0x30
VK_SPACE, VK_DOWN, VK_TAB = 0x20, 0x28, 0x09
WIN_KEYS = {
    "esc": [(VK_ESCAPE, False), (VK_ESCAPE, True)],
    "enter": [(VK_RETURN, False), (VK_RETURN, True)],
    "space": [(VK_SPACE, False), (VK_SPACE, True)],
    "down_enter": [(VK_DOWN, False), (VK_DOWN, True), (VK_RETURN, False), (VK_RETURN, True)],
    "tab_enter": [(VK_TAB, False), (VK_TAB, True), (VK_RETURN, False), (VK_RETURN, True)],
    "approve": [(VK_CONTROL, False), (VK_RETURN, False), (VK_RETURN, True), (VK_CONTROL, True)],
}

UIA_SCRIPT = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$labels = $env:PROBE_LABELS -split '\|'
$button = New-Object System.Windows.Automation.PropertyCondition(
  $A::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)

function Plain($name) { ($name -replace '[^A-Za-z ]+$', '').Trim() }

# The driver's rule: only a button of an approval box, one whose parent or grandparent also holds
# a Deny button. A chat in the sidebar or a banner called Allow has none.
function InBox($b) {
  $node = $walker.GetParent($b)
  for ($i = 0; $i -lt 2 -and $node; $i++) {
    foreach ($c in $node.FindAll($scope::Descendants, $button)) {
      if ((Plain $c.Current.Name) -eq 'Deny') { return $true }
    }
    $node = $walker.GetParent($node)
  }
  return $false
}

$found = $null; $seen = @()
foreach ($id in (Get-Process -Name claude -ErrorAction SilentlyContinue).Id) {
  $mine = New-Object System.Windows.Automation.PropertyCondition($A::ProcessIdProperty, $id)
  foreach ($window in $A::RootElement.FindAll($scope::Children, $mine)) {
    foreach ($b in $window.FindAll($scope::Descendants, $button)) {
      $name = $b.Current.Name
      if (-not $name) { continue }
      $seen += $name
      # A label can carry its shortcut: a digit, or the Enter symbol.
      if (-not $found -and ($labels -contains (Plain $name)) -and (InBox $b)) { $found = $b }
    }
  }
}
if (-not $found) { "pressed=" }
elseif ($env:PROBE_MODE -eq 'focus') { $found.SetFocus(); "pressed=focus:" + $found.Current.Name }
else {
  $p = $null
  if ($found.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$p)) {
    $p.Invoke(); "pressed=invoke:" + $found.Current.Name
  } else { $found.SetFocus(); "pressed=focus (no invoke):" + $found.Current.Name }
}
"buttons=" + ($seen[-10..-1] -join ' | ')
"""

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
# A run whose last answer was a deny and that then writes nothing for this long is over: a denied
# folder box ends the turn with no reply and no completed record. After an allow, Claude can
# think longer than this before it writes, so only a deny ends a run this way.
QUIET_SECONDS = 20.0
RETRY_SECONDS = 3.0
PRESSES = 4


# The driver of this run, for ax_focus_enter's Enter.
PROBE: CoWork | None = None


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
        self.last_decision: str | None = None

    def poll(self, log: Log) -> bool:
        # CoWork writes while this reads: a temporary file (.claude.json.tmp.<n>) is renamed and
        # a lock directory removed between the listing and the read. os.walk skips a directory
        # that is gone, a temporary file is not looked at, and a file gone by its stat is skipped.
        changed = False
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
                    changed = True
                if name.endswith(".jsonl"):
                    self._lines(path, relative, log)
        return changed

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
            self.last_decision = record.get("decision")


def _window_details() -> dict[str, str]:
    """Windows: the executable and the window class of the CoWork window. The driver's frontmost
    guard compares only the process name, `claude`, which Claude Code's CLI shares; this is what
    would tell the two apart."""
    import ctypes
    from ctypes import wintypes

    from cowork_evals import windows

    user32, kernel32 = windows._load()
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    hwnd = windows._cowork_window()
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    path, handle = "", kernel32.OpenProcess(0x1000, False, pid.value)
    if handle:
        size, buffer = ctypes.c_ulong(1024), ctypes.create_unicode_buffer(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            path = buffer.value
        kernel32.CloseHandle(handle)
    name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, name, 256)
    return {"exe": path, "window_class": name.value}


def _ax(key: str) -> str:
    """Press the box's Allow button. Types nothing, so no frontmost check. What it found."""
    if driver.WINDOWS:
        import subprocess

        env = {**os.environ, "PROBE_LABELS": "|".join(AX_ALLOW)}
        env["PROBE_MODE"] = "focus" if key == "ax_focus_enter" else "invoke"
        argv = ["powershell", "-NoProfile", "-NonInteractive", "-Command", UIA_SCRIPT]
        done = subprocess.run(
            argv, capture_output=True, text=True, env=env, timeout=60, check=False
        )
        found = " ".join((done.stdout + done.stderr).split())[:600]
        if key == "ax_focus_enter" and "pressed=focus" in found:
            time.sleep(0.3)
            _press_one(PROBE, "enter")
        return found
    if key == "ax_focus_enter":
        return "ax_focus_enter is Windows only"
    pressed, seen = _ax_press(list(AX_ALLOW))
    return f"pressed={pressed} buttons={' | '.join(seen[-10:])}"


def _ax_dump() -> str:
    """macOS: the accessibility subtree of the question card, as JSON. Presses nothing.

    The card is found from its Skip or Submit button: the subtree four parents up holds the
    options as siblings. Each element lists its role, subrole, title, description, value and the
    actions it takes, which is what answering a question through accessibility needs."""
    import ctypes
    import subprocess

    ax = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    p, utf8 = ctypes.c_void_p, 0x08000100
    cf.CFStringCreateWithCString.restype = p
    cf.CFStringCreateWithCString.argtypes = [p, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringGetCString.argtypes = [p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    cf.CFGetTypeID.argtypes = [p]
    cf.CFGetTypeID.restype = ctypes.c_ulong
    cf.CFStringGetTypeID.restype = ctypes.c_ulong
    cf.CFArrayGetTypeID.restype = ctypes.c_ulong
    cf.CFArrayGetCount.argtypes = [p]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetValueAtIndex.argtypes = [p, ctypes.c_long]
    cf.CFArrayGetValueAtIndex.restype = p
    cf.CFRelease.argtypes = [p]
    ax.AXUIElementCreateApplication.argtypes = [ctypes.c_int]
    ax.AXUIElementCreateApplication.restype = p
    ax.AXUIElementCopyAttributeValue.argtypes = [p, p, ctypes.POINTER(p)]
    ax.AXUIElementCopyActionNames.argtypes = [p, ctypes.POINTER(p)]
    ax.AXUIElementSetAttributeValue.argtypes = [p, p, p]
    owned: list[int] = []

    def name(text: str) -> int:
        value = cf.CFStringCreateWithCString(None, text.encode(), utf8)
        owned.append(value)
        return value

    def copy(element: int, attribute: int) -> int | None:
        value = p()
        if ax.AXUIElementCopyAttributeValue(element, attribute, ctypes.byref(value)) != 0:
            return None
        owned.append(value.value)
        return value.value

    def text(element: int, attribute: int) -> str:
        value = copy(element, attribute)
        if not value or cf.CFGetTypeID(value) != cf.CFStringGetTypeID():
            return ""
        buffer = ctypes.create_string_buffer(1024)
        cf.CFStringGetCString(value, buffer, 1024, utf8)
        return buffer.value.decode(errors="replace")

    def array(value: int | None) -> list[int]:
        if not value or cf.CFGetTypeID(value) != cf.CFArrayGetTypeID():
            return []
        return [cf.CFArrayGetValueAtIndex(value, i) for i in range(cf.CFArrayGetCount(value))]

    role, subrole, title, description, value, children, parent = (
        name(n)
        for n in (
            "AXRole",
            "AXSubrole",
            "AXTitle",
            "AXDescription",
            "AXValue",
            "AXChildren",
            "AXParent",
        )
    )
    found = subprocess.run(["pgrep", "-x", driver.COWORK_PROCESS], capture_output=True, text=True)
    app = ax.AXUIElementCreateApplication(int(found.stdout.split()[0]))
    owned.append(app)
    ax.AXUIElementSetAttributeValue(
        app, name("AXManualAccessibility"), p.in_dll(cf, "kCFBooleanTrue")
    )

    def label(element: int) -> str:
        return text(element, title) or text(element, description) or text(element, value)

    anchor, stack = None, [app]
    try:
        while stack and anchor is None:
            element = stack.pop()
            if text(element, role) == "AXButton" and label(element).split(" ")[0] in (
                "Skip",
                "Submit",
            ):
                anchor = element
            stack.extend(array(copy(element, children)))
        if anchor is None:
            return json.dumps({"error": "no Skip or Submit button: no question card on screen"})
        top = anchor
        for _ in range(4):
            up = copy(top, parent)
            if not up:
                break
            top = up
        out: list[dict[str, Any]] = []

        def walk(element: int, depth: int) -> None:
            if len(out) >= 160 or depth > 7:
                return
            actions = p()
            names: list[str] = []
            if ax.AXUIElementCopyActionNames(element, ctypes.byref(actions)) == 0:
                owned.append(actions.value)
                names = [text_of(x) for x in array(actions.value)]
            out.append(
                {
                    "depth": depth,
                    "role": text(element, role),
                    "subrole": text(element, subrole),
                    "label": label(element)[:100],
                    "actions": names,
                }
            )
            for kid in array(copy(element, children)):
                walk(kid, depth + 1)

        def text_of(x: int) -> str:
            if cf.CFGetTypeID(x) != cf.CFStringGetTypeID():
                return ""
            buffer = ctypes.create_string_buffer(256)
            cf.CFStringGetCString(x, buffer, 256, utf8)
            return buffer.value.decode(errors="replace")

        walk(top, 0)
        return json.dumps(out, ensure_ascii=False)
    finally:
        for owned_value in owned:
            cf.CFRelease(owned_value)


def _ax_press(labels: list[str]) -> tuple[str, list[str]]:
    """macOS: press the first Claude button labelled one of `labels`, its shortcut digit dropped.
    The button pressed, or "", and every label seen."""
    import ctypes
    import re
    import subprocess

    ax = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    p, utf8 = ctypes.c_void_p, 0x08000100
    cf.CFStringCreateWithCString.restype = p
    cf.CFStringCreateWithCString.argtypes = [p, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringGetCString.argtypes = [p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    cf.CFGetTypeID.argtypes = [p]
    cf.CFGetTypeID.restype = ctypes.c_ulong
    cf.CFStringGetTypeID.restype = ctypes.c_ulong
    cf.CFArrayGetTypeID.restype = ctypes.c_ulong
    cf.CFArrayGetCount.argtypes = [p]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetValueAtIndex.argtypes = [p, ctypes.c_long]
    cf.CFArrayGetValueAtIndex.restype = p
    cf.CFRelease.argtypes = [p]
    ax.AXUIElementCreateApplication.argtypes = [ctypes.c_int]
    ax.AXUIElementCreateApplication.restype = p
    ax.AXUIElementCopyAttributeValue.argtypes = [p, p, ctypes.POINTER(p)]
    ax.AXUIElementSetAttributeValue.argtypes = [p, p, p]
    ax.AXUIElementPerformAction.argtypes = [p, p]
    owned: list[int] = []

    def name(text: str) -> int:
        value = cf.CFStringCreateWithCString(None, text.encode(), utf8)
        owned.append(value)
        return value

    def copy(element: int, attribute: int) -> int | None:
        value = p()
        if ax.AXUIElementCopyAttributeValue(element, attribute, ctypes.byref(value)) != 0:
            return None
        owned.append(value.value)
        return value.value

    def text(element: int, attribute: int) -> str:
        value = copy(element, attribute)
        if not value or cf.CFGetTypeID(value) != cf.CFStringGetTypeID():
            return ""
        buffer = ctypes.create_string_buffer(1024)
        cf.CFStringGetCString(value, buffer, 1024, utf8)
        return buffer.value.decode(errors="replace")

    role, title, description, children = (
        name(n) for n in ("AXRole", "AXTitle", "AXDescription", "AXChildren")
    )
    press = name("AXPress")
    found = subprocess.run(["pgrep", "-x", driver.COWORK_PROCESS], capture_output=True, text=True)
    app = ax.AXUIElementCreateApplication(int(found.stdout.split()[0]))
    owned.append(app)
    ax.AXUIElementSetAttributeValue(
        app, name("AXManualAccessibility"), p.in_dll(cf, "kCFBooleanTrue")
    )
    seen: list[str] = []
    stack = [(app, 0)]
    try:
        while stack:
            element, depth = stack.pop()
            if text(element, role) == "AXButton":
                label = text(element, title) or text(element, description)
                if label:
                    seen.append(label)
                    if re.sub(r"\s+\d$", "", label.strip()) in labels:
                        ok = ax.AXUIElementPerformAction(element, press) == 0
                        return (label if ok else f"{label} (refused)"), seen
            kids = copy(element, children) if depth < 40 else None
            if kids and cf.CFGetTypeID(kids) == cf.CFArrayGetTypeID():
                for index in reversed(range(cf.CFArrayGetCount(kids))):
                    stack.append((cf.CFArrayGetValueAtIndex(kids, index), depth + 1))
        return "", seen
    finally:
        for value in owned:
            cf.CFRelease(value)


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
    if key == "ax_dump":
        return f"ax_dump: {_ax_dump()}"
    if key == "ax_option":
        # The driver's own question step (cowork_evals.macos, branch feat/cowork-interactions):
        # choose the card's first option, or press its Submit or Next question. One step per press.
        from cowork_evals import macos

        acted, detail = macos.answer_question(driver.COWORK_PROCESS)
        return f"ax_option: acted={acted} {detail[:700]}"
    if key == "ax_deny":
        pressed, seen = _ax_press(list(AX_DENY))
        return f"ax_deny: pressed={pressed} buttons={' | '.join(seen[-10:])}"
    if key in ("ax_allow", "ax_focus_enter"):
        return f"{key}: {_ax(key)}"
    _press_one(probe, key)
    return key


def _retries(key: str) -> bool:
    """Whether a key is pressed again while its request stands. A lone digit is not."""
    return not key.isdigit() and key not in ("1_each", "ax_dump")


def _limit(key: str) -> int:
    """How many presses a key gets while its request stands."""
    if key == "ax_option":
        return 8
    return len(TRY_KEYS) if key == "try_keys" else PRESSES


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--key", choices=KEYS, help="the key to press instead of the scenario's")
    parser.add_argument(
        "--delay",
        type=float,
        default=FIRST_SECONDS,
        help="seconds a request stands before the first press (default %(default)s)",
    )
    parser.add_argument(
        "--config", help="cowork_evals.yaml to read, default the working directory's"
    )
    args = parser.parse_args()
    prompt, key = SCENARIOS[args.scenario]
    key = args.key or key

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log = Log(Path(f"interaction_probe_{args.scenario}_{stamp}.log").resolve())
    global PROBE
    probe = CoWork.from_file(args.config) if args.config else CoWork()
    PROBE = probe
    log.write(
        "start",
        scenario=args.scenario,
        platform=sys.platform,
        os=platform.platform(),
        python=platform.python_version(),
        prompt=prompt,
        key=key,
    )
    if driver.WINDOWS:
        try:
            log.write("window", **_window_details())
        except Exception as error:  # a diagnostic: it never stops the run
            log.write("window", error=str(error)[:200])
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
    last_change = time.monotonic()
    try:
        while time.monotonic() < deadline:
            if watcher.poll(log):
                last_change = time.monotonic()
            if driver.TERMINAL_STATE in _states(session_dir):
                log.write("completed")
                break
            now = time.monotonic()
            if (
                watcher.waiting is None
                and watcher.last_decision == "deny"
                and now - last_change >= QUIET_SECONDS
            ):
                log.write("ended_after_deny", seconds=QUIET_SECONDS)
                break
            if watcher.waiting is None:
                presses = 0
            elif presses == 0 and now - watcher.waiting_since >= args.delay:
                first = TRY_KEYS[0] if key == "try_keys" else key
                pressed = _press(probe, first, watcher.waiting_input, again=False)
                presses, last_press = 1, time.monotonic()
                log.write(
                    "pressed",
                    key=pressed,
                    tool=watcher.waiting,
                    count=presses,
                    since_request=round(last_press - watcher.waiting_since, 1),
                )
            elif 0 < presses < _limit(key) and _retries(key) and now - last_press >= RETRY_SECONDS:
                again = TRY_KEYS[presses] if key == "try_keys" else key
                pressed = _press(probe, again, watcher.waiting_input, again=True)
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
