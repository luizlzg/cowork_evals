"""Probe a Windows PC for what a Windows CoWork driver needs. See windows_probe.md.

The macOS driver opens a claude:// deep link, brings Claude to the front, clears the message box,
presses Return, and finds the new session under <profile>/local-agent-mode-sessions/*/*/*. This
probe checks each of those on Windows, except Return: it never presses it, so nothing is sent.

It writes windows_probe_<stamp>.log, one JSON object per line, with the user name, home folder
and computer name replaced. Standard library only.
"""

from __future__ import annotations

import ctypes
import itertools
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

PROBE_TEXT = "cowork_evals probe - DO NOT SEND"
TYPED_TEXT = "probe typed"
DEEP_LINK = "claude://claude.ai/new?" + urlencode(
    {"q": PROBE_TEXT, "surface": "cowork"}, quote_via=quote, safe=""
)

VK_MENU, VK_CONTROL, VK_A, VK_DELETE = 0x12, 0x11, 0x41, 0x2E
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x2, 0x4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class Log:
    """Writes and flushes one line per record, so a run that stops halfway still helps."""

    def __init__(self, path: Path) -> None:
        self._file = path.open("w", encoding="utf-8")
        names = ("USERPROFILE", "LOCALAPPDATA", "APPDATA", "USERNAME", "COMPUTERNAME")
        pairs = {(os.environ[n], f"%{n}%") for n in names if len(os.environ.get(n, "")) >= 3}
        self._replace = sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)

    def write(self, step: str, **fields: object) -> None:
        record = {"t": datetime.now(timezone.utc).isoformat(timespec="seconds"), "step": step}
        line = json.dumps({**record, **fields}, ensure_ascii=False, default=str)
        for value, label in self._replace:
            for form in (value, value.replace("\\", "\\\\")):
                line = _replace_ci(line, form, label)
        self._file.write(line + "\n")
        self._file.flush()
        print(f"[{step}] {line[:150]}")

    def close(self) -> None:
        self._file.close()


def _replace_ci(text: str, value: str, label: str) -> str:
    out, start, lower, needle = [], 0, text.lower(), value.lower()
    while (index := lower.find(needle, start)) >= 0:
        out += [text[start:index], label]
        start = index + len(value)
    return "".join(out) + text[start:]


def ask(log: Log, step: str, question: str) -> None:
    try:
        answer = input(f"\n>>> {question} [y/n]: ").strip()
    except EOFError:
        answer = "<no input>"
    log.write(step, question=question, answer=answer)


# --- Win32 -----------------------------------------------------------------------------------

user32 = kernel32 = None


def load_win32() -> None:
    global user32, kernel32
    from ctypes import wintypes as w

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.EnumWindows.argtypes = [ctypes.c_void_p, w.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
    user32.GetWindowTextLengthW.argtypes = [w.HWND]
    user32.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [w.HWND]
    user32.GetForegroundWindow.restype = w.HWND
    user32.SetForegroundWindow.argtypes = [w.HWND]
    user32.keybd_event.argtypes = [w.BYTE, w.BYTE, w.DWORD, ctypes.c_void_p]
    user32.SendInput.argtypes = [w.UINT, ctypes.c_void_p, ctypes.c_int]
    kernel32.GetConsoleWindow.restype = w.HWND
    kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel32.OpenProcess.restype = w.HANDLE
    kernel32.CloseHandle.argtypes = [w.HANDLE]
    kernel32.QueryFullProcessImageNameW.argtypes = [
        w.HANDLE,
        w.DWORD,
        w.LPWSTR,
        ctypes.POINTER(w.DWORD),
    ]


def describe(hwnd) -> dict:
    """The window's title and the exe name of the process that owns it."""
    if not hwnd:
        return {"hwnd": None, "exe": None, "title": None}
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    exe = None
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if handle:
        size, buffer = ctypes.c_ulong(1024), ctypes.create_unicode_buffer(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            exe = Path(buffer.value).name
        kernel32.CloseHandle(handle)
    title = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(hwnd) + 1)
    user32.GetWindowTextW(hwnd, title, len(title))
    return {"hwnd": int(hwnd), "exe": exe, "title": title.value}


def claude_windows() -> list[dict]:
    found = []
    callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def collect(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd):
            window = describe(hwnd)
            if "claude" in (window["exe"] or "").lower():
                found.append(window)
        return True

    user32.EnumWindows(callback(collect), 0)
    return found


def foreground() -> dict:
    return describe(user32.GetForegroundWindow())


def press_alt() -> None:
    """A key press of our own, which lets this process take the foreground."""
    user32.keybd_event(VK_MENU, 0, 0, None)
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, None)


def send_keys(events: list[tuple[int, int, int]]) -> dict:
    """SendInput for (virtual key, scan code, flags). `sent` < `requested` means blocked."""

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class MOUSEINPUT(ctypes.Structure):  # only sizes the union, as SendInput expects
        _fields_ = [
            ("dx", ctypes.c_long),
            ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_ulong),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("u", INPUTUNION)]

    inputs = (INPUT * len(events))()
    for index, (vk, scan, flags) in enumerate(events):
        inputs[index].type = 1  # INPUT_KEYBOARD
        inputs[index].u.ki = KEYBDINPUT(vk, scan, flags, 0, None)
    sent = user32.SendInput(len(events), inputs, ctypes.sizeof(INPUT))
    return {"requested": len(events), "sent": sent, "last_error": ctypes.get_last_error()}


# --- the checks ------------------------------------------------------------------------------


def check_sessions(log: Log) -> None:
    """Where the sessions are, and whether the macOS layout */*/*/audit.jsonl holds."""
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")):
        if not base:
            continue
        for profile in sorted(Path(base).glob("[Cc]laude*")):
            root = profile / "local-agent-mode-sessions"
            entry = {"profile": str(profile), "sessions_dir": root.is_dir()}
            if root.is_dir():
                sessions = [d for d in root.glob("*/*/*") if (d / "audit.jsonl").is_file()]
                entry["sessions_matching_layout"] = len(sessions)
                entry["audit_depths"] = sorted(
                    {len(p.relative_to(root).parts) - 1 for p in root.rglob("audit.jsonl")}
                )
                if sessions:
                    newest = max(sessions, key=lambda d: d.stat().st_mtime)
                    transcripts = newest / ".claude" / "projects" / "session"
                    entry["newest_has_transcripts"] = transcripts.is_dir()
                    entry["newest_audit_records"] = audit_shape(newest / "audit.jsonl")
            log.write("sessions", **entry)


def audit_shape(audit: Path) -> list[dict]:
    """Field names and the type of the first records, never their content."""
    shape = []
    with audit.open(encoding="utf-8", errors="replace") as handle:
        for line in itertools.islice(handle, 3):
            try:
                record = json.loads(line)
                shape.append({"type": record.get("type"), "keys": sorted(record)})
            except (ValueError, AttributeError):
                shape.append({"unparsable": True})
    return shape


def check_deep_link(log: Log) -> None:
    print(f"\nThe probe will open a new Cowork chat with '{PROBE_TEXT}' in the message box.")
    print("Do NOT press Enter in Claude and do NOT click Send.")
    input("Press Enter here to open it... ")
    try:
        os.startfile(DEEP_LINK)
        log.write("deep_link", link=DEEP_LINK, ok=True)
    except OSError as error:
        log.write("deep_link", link=DEEP_LINK, ok=False, error=str(error))
        return
    time.sleep(5)
    log.write("deep_link.foreground", window=foreground())
    ask(log, "deep_link.new_cowork_chat", "Did a NEW chat open in Cowork (not the Chat tab)?")
    ask(log, "deep_link.prefilled", f"Is '{PROBE_TEXT}' in the message box?")
    ask(log, "deep_link.cursor", "Is the cursor in the message box (could you type right away)?")


def check_focus(log: Log, claude: int) -> None:
    """Can a background script bring Claude to the front? Windows often refuses."""
    console = kernel32.GetConsoleWindow()
    print("\nThe probe will switch from this window to Claude twice. Do not touch anything.")
    input("Click into THIS window, then press Enter... ")
    for method in ("plain", "alt_key_first"):
        user32.SetForegroundWindow(console)
        time.sleep(1)
        before = foreground()["exe"]
        if method == "alt_key_first":
            press_alt()
        returned = bool(user32.SetForegroundWindow(claude))
        time.sleep(1)
        after = foreground()
        log.write(
            f"focus.{method}",
            claude_in_front=after["hwnd"] == claude,
            returned=returned,
            before=before,
            after=after["exe"],
        )


def check_keys(log: Log, claude: int) -> None:
    print(
        f"\nThe probe will clear Claude's message box and type '{TYPED_TEXT}'. It never presses "
        "Enter. Do not touch anything."
    )
    input("Make sure the probe chat is showing in Claude, then press Enter here... ")
    press_alt()
    user32.SetForegroundWindow(claude)
    time.sleep(1)
    if foreground()["hwnd"] != claude:  # the driver's guard: never type into anything else
        log.write("keys", ok=False, error="Claude was not in front; nothing typed")
        return
    clear = [
        (VK_CONTROL, 0, 0),
        (VK_A, 0, 0),
        (VK_A, 0, KEYEVENTF_KEYUP),
        (VK_CONTROL, 0, KEYEVENTF_KEYUP),
        (VK_DELETE, 0, 0),
        (VK_DELETE, 0, KEYEVENTF_KEYUP),
    ]
    log.write("keys.clear", **send_keys(clear))
    time.sleep(1)
    typed = [(0, ord(c), KEYEVENTF_UNICODE | up) for c in TYPED_TEXT for up in (0, KEYEVENTF_KEYUP)]
    log.write("keys.type", **send_keys(typed))
    ask(log, "keys.result", f"Does the message box now show only '{TYPED_TEXT}'?")


def main() -> int:
    path = Path.cwd() / f"windows_probe_{datetime.now():%Y%m%d-%H%M%S}.log"
    log = Log(path)
    try:
        log.write("system", windows=platform.platform(), python=sys.version.split()[0])
        if sys.platform != "win32":
            log.write("system", ok=False, error="not Windows; nothing else was run")
            return 1
        load_win32()
        check_sessions(log)
        windows = claude_windows()
        log.write("claude_windows", windows=windows)
        if not windows:
            log.write("claude_windows", ok=False, error="no Claude window: open Claude, run again")
            return 1
        claude = windows[0]["hwnd"]
        check_deep_link(log)
        check_focus(log, claude)
        check_keys(log, claude)
        print("\nDone. Delete the text in Claude's message box by hand and close that chat.")
        ask(log, "sent_by_accident", "Was anything sent by accident?")
        return 0
    except KeyboardInterrupt:
        log.write("stopped", reason="Ctrl+C")
        return 130
    except Exception as error:  # a probe logs what broke instead of losing the log
        log.write("error", error=f"{type(error).__name__}: {error}")
        return 1
    finally:
        log.close()
        print(f"\nSend back this one file:\n  {path}")


if __name__ == "__main__":
    sys.exit(main())
