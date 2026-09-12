---
name: cowork-ask
description: Answer a question about what a real Claude CoWork session does by submitting one prompt to one with cowork_evals ask. TRIGGER when a question is about what a live CoWork session actually does, when a claim about the product has to be confirmed rather than argued, or when a cowork_evals ask command fails.
---

# cowork_evals ask

`cowork_evals ask --cowork "<prompt>"` submits one prompt to a real CoWork session, waits,
and prints the answer. It runs no eval: no case tree, no grader, no result document, no verdict
and no run directory.

Use it when the answer is a fact about the deployed product. Do not use it to check anything
a file already states, and do not use it in place of `cowork_evals run`.

Run `cowork_evals docs` for the documentation this command ships. Every rule below is in one
of those files, and the name in the right column is the file that owns it.

| Question                                       | Read                   |
| ---------------------------------------------- | ---------------------- |
| The verb, its options and its exit codes       | `docs cli`             |
| What the driver does, and what it refuses      | `docs cowork_driver`   |
| What the application writes, and where         | `docs cowork_desktop`  |
| What the CoWork backend can and cannot honour  | `docs approaches`      |
| What a session may import                      | `docs runtime`         |

## The command

```bash
cowork_evals ask --cowork "Reply with the single word: ready"
cowork_evals ask --cowork --dry-run "..."      # the deep link and the ceiling. Spends nothing
cowork_evals ask --cowork --json "..."         # the session document instead of the text
cowork_evals ask --cowork --session <dir>      # a session already on disk. Submits nothing
```

The answer is stdout. The session directory, the assistant turn count, the tool names, the
outputs and the driver log are stderr, so a redirect captures the answer alone.

## What it costs

One ask costs a VM boot, the keyboard for the length of the run because the submission is a
synthetic Return to the frontmost window, and one submission against `cowork.max_runs`.

Ask once. `--dry-run` first when the prompt is long or built by hand, and `--session` to
re-read a session already on disk instead of submitting it again.

## The one rule that makes an answer evidence

Ask the session to **do** the thing, and read what it did. What a session says about its own
configuration is not evidence: a model reports its tools, its permissions and its environment
from its prompt and from habit, and both go stale.

| Question                      | Ask                                                       | Read                    |
| ----------------------------- | --------------------------------------------------------- | ----------------------- |
| Can it write a file?          | write one, at a named path, with named contents           | `outputs` in the footer |
| Can it run a shell command?   | run one whose output cannot be guessed                    | `tools`, then the text  |
| Which tools does it have?     | use the tool                                              | `tools` in the footer   |
| Does a skill fire?            | give it the request the skill's own description triggers on | `tool_calls` under `--json`. There is no `Skill` tool in a session: it reads `SKILL.md` over the mount, which `docs cowork_desktop` records |

`--json` prints the whole session document, and `tool_calls` in it carries each call's input
and its result. That is what a claim about a tool is checked against.

A refusal is a result. Record what the session refused and how, and do not re-ask a different
way to get a different answer.

## When it fails

`cowork_evals ask` exits 3 when the preflight is unmet or the driver refused before
submitting, and the message names what to fix. Exit 1 is everything else the driver raised,
and the driver's codes are in `cowork_evals docs cowork_driver`.

`cowork_evals check --cowork` reports what the backend is missing. The authorizations it
cannot report, including the macOS Accessibility grant, are in
`cowork_evals docs cowork_desktop`.
