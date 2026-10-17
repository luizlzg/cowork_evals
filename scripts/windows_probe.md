# Windows probe for cowork_evals

`windows_probe.py` checks whether `cowork_evals` can drive Cowork on this PC. It takes about three
minutes and writes one log file to send back.

## Before you start

- The Claude desktop app open and signed in, with Cowork available.
- Python 3.8 or newer: `py --version` in PowerShell prints it. If it does not, install Python from
  the Microsoft Store or the company software portal. Nothing else is needed.

## Run it

1. Save `windows_probe.py` in a folder, for example `Downloads`.
2. Open PowerShell in that folder: in File Explorer, type `powershell` in the address bar and
   press Enter.
3. Run `py windows_probe.py` (or `python windows_probe.py`).
4. Follow what it prints. When it asks a question, answer `y` or `n` in the PowerShell window and
   press Enter there.
5. At the end it prints the path of `windows_probe_<date>-<time>.log`. Send back only that file.

## What it does on screen

1. Opens a new Cowork chat with `cowork_evals probe - DO NOT SEND` in the message box. **Do not
   press Enter in Claude and do not click Send.**
2. Switches from PowerShell to Claude twice.
3. Clears Claude's message box and types `probe typed`.

Do not touch the keyboard or mouse while it says so. It never presses Enter in Claude, so nothing
is sent. At the end, delete the text in the message box and close that chat.

## What the log contains

- Windows and Python versions.
- Where Claude keeps its sessions, how many there are, and the field names of the first lines of
  the newest session's log. No chat, message or file content.
- The title of the Claude window and whether the probe could bring it to the front and type
  into it.
- Your answers.

Your user name, home folder and computer name are replaced by `%USERNAME%`, `%USERPROFILE%` and
`%COMPUTERNAME%`. The log is plain text: open it in Notepad to check it before sending.
