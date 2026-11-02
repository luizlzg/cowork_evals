# Interaction probe for cowork_evals

`interaction_probe.py` records what Cowork writes to its session files while it waits for you: a
question it asks mid-run, or an Allow/Deny box. The driver needs this to answer them and to tell
"waiting" from "finished". Each scenario takes two to five minutes and writes one log file to send
back.

## Before you start

- The Claude desktop app open and signed in, with Cowork available.
- The second-brain plugin installed in Cowork (the `deny` and `allow` scenarios use its send check).
- This repository on branch `feat/cowork-interactions`, with `uv sync` run once, and a
  `cowork_evals.yaml` that names your profile (`cowork.profile`, for example `Claude-3p`).

## Run it

Run each scenario from the repository folder, in a terminal (PowerShell on Windows):

```sh
uv run python scripts/interaction_probe.py question
uv run python scripts/interaction_probe.py deny
uv run python scripts/interaction_probe.py allow
```

Add `--config <path>` if your `cowork_evals.yaml` is in another folder.

| Scenario   | What Cowork is asked                                           | Key it offers to press |
| ---------- | -------------------------------------------------------------- | ---------------------- |
| `question` | Ask you red or blue with its question tool, then write a file  | `1`, the first option  |
| `deny`     | Run a `curl` POST to Microsoft Graph, which an approval box stops | `esc`, Deny         |
| `allow`    | The same command                                               | `approve`, Allow       |

`approve` is Cmd+Return on macOS (measured) and Ctrl+Enter on Windows (a guess: if it does not
allow, try another key and say which one worked). The `curl` carries no token, so even after Allow
nothing changes: Graph answers 401.

## What happens on screen

1. A box asks for the keyboard (the driver's usual consent). Then the probe opens a new Cowork
   chat and sends the prompt. Hands off the keyboard and mouse while it does.
2. When Cowork has been quiet for 10 seconds, the terminal asks what Claude shows. Look at Claude,
   then click back into the terminal and type a short answer. For an Allow/Deny box, include each
   button's label and its number.
3. The terminal asks which key to press. Enter takes the scenario's key; type `esc`, `approve` or a digit if the
   box numbers differ, or `none` to stop. The probe brings Claude to the front and presses it.
   Hands off again.
4. This repeats until the run ends. At the end it asks what Claude shows, and prints the log path.

If something other than Claude is in front when it is about to press a key, it stops and presses
nothing.

## What the log contains

- The OS and Python versions, the scenario and its prompt.
- Each new line of the session's files: the record type, its field names, and for messages the
  first 200 characters of text, the tool name and input, and tool results.
- Field names and sizes only for other records, such as a plugin's injected context.
- Files added or grown under the session folder, by relative path and size.
- Your answers and the keys pressed.

Your user name, home folder and computer name are replaced. Read the log before sending it.
