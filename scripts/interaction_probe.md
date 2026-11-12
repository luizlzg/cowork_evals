# Interaction probe for cowork_evals

`interaction_probe.py` records what Cowork writes to its session files while it waits for you, a
question it asks mid-run or an approval box, and checks which key answers it. It presses the key
itself: you do not touch anything until the end. Each scenario takes one to two minutes and writes
one log file to send back.

## Before you start

- The Claude desktop app open and signed in, with Cowork available, and the Microsoft 365
  connector connected. The question and folder scenarios need no plugin. For `connector_*`,
  **disable the `second-brain` plugin in Cowork first**: its send gate refuses the call before
  Cowork's own box can appear. Cowork raises no box for a shell command.
- This repository on branch `feat/interaction-probe`, with `uv sync` run once, and a
  `cowork_evals.yaml` that names your profile (`cowork.profile`, for example `Claude-3p`).
- On macOS, the terminal you run it from allowed under System Settings, Privacy and Security,
  Accessibility.

## Run it

From the repository folder, in a terminal (PowerShell on Windows):

```sh
uv run python scripts/interaction_probe.py question
uv run python scripts/interaction_probe.py questions
uv run python scripts/interaction_probe.py multiselect
uv run python scripts/interaction_probe.py folder_allow
uv run python scripts/interaction_probe.py folder_deny
uv run python scripts/interaction_probe.py connector_allow
uv run python scripts/interaction_probe.py connector_deny
```

Run them all, in any order. Since the Cowork update of 10 Nov 2026 the digit no longer answers a
question on macOS (it types into the card's "Something else" field), so there the three question
scenarios press the options through accessibility. On Windows they still press the digit: if
the log shows the digit typed into the text field, tell us.

Add `--delay <seconds>` to wait longer than 2 s before the first press, and `--config <path>` if your `cowork_evals.yaml` is in another folder, and `--key <key>` to try
another key than the scenario's.

| Scenario       | What Cowork is asked                                          | Key pressed |
| -------------- | ------------------------------------------------------------- | ----------- |
| `question`     | Ask you red or blue with its question tool, then write a file | Windows `1`; macOS `ax_option` |
| `questions`    | Two questions in one question call, colour and size           | Windows `1_each`: `1` once per question; macOS `ax_option` |
| `multiselect`  | One question where several colours can be chosen              | Windows `1_approve`: `1`, then `approve` to send; macOS `ax_option` |
| `folder_allow` | Connect your Downloads folder and count its files             | `ax_allow`  |
| `folder_deny`  | The same                                                      | `esc`       |
| `connector_allow` | Create a calendar event with the Microsoft 365 connector (Cowork's own box). **Creates a real 15-minute event tomorrow at 09:00: delete it** | Windows `approve`; macOS `ax_allow` |
| `connector_deny` | The same, denied: no event | Windows `esc`; macOS `ax_deny` |

| Key        | macOS      | Windows    |
| ---------- | ---------- | ---------- |
| `approve`  | Cmd+Return | Ctrl+Enter |
| `esc`      | Escape     | Escape     |
| `enter`    | Return     | Enter      |
| `1` to `9` | the digit  | the digit  |
| `ax_option` | chooses the question card's first option, then Submit or Next question, one step per press | not available |
| `ax_deny`  | presses the box's Deny button through the Accessibility API | not available |
| `ax_dump`  | writes the question card's accessibility tree to the log, presses nothing | not available |
| `try_keys` | presses 1, Return, Down+Return, Space, Tab+Return in turn on one request | the same |
| `ax_allow` | presses the box's Allow button through the Accessibility API | presses it through UI Automation (Windows PowerShell) |
| `ax_focus_enter` | not available | gives the Allow button the keyboard through UI Automation, then Enter |

`approve` allows once on the tool boxes (bash, Microsoft 365 connector). A digit is not used to
approve: on the Windows connector box `2` is "Allow for this task", which skips later checks in
the same chat. The folder box has no shortcut: no key allows it while the keyboard is in the
message field (measured on macOS and Windows), so `folder_allow` presses its Allow button
instead. On Windows it invokes only an Allow button that has a Deny button beside it, so a chat
or a banner called "Allow" is not pressed. If it does not allow the box, try `--key ax_focus_enter`.

## What happens

1. A box asks for the keyboard (the driver's usual consent). Then the probe opens a new Cowork
   chat and sends the prompt. **Keep Claude in front and do not touch the keyboard or mouse**
   until the terminal asks you something: if another window is in front when a key is due, the
   probe stops and presses nothing.
2. Two seconds after Cowork asks, the probe presses the key, without bringing Claude to the front
   again (that would move the keyboard to the message field, away from the box). While the box
   still stands it presses again every 3 seconds, four times at most; a lone digit is pressed
   once, since a second `1` unticks a multi-choice option. A button press through accessibility
   types nothing, so it does not need Claude in front.
3. The run ends when Cowork records it as completed, or 20 seconds after a deny with nothing
   more written (a denied folder box ends the turn that way, with no reply). Then the terminal
   asks what Claude shows. Type a few words and press Enter. It
   prints the log path.

## What the log contains

- The OS and Python versions, the scenario, its prompt and key. On Windows also the executable
  path and the window class of the Claude window.
- Each new line of the session's files: the record type, its field names, and for messages the
  first 200 characters of text, the tool name and input, and tool results.
- Field names only for other records, such as a plugin's injected context.
- Files added or grown under the session folder, by relative path and size.
- Each key pressed, how long after the request, and your answer at the end.
- Times in UTC to the millisecond, from this computer's clock. A time inside a tool result (for
  example a server's) comes from another clock and can differ by a second or two.

Your user name, home folder and computer name are replaced. Read the log before sending it.
