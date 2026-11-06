"""Press a button of the CoWork application through the macOS Accessibility API.

An approval box is answered by pressing its own button, found by label: no mouse and no key, so
the layout, the keyboard focus and the frontmost application do not matter. A key reaches the
box only when the composer does not hold the keyboard, and the folder box never takes one.
Measured on macOS 26 with the interaction probe. docs/cowork_desktop.md.

The application exposes its tree once AXManualAccessibility is set, which an Electron
application waits for. One walk of the tree takes well under a second.
"""

from __future__ import annotations

import ctypes
import re
import subprocess

_APPLICATION_SERVICES = (
    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)
_CORE_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
_UTF8 = 0x08000100
_DEPTH = 40

# A button carries its shortcut digit in its label: "Deny 1", "Allow once 2".
_SHORTCUT = re.compile(r"\s+\d$")


def press_button(process: str, labels: tuple[str, ...]) -> bool:
    """Press the first button of `process` labelled one of `labels`. False when there is none.

    A label matches with its trailing shortcut digit dropped. `OSError` when the process is
    not running.
    """
    found = subprocess.run(["pgrep", "-x", process], capture_output=True, text=True, check=False)
    if not found.stdout.split():
        raise OSError(f"{process} is not running")
    ax, cf = ctypes.CDLL(_APPLICATION_SERVICES), ctypes.CDLL(_CORE_FOUNDATION)
    _declare(ax, cf)
    owned: list[int] = []

    def name(text: str) -> int:
        value = cf.CFStringCreateWithCString(None, text.encode(), _UTF8)
        owned.append(value)
        return value

    def copy(element: int, attribute: int) -> int | None:
        value = ctypes.c_void_p()
        if ax.AXUIElementCopyAttributeValue(element, attribute, ctypes.byref(value)) != 0:
            return None
        owned.append(value.value)
        return value.value

    def text(element: int, attribute: int) -> str:
        value = copy(element, attribute)
        if not value or cf.CFGetTypeID(value) != cf.CFStringGetTypeID():
            return ""
        buffer = ctypes.create_string_buffer(1024)
        cf.CFStringGetCString(value, buffer, 1024, _UTF8)
        return buffer.value.decode(errors="replace")

    role, title, description, children = (
        name(n) for n in ("AXRole", "AXTitle", "AXDescription", "AXChildren")
    )
    press = name("AXPress")
    app = ax.AXUIElementCreateApplication(int(found.stdout.split()[0]))
    owned.append(app)
    true = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")
    ax.AXUIElementSetAttributeValue(app, name("AXManualAccessibility"), true)
    stack = [(app, 0)]
    try:
        while stack:
            element, depth = stack.pop()
            if text(element, role) == "AXButton":
                label = text(element, title) or text(element, description)
                if _SHORTCUT.sub("", label.strip()) in labels:
                    return ax.AXUIElementPerformAction(element, press) == 0
            kids = copy(element, children) if depth < _DEPTH else None
            if kids and cf.CFGetTypeID(kids) == cf.CFArrayGetTypeID():
                for index in reversed(range(cf.CFArrayGetCount(kids))):
                    stack.append((cf.CFArrayGetValueAtIndex(kids, index), depth + 1))
        return False
    finally:
        for value in owned:
            cf.CFRelease(value)


def _declare(ax: ctypes.CDLL, cf: ctypes.CDLL) -> None:
    pointer = ctypes.c_void_p
    cf.CFStringCreateWithCString.restype = pointer
    cf.CFStringCreateWithCString.argtypes = [pointer, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringGetCString.argtypes = [pointer, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    cf.CFGetTypeID.argtypes = [pointer]
    cf.CFGetTypeID.restype = ctypes.c_ulong
    cf.CFStringGetTypeID.restype = ctypes.c_ulong
    cf.CFArrayGetTypeID.restype = ctypes.c_ulong
    cf.CFArrayGetCount.argtypes = [pointer]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetValueAtIndex.argtypes = [pointer, ctypes.c_long]
    cf.CFArrayGetValueAtIndex.restype = pointer
    cf.CFRelease.argtypes = [pointer]
    ax.AXUIElementCreateApplication.argtypes = [ctypes.c_int]
    ax.AXUIElementCreateApplication.restype = pointer
    ax.AXUIElementCopyAttributeValue.argtypes = [pointer, pointer, ctypes.POINTER(pointer)]
    ax.AXUIElementSetAttributeValue.argtypes = [pointer, pointer, pointer]
    ax.AXUIElementPerformAction.argtypes = [pointer, pointer]
