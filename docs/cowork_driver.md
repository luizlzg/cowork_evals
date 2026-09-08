# CoWork driver

Submit a prompt to a real CoWork session without a human keystroke, and collect the result
from the host filesystem. The only approach that exercises the deployed stack.

The measured application internals it couples to are in
[cowork_desktop.md](cowork_desktop.md), including the deep link route, the session
filesystem layout, the authorizations table and the coupling list to re-probe after an
update. Do not restate them here.

Design. Nothing here is built, and neither is the CoWork backend above it. What is built is
the status table in [running_evals.md](running_evals.md).

This page is the contract the driver is built to: the sequence, the command surface, the
configuration, the reading rules, the result document, the grader mapping and the exit
codes. Every statement is a design decision, not a measurement, except where it cites
[cowork_desktop.md](cowork_desktop.md). The completion signal is measured on first use and
the fallback is stated below.

## Scope

The driver is the transport. One prompt in, one JSON document out. It holds no case format,
no graders and no pass or fail.

The CoWork backend is the layer above it and holds all three. It reads the same case tree as
every other backend, submits each case's prompt body through this driver, grades the result
document with the CoWork grader below, and writes the same `aggregate-result.json` v1
document into the same log directory. It is reached as `cowork_evals run --cowork <path>`;
see [cli.md](cli.md), [running_evals.md](running_evals.md), and
[approaches.md](approaches.md) for which part of the case format survives this route.

It does not use `claude plugin eval`: that harness must load a plugin, and only Claude Code
knows how. The case format is shared with that harness. The execution is not.

Attachments and plugin staging are out of scope. The router reads `file` and `folder`
parameters, but the driver does not send them. That is why `context.add_dirs` and
`context.scaffold_script` cannot be honoured on this backend.

## The command surface

The driver is `cowork_evals.cowork`, library code like the rest of the package: standard
library only, one module. It runs on the host and never under the CoWork mirror, because it
drives the desktop application and reads host paths, and nothing it does belongs to a
session. It is therefore not bound to 3.10; see [library.md](library.md).

It is not a verb of the consumer command. The `--cowork` backend calls it, and
`python -m cowork_evals.cowork` reaches the three commands below directly when a run has to
be taken apart by hand.

| Command                            | Does                                 | Prints                | Returns when              |
| ---------------------------------- | ------------------------------------ | --------------------- | ------------------------- |
| `run <prompt>`                     | Submit, wait for the run, collect    | The result document   | The run is finished       |
| `submit <prompt>`                  | Submit only                          | The session directory | The session is attributed |
| `collect <session_dir>`            | Parse one session already on disk    | The result document   | Immediately               |

```sh
python -m cowork_evals.cowork run 'Reply with exactly: PONG' > result.json
python -m cowork_evals.cowork submit 'Reply with exactly: PONG'
python -m cowork_evals.cowork collect "$session_dir" > result.json
```

Every function that reads a session takes the sessions root or the session directory as an
argument. Nothing derives a path from the environment at read time, so the tests drive the
discovery, attribution and collection code over fixture directories.

| Flag              | On           | Default  | Is                                             |
| ----------------- | ------------ | -------- | ---------------------------------------------- |
| `--surface NAME`  | run, submit  | `cowork` | Deep link `surface` parameter. `""` omits it   |
| `--idle SECONDS`  | run          | env      | Overrides `COWORK_IDLE_SECONDS` for this call  |
| `--timeout SECS`  | run          | env      | Overrides `COWORK_RUN_TIMEOUT` for this call   |

`collect` is the only command that needs no authorization beyond read access to the
profile. It runs over a recorded session directory, so it is the command the tests exercise
and the one to call again when a stored run has to be re-parsed.

A calling script pairs `submit` with a later `collect` when it must not hold a process open
for the length of an agentic run. Everything else uses `run`.

The exit code is the failure taxonomy below, on every command.

## The sequence

`run` performs these steps in order. Each step names the exit code it produces on failure.

| # | Step                | Does                                                                                | Fails as |
| - | ------------------- | ----------------------------------------------------------------------------------- | -------- |
| 1 | Refuse              | Check the configuration, the rate ceiling, the 14336 cap, and the prompt linter     | 2        |
| 2 | Record the baseline | List the session directories that already exist                                     |          |
| 3 | Fire the deep link  | `open claude://claude.ai/new?q=<prompt>&surface=<surface>`                          | 3        |
| 4 | Settle              | Sleep `COWORK_SETTLE_SECONDS` while the window navigates and focuses the composer   |          |
| 5 | Submit              | Activate the application and send a synthetic Return through `osascript`            | 3        |
| 6 | Discover            | Poll for a session directory that is not in the baseline                            | 4, 5     |
| 7 | Attribute           | Compare the recorded prompt with the submitted one                                  | 6        |
| 8 | Wait                | Block until the completion signal fires                                             | 7        |
| 9 | Collect             | Build the result document from the session directory                                | 8        |

Step 5 sends the keystroke to the frontmost application. Nothing may steal focus between
steps 3 and 5.

Step 6 identifies a session by structure, not by name: a directory holding an `audit.jsonl`
three levels below the sessions root. New sessions are the set difference against the
baseline. More than one means another session was created while this one ran, and the run
cannot be attributed: exit 5, not a guess.

Step 7 tolerates a session directory that exists before its `user` audit record is written.
It keeps polling until the record appears or the discovery timeout expires.

## The completion signal

The terminal `command_lifecycle` audit state is the signal. If it has not been observed,
the driver falls back to quiescence: the run is finished when no file under the session
directory has changed for `COWORK_IDLE_SECONDS`.

Quiescence counts only after the run has demonstrably started, which is a `started`
lifecycle state or a first assistant turn in the transcript. Without that condition the
idle window accrues during VM boot and an empty session is reported as a finished run.

The fallback is a heuristic and is labelled as one in the code. It can fire during a long
pause mid-run, which is why `COWORK_IDLE_SECONDS` is raisable.

## Configuration

Environment variables with defaults. No machine fact is hardcoded. They are read from the
environment and from `.env`, like every other variable this command takes. See
[library.md](library.md).

| Variable                 | Default                | Is                                             |
| ------------------------ | ---------------------- | ---------------------------------------------- |
| `COWORK_PROFILE`         | none, required         | The Application Support profile directory name |
| `COWORK_RUN_LOG`         | `~/.cowork-runs.jsonl` | The run log, outside the profile               |
| `COWORK_MAX_RUNS`        | 50                     | Submissions allowed in the trailing 24 hours   |
| `COWORK_SETTLE_SECONDS`  | 3                      | Deep link navigation before the Return         |
| `COWORK_IDLE_SECONDS`    | 20                     | Quiescence window, fallback signal only        |
| `COWORK_SESSION_TIMEOUT` | 120                    | Wait for a session directory to appear         |
| `COWORK_RUN_TIMEOUT`     | 1800                   | Wait for the run to finish                     |

`COWORK_PROFILE` has no default on purpose. A wrong guess drives the wrong account. An
unset or unreadable one is refused at step 1, as exit 2, before anything is fired.

`COWORK_SESSION_TIMEOUT` is the observed VM boot in
[cowork_desktop.md](cowork_desktop.md) with margin. `COWORK_SETTLE_SECONDS` is not measured
and is conservative.

The driver never writes anywhere under the profile. The run log is the only file it owns.

## Identifying its own run

The `user` record in `audit.jsonl` carries the submitted prompt verbatim in
`message.content`. The driver compares it and refuses any session that does not match. That
is what makes a collected result attributable to a submission.

The application caps the deep link prompt at 14336 characters and truncates silently above
it, so the driver refuses a longer prompt rather than grade an altered one.

## Reading a session

Rules the reader follows. The record shapes they act on are in
[cowork_desktop.md](cowork_desktop.md).

- The run is the newest top level transcript by modification time under
  `.claude/projects/session/`. Files under `subagents/` are recorded by path and are never
  merged into it.
- An unparsable line is skipped. Both `audit.jsonl` and the transcript are appended while
  the run is live, so the last line can be partial.
- `message.content` is a string or a list of blocks. Both carry turn text.
- A `tool_result` attaches to its `tool_use` by `tool_use_id`. Positional pairing is wrong:
  results arrive in later records, and parallel calls interleave.
- A `tool_result` whose call is absent from this transcript belongs to a subagent and is
  dropped.
- `final_text` is the last assistant text turn. A run with none exits 8.

## The result document

One JSON object on stdout.

| Key                     | Is                                                                     |
| ----------------------- | ---------------------------------------------------------------------- |
| `prompt`                | The submitted prompt                                                   |
| `prompt_sha256`         | Its digest, the join key to the run log                                |
| `session_dir`           | Absolute path of the attributed session                                |
| `submitted_at`          | Timestamp of the deep link                                             |
| `collected_at`          | Timestamp of the collection                                            |
| `transcript`            | Path of the main transcript                                            |
| `other_transcripts`     | Paths of the remaining top level transcripts                           |
| `subagent_transcripts`  | Paths under `subagents/`                                               |
| `audit_prompt`          | The prompt as recorded in `audit.jsonl`                                |
| `lifecycle`             | Every `command_lifecycle` state, in order                              |
| `turns`                 | Role and text per turn                                                 |
| `tool_calls`            | Id, name, input, MCP attribution, timestamp, and the paired result     |
| `tool_names`            | Tool names in call order, for a grader that only asks what fired       |
| `final_text`            | The last assistant text turn                                           |
| `outputs`               | Files under `outputs/`, relative to the session directory              |
| `exit_code`             | The taxonomy code                                                      |

## Grading the result document

The CoWork grader evaluates a case's graders, defined in
[eval_format.md](eval_format.md), against the document above. It takes the result document
and the case directory as arguments, runs on the host inside the `cowork_evals` process, and
prints one result per grader. It submits nothing, so it re-runs over a stored document for free.

| Grader        | Read from                                    |
| ------------- | -------------------------------------------- |
| `regex`       | `final_text`, or `turns` for target `trace`  |
| `tool_used`   | `tool_calls`, matched on name and input      |
| `tool_order`  | `tool_names`, in call order                  |
| `file_exists` | `outputs`, as a glob                         |
| `llm`         | a judge call on the same target, 2 of 3      |
| `baseline`    | a judge call against `baseline_file`, 2 of 3 |

Grader targets map onto the document as `last_message` to `final_text`, `trace` to `turns`
and `tool_calls`, `files` to `outputs`, and `{source: file, path}` to that file under the
session directory. `mock_calls` has no equivalent here, because the MCP servers are the real
ones.

Skips are recorded, never silent. A grader with no equivalent, and a case whose frontmatter
writes out a key this backend cannot honour, are both written into the result document as
skipped with the reason. A key the case leaves to its default is not a skip; the rule and
the key-by-key table are in [running_evals.md](running_evals.md). The gate fails a run that
reports a skip, so a suite cannot go green on CoWork by grading nothing.

## Decisions

**Session accumulation.** Every run leaves a permanent session in the signed-in account's
CoWork history. The driver never deletes anything: deleting from the profile directory is
writing into application-managed state and can corrupt a profile.

The mitigation is a rate ceiling and a record, not deferral.

The ceiling counts submissions, because a runaway loop is what fills an account history. It
is enforced against the run log: before submitting, `run` and `submit` count the log entries
whose timestamp falls in the trailing 24 hours, and refuse with exit 2 when that count is
already `COWORK_MAX_RUNS`. Every submission is logged, successful or not, so a failing loop
is throttled by the same ceiling as a working one. `collect` never checks it. The window is
fixed at 24 hours; only the count is configurable, and there is no flag to skip it.

The default of 50 is a working day of development, and it is a ceiling, not a budget. A
sweep that needs more raises the variable deliberately.

The record is the run log itself: one line per submission, holding the timestamp, the prompt
hash, the session directory and the exit code. That log is the only file the driver owns,
and it is what makes manual cleanup tractable. Removal is manual, through the application.

**Live account exposure.** The driver drives a real signed-in account through the
organization inference gateway, with whatever MCP servers that account has. A prompt can
send mail or mutate data for real.

A prompt linter runs before every submission and refuses a prompt that instructs a mutation.
It is a module the driver imports, not a command, so it has no entry point of its own. The driver exits 2 on refusal. There is no flag to skip it.

### The deny-list

The rule the linter enforces: **read anything, mutate nothing outside the session.** Writing
a file inside the session is not a mutation. Sending mail, moving a calendar, editing a
document or pushing a commit is.

The linter splits the prompt into sentences on `.`, `;`, `?`, `!` and newline. A sentence is
refused when it matches a rule below and names no session-local target. A prompt is refused
when any of its sentences is. Every pattern is a case-insensitive regular expression on word
boundaries, so the rules are mechanical and the tests are one prompt per rule.

| Rule       | Patterns                                                                            |
| ---------- | ------------------------------------------------------------------------------------ |
| `send`     | `send`, `reply to`, `forward`, `post to`, `publish`, `share`, `notify`, `invite`     |
| `create`   | `create`, `add`, `schedule`, `book`, `draft`, `file a`, `submit`                     |
| `modify`   | `update`, `edit`, `rename`, `move`, `assign`, `enable`, `disable`, `mark`            |
| `destroy`  | `delete`, `remove`, `cancel`, `decline`, `archive`, `trash`, `revoke`, `unsubscribe` |
| `deploy`   | `install`, `deploy`, `commit`, `push`, `merge`, `upload`, `rm -`, `mv `, `git push`, `curl -X (POST|PUT|PATCH|DELETE)` |
| `transact` | `approve`, `pay`, `purchase`, `order a`, `place an order`, `authorize`, `sign`       |

A sentence naming `outputs/`, `/sessions/`, `/tmp`, `TMPDIR` or `the session` is exempt, so
`Write the summary to outputs/summary.md` passes.

Each pattern is the mutating verb in the phrasing a prompt actually uses, not the bare word,
wherever the bare word has a common read-only sense. `reply to` is a rule and `reply with`
is not, so `Reply with exactly: PONG` passes. `order a` is a rule and `in order to` is not.
Words with no usable verb sense in a prompt are left out entirely: `set`, `clear`, `change`,
`close`, `resolve`, `confirm` and `message` all refuse more read-only prompts than mutating
ones, and are not in the list.

The list grows when a mutating prompt gets through. It is a deny-list, so it is never
complete.

The limit: a linter is a filter, not a sandbox. It reads English, so it is
blunt in both directions. It refuses harmless prompts that happen to use a listed verb, and
the fix is to rephrase or split the sentence, because there is no skip flag. It passes a
mutating prompt that avoids every listed verb, and nothing outside the session can restrict
the session's tools. Reads and local computation only remains a rule enforced by review as
well as by the linter.

## Failure taxonomy

A grading layer has to tell these apart, so the driver exits on distinct codes and never
collapses them.

| Code | Meaning                                                    |
| ---- | ---------------------------------------------------------- |
| 0    | Run completed and was collected                            |
| 2    | Refused before submission: configuration, rate ceiling, prompt too long, or lint |
| 3    | Submission failed: `open` or `osascript` returned non-zero |
| 4    | No session directory appeared within the timeout           |
| 5    | More than one session directory appeared, cannot attribute |
| 6    | A session appeared but its audit prompt does not match     |
| 7    | The run did not complete within the timeout                |
| 8    | The run completed with no assistant output                 |

A missing Accessibility grant shows as exit 3, with `osascript` error 1002 on stderr. A
tenant that enables `disableDeepLinkRegistration` shows as exit 4. It fails closed.

These are the module's codes and no operator sees them. The `--cowork` backend maps them
onto the four codes the command exits with, and that mapping is in [cli.md](cli.md).

## Cleanup

Manual, through the application. Read the run log to find what to remove. The driver deletes
nothing, ever.
