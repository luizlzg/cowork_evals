# CoWork driver

Submit a prompt to a real CoWork session without a human keystroke, and collect the result
from the host filesystem. The only approach that exercises the deployed stack.

The measured application internals it couples to are in
[cowork_desktop.md](cowork_desktop.md), including the deep link route, the session
filesystem layout, the authorizations table and the coupling list to re-probe after an
update. Do not restate them here.

What of this is built is the status table in
[running_evals.md](running_evals.md).

This file is the contract the driver is built to: the sequence, the API, the configuration,
the reading rules, the session document, the grader mapping and the failure taxonomy. Every
statement is a design decision, not a measurement, except where it cites
[cowork_desktop.md](cowork_desktop.md).

## Scope

The driver is the transport. One prompt in, one session document out. It holds no case
format, no graders and no pass or fail.

The CoWork backend is the layer above it and holds all three. It reads the same case tree as
every other backend, submits each case's prompt body through this driver, grades the session
document with the CoWork grader below, and writes the same `aggregate-result.json` v1
document into the same log directory. It is reached as `cowork_evals run --cowork <path>`;
see [cli.md](cli.md), [running_evals.md](running_evals.md), and
[approaches.md](approaches.md) for which part of the case format survives this route.

It does not use `claude plugin eval`: that harness must load a plugin, and only Claude Code
knows how. The case format is shared with that harness. The execution is not.

Attachments and plugin staging are out of scope. The router reads `file` and `folder`
parameters, but the driver does not send them. That is why `context.add_dirs` and
`context.scaffold_script` cannot be honoured on this backend.

## The API

The driver is a library and nothing else. It has no entry point, no console script and no
`__main__`. It runs on the host and never under the CoWork mirror, because it drives the
desktop application and reads host paths, and nothing it does belongs to a session. It is
therefore not bound to 3.10; see [library.md](library.md).

Two modules, and PyYAML.

| Module                     | Holds                                                       |
| -------------------------- | ------------------------------------------------------------ |
| `cowork_evals.config`      | `cowork_evals.yaml`, the frozen `Config` and its sections, and `CoWorkError` |
| `cowork_evals.cowork`      | `CoWork`, the driver                                        |

`Config`, its three sections, `CoWork` and `CoWorkError` are the whole public surface, and
they are re-exported from `cowork_evals`. There is no module level function, so a caller
passes a configuration once and calls methods on the object that holds it. A `CoWork` takes
the `cowork:` section, `CoWorkSection`, and never the whole file.

```python
from cowork_evals import Config, CoWork, CoWorkError

cw = CoWork()  # reads cowork_evals.yaml
cw = CoWork(profile="...", max_runs=10)  # the same, with overrides
cw = CoWork(Config.load().cowork)  # from a configuration already loaded
cw = CoWork.from_file("other.yaml")

doc = cw.run("Reply with exactly: PONG")  # submit, wait, collect
```

| Method                              | Does                                        | Returns                          | Fires |
| ----------------------------------- | --------------------------------------------- | --------------------------------- | ----- |
| `from_file(path, **overrides)`      | Builds from a named configuration file      | A `CoWork`                       | no    |
| `run(prompt)`                       | `submit`, then `wait`, then `collect`       | The session document             | yes   |
| `submit(prompt)`                    | Steps 1 to 7 of the sequence                | The attributed session directory | yes   |
| `wait(session_dir)`                 | Step 8, the completion signal               | The same directory               | no    |
| `collect(session_dir, prompt=None)` | Step 9, reading one session already on disk | The session document             | no    |
| `sessions(root=None)`               | Every session directory under a root        | Paths, sorted                    | no    |
| `history(run_log=None)`             | The run log                                 | One dictionary per line, oldest first | no |
| `deep_link(prompt)`                 | Builds the URL, percent-encoding the prompt | The URL                          | no    |

Rules that hold for all of them:

- Construction resolves the configuration and validates nothing else. It reads no session,
  starts no process and raises only on a malformed configuration file. A missing `profile`
  is refused by the first method that needs one, so `CoWork().collect(archived_dir)` works
  on a machine that has no CoWork.
- A failure raises `CoWorkError`, which carries the taxonomy code below as `.code` and the
  session directory as `.session_dir` when one is known. No method returns an error code,
  calls `sys.exit`, or prints.
- `config` is a frozen dataclass and is not reassigned. A different configuration is a
  different `CoWork`.
- `sessions` and `history` default to the configured paths and take an argument to read
  somewhere else, which is what the tests use.
- There is no test seam. `open` and `osascript` are run directly, no mock, fake, stub or
  patch is used anywhere in this repository, and no parameter exists to inject one. What a
  test cannot reach without the application, the live test reaches by firing one. See
  [../tests/README.md](../tests/README.md).
- `collect` takes `prompt` when the caller knows what was submitted, which fills `prompt`
  and `prompt_sha256`. Without it those two come from the audit record.
- Every public callable is fully type hinted, and the session document is JSON-serializable:
  dictionaries, lists, strings, numbers and `None`, with every path a string.

`collect` is the only method that needs no authorization beyond read access to the profile.
It runs over a recorded session directory, so it is what the tests exercise and what is
called again when a stored run has to be re-parsed.

A calling script pairs `submit` with a later `collect` when it must not hold a process open
for the length of an agentic run. Everything else uses `run`.

## The sequence

`run` performs these steps in order. Each step names the taxonomy code it raises on failure.

| # | Step                | Does                                                                                | Fails as |
| - | ------------------- | ----------------------------------------------------------------------------------- | -------- |
| 1 | Refuse              | Check the configuration, the rate ceiling and the prompt cap                        | 2        |
| 2 | Record the baseline | List the session directories that already exist                                     |          |
| 3 | Fire the deep link  | `open claude://claude.ai/new?q=<prompt>&surface=<surface>`                          | 3        |
| 4 | Settle              | Sleep `settle_seconds` while the window navigates and focuses the composer          |          |
| 5 | Submit              | Activate the application and send a synthetic Return through `osascript`            | 3        |
| 6 | Discover            | Poll for a session directory that is not in the baseline                            | 4, 5     |
| 7 | Attribute           | Compare the recorded prompt with the submitted one                                  | 6        |
| 8 | Wait                | Block until the completion signal fires                                             | 7        |
| 9 | Collect             | Build the session document from the session directory                               | 8        |

Step 5 sends the keystroke to the frontmost application. Nothing may steal focus between
steps 3 and 5.

Step 6 identifies a session by structure, not by name: a directory holding an `audit.jsonl`
three levels below the sessions root. New sessions are the set difference against the
baseline. More than one means another session was created while this one ran, and the run
cannot be attributed: code 5, not a guess.

Step 7 tolerates a session directory that exists before its `user` audit record is written.
It keeps polling until the record appears or the discovery timeout expires.

## The completion signal

The `completed` `command_lifecycle` audit state is the signal.
[cowork_desktop.md](cowork_desktop.md) measures it. No other terminal state has been seen,
so a failed or cancelled command has an unknown state name, and the fallback stays.

The fallback is quiescence: the run is finished when no file under the session directory has
changed for `idle_seconds`.

Quiescence counts only after the run has demonstrably started, which is a `started`
lifecycle state or a first assistant turn in the transcript. Without that condition the
idle window accrues during VM boot and an empty session is reported as a finished run.

The fallback is a heuristic, is labelled as one in the code, and logs a warning when it
fires. It can fire during a long pause mid-run, which is why `idle_seconds` is raisable.

## Configuration

The `cowork:` section of `cowork_evals.yaml`, in the working directory. That file is the
only configuration route, and the sections beside this one belong to other readers; see
[library.md](library.md). No machine fact is hardcoded, and the driver reads no environment
variable.

```yaml
cowork:
  profile: <the Application Support profile directory name>   # required
  surface: cowork
  settle_seconds: 3
  session_timeout: 120
  idle_seconds: 20
  run_timeout: 1800
  max_runs: 50
  run_log: ~/.cowork-runs.jsonl
  log_dir: logs
```

| Key               | Default                | Is                                             |
| ----------------- | ---------------------- | ---------------------------------------------- |
| `profile`         | none, required         | The Application Support profile directory name |
| `surface`         | `cowork`               | Deep link `surface` parameter. `""` omits it   |
| `settle_seconds`  | 3                      | Deep link navigation before the Return         |
| `session_timeout` | 120                    | Wait for a session directory to appear         |
| `idle_seconds`    | 20                     | Quiescence window, fallback signal only        |
| `run_timeout`     | 1800                   | Wait for the run to finish                     |
| `max_runs`        | 50                     | Submissions allowed in the trailing 24 hours   |
| `run_log`         | `~/.cowork-runs.jsonl` | The run log, outside the profile               |
| `log_dir`         | `logs`                 | Diagnostic logs. `null` turns them off         |

The loading rules are [library.md](library.md), which owns the file. Two are the driver's
own: a file named to `Config.load` or `CoWork.from_file` must exist, so a mistyped path is
never a silent set of defaults, and an override passed to the `CoWork` constructor beats
the file.

`profile` has no default on purpose. A wrong guess drives the wrong account. An unset or
unreadable one is refused at step 1, as code 2, before anything is fired. A bare name
resolves under `~/Library/Application Support/`. An absolute path is taken as it stands,
which is how a test and a developer point the driver at a profile elsewhere.

`session_timeout` is the observed VM boot in [cowork_desktop.md](cowork_desktop.md) with
margin. `settle_seconds` is not measured and is conservative.

`cowork_evals.yaml` names a profile, which is an identifier, so it is git-ignored. See the
public repository rule in [../README.md](../README.md).

The driver never writes anywhere under the profile. The two log files below are the only
files it owns.

## Logging

Two files, and they are not the same thing.

| File                                          | Is                                                    | Lifetime            |
| ---------------------------------------------- | ------------------------------------------------------ | ------------------- |
| `<log_dir>/<yyyymmdd-hhmmss>-cowork_evals.log` | What the driver did: the link fired, the session found, the signal seen, the failure raised | One per firing call |
| `run_log`, `~/.cowork-runs.jsonl`              | One JSON line per submission. The rate ceiling counts it | Append only, forever |

The run log cannot be per-run, because the ceiling counts the submissions in the trailing 24
hours. It stays in the home directory, because the ceiling protects one CoWork account and
an account is not per-project.

The diagnostic log is written by `run` and `submit` only, through a handler on the
`cowork_evals` logger. Every `CoWorkError` that leaves one of them is logged once, where the
handler is opened, rather than at the step that raised it. The library never configures the
root logger and never adds a handler twice. `log_dir: null` turns the file off, and the logger then carries whatever handler the
caller attached. Two calls in the same second would share one name, so the second gets a
counter suffix.

## Identifying its own run

The driver compares the prompt recorded in `audit.jsonl` against the one it submitted, and
refuses any session that does not match. That the record carries the prompt verbatim is
measured in [cowork_desktop.md](cowork_desktop.md), and the comparison is what makes a
collected result attributable to a submission.

The driver refuses a prompt longer than the deep link cap
[cowork_desktop.md](cowork_desktop.md) measures, rather than fire one and grade an altered
prompt.

## Reading a session

Rules the reader follows. The record shapes they act on are in
[cowork_desktop.md](cowork_desktop.md).

- The run is the newest top level transcript by modification time under
  `.claude/projects/session/`. Files under `subagents/` are recorded by path and are never
  merged into it.
- An unparsable line is skipped. Both `audit.jsonl` and the transcript are appended while
  the run is live, so the last line can be partial.
- Both forms `message.content` takes are read for turn text.
- A `tool_result` is paired to its `tool_use` by id, never by position: results arrive in
  later records, and parallel calls interleave.
- A `tool_result` whose call is absent from this transcript belongs to a subagent and is
  dropped.
- Turns are read from `user` and `assistant` records only. Every other record type is
  ignored, because [cowork_desktop.md](cowork_desktop.md) measures that set as open. A
  thinking block is not read as turn text.
- `final_text` is the last assistant text turn. A run with none raises code 8.
- A session directory with no transcript directory yet is tolerated, and raises code 8 for
  the same reason.

## The session document

One dictionary, and it holds exactly these keys.

| Key                     | Is                                                                     |
| ----------------------- | ---------------------------------------------------------------------- |
| `prompt`                | The submitted prompt                                                   |
| `prompt_sha256`         | Its digest, the join key to the run log                                |
| `session_dir`           | Absolute path of the attributed session                                |
| `submitted_at`          | Timestamp of that same record, when the prompt reached the application |
| `collected_at`          | Timestamp of the collection                                            |
| `transcript`            | Path of the main transcript                                            |
| `other_transcripts`     | Paths of the remaining top level transcripts                           |
| `subagent_transcripts`  | Paths under `subagents/`                                               |
| `audit_prompt`          | The prompt as recorded in the first `user` record of `audit.jsonl`     |
| `lifecycle`             | Every `command_lifecycle` state name, in order                         |
| `turns`                 | Role and text per turn                                                 |
| `tool_calls`            | Id, name, input, MCP attribution, timestamp, and the paired result     |
| `tool_names`            | Tool names in call order, for a grader that only asks what fired       |
| `final_text`            | The last assistant text turn                                           |
| `outputs`               | Files under `outputs/`, relative to the session directory              |
| `log_file`              | The diagnostic log of the call that produced it, or `null`             |

## Grading the session document

The CoWork grader evaluates a case's graders, defined in
[eval_format.md](eval_format.md), against the document above. It takes the session document
and the case directory as arguments, runs on the host inside the `cowork_evals` process, and
prints one result per grader. It submits nothing, so it re-runs over a stored session
document for free.

| Grader        | Read from                                    |
| ------------- | -------------------------------------------- |
| `regex`       | `final_text`, or `turns` and `tool_calls` for target `trace` |
| `tool_used`   | `tool_calls`, matched on name and input      |
| `tool_order`  | `tool_names`, in call order                  |
| `file_exists` | `outputs`, as a glob                         |
| `llm`         | a judge call on the same target, 2 of 3      |
| `baseline`    | a judge call against `baseline_file`, 2 of 3 |

Grader targets map onto the session document as `last_message` to `final_text`, `trace` to
`turns` and `tool_calls`, `files` to `outputs`, and `{source: file, path}` to that file
under the session directory. `mock_calls` has no equivalent here, because the MCP servers
are the real ones.

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
whose timestamp falls in the trailing 24 hours, and refuse with code 2 when that count is
already `max_runs`. Every submission is logged, successful or not, so a failing loop is
throttled by the same ceiling as a working one. A refusal at step 1 has fired nothing and is
not logged. `collect` never checks it.

The line is written after the sequence returns or raises, so a process killed between the
deep link and that write leaves a fired submission the ceiling never counts. Observed once,
2026-09-08. Nothing inside the library closes that window, because the line cannot be
written before the thing it records.

The window is fixed at 24 hours; only the count is configurable, and there is no way to
skip it.

The default of 50 is a working day of development, and it is a ceiling, not a budget. A
sweep that needs more raises `max_runs` deliberately.

The record is the run log itself: one line per submission, holding the timestamp, the prompt
hash, the session directory and the outcome, which is `submitted` or `failed:<code>`. It is
what makes manual cleanup tractable. Removal is manual, through the application.

**Live account exposure.** The driver drives a real signed-in account through the
organization inference gateway, with whatever MCP servers that account has. A prompt can
send mail or mutate data for real.

## Failure taxonomy

A grading layer has to tell these apart, so `CoWorkError.code` is one of these and never
collapses two of them. These are not exit codes. The library exits nothing, and a command
line over it maps them onto its own.

| Code | Meaning                                                    |
| ---- | ---------------------------------------------------------- |
| 2    | Refused before submission: configuration, rate ceiling, or prompt too long |
| 3    | Submission failed: `open` or `osascript` returned non-zero |
| 4    | No session directory appeared within the timeout           |
| 5    | More than one session directory appeared, cannot attribute |
| 6    | A session appeared but its audit prompt does not match     |
| 7    | The run did not complete within the timeout                |
| 8    | The run completed with no assistant output                 |

A run that completed and was collected raises nothing.

A missing Accessibility grant shows as code 3, with `osascript` error 1002 on stderr. A
tenant that enables `disableDeepLinkRegistration` shows as code 4. It fails closed.

These are the library's codes and no operator sees them. The `--cowork` backend maps them
onto the four codes the command exits with, and that mapping is in [cli.md](cli.md).

## Cleanup

Manual, through the application. Read the run log to find what to remove. The driver deletes
nothing, ever.
