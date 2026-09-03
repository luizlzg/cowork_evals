# CoWork driver

Submit a prompt to a real CoWork session without a human keystroke, and collect the result
from the host filesystem. The only approach that exercises the deployed stack.

The measured application internals it couples to are in
[cowork_desktop.md](cowork_desktop.md), including the authorizations table and the coupling
list to re-probe after an update. Do not restate them here.

## Status

Not built. The design below is settled; the completion signal is measured on first use, and
the fallback is stated.

## Scope

One prompt in, one JSON document out. No graders, no case format, no pass or fail. Mapping
the result document onto grader classes needs this driver to exist first.

It does not use `claude plugin eval`: that harness must load a plugin, and only Claude Code
knows how.

## Decisions

**Session accumulation.** Every run leaves a permanent session in the signed-in account's
CoWork history. The driver never deletes anything: deleting from the profile directory is
writing into application-managed state and can corrupt a profile.

The mitigation is a ceiling and a record, not deferral. The driver refuses more than
`COWORK_MAX_RUNS` invocations per call, and appends one line per run to a run log outside
the profile: timestamp, prompt hash, session directory, exit code. That log is the only
record it owns, and it is what makes manual cleanup tractable. Removal is manual, through
the application.

**Live account exposure.** The driver drives a real signed-in account through the
organization inference gateway, with whatever MCP servers that account has. A prompt can
send mail or mutate data for real.

`scripts/prompt_lint.py` runs before every submission and refuses a prompt matching its
deny-list of mutating instructions. The driver calls it and exits 2 on refusal. There is no
flag to skip it.

The limit, stated plainly: a linter is a filter, not a sandbox. A prompt phrased around the
deny-list will execute, and nothing outside the session can restrict the session's tools.
Reads and local computation only remains a rule enforced by review as well as by the linter.

## The completion signal

The terminal `command_lifecycle` audit state is the signal. If it has not been observed,
the driver falls back to quiescence: the run is finished when no file under the session
directory has changed for `COWORK_IDLE_SECONDS`, counted only after the first assistant
output has appeared.

The fallback is a heuristic and is labelled as one in the code. It can fire during a long
pause mid-run, which is why `COWORK_IDLE_SECONDS` is raisable.

## Configuration

Environment variables with defaults. No machine fact is hardcoded.

| Variable                 | Default                | Is                                             |
| ------------------------ | ---------------------- | ---------------------------------------------- |
| `COWORK_PROFILE`         | none, required         | The Application Support profile directory name |
| `COWORK_RUN_LOG`         | `~/.cowork-runs.jsonl` | The run log, outside the profile               |
| `COWORK_MAX_RUNS`        | 10                     | Refusal ceiling per invocation                 |
| `COWORK_IDLE_SECONDS`    | 20                     | Quiescence window, fallback signal only        |
| `COWORK_SESSION_TIMEOUT` | 120                    | Wait for a session directory to appear         |
| `COWORK_RUN_TIMEOUT`     | 1800                   | Wait for the run to finish                     |

`COWORK_PROFILE` has no default on purpose. A wrong guess drives the wrong account.

The driver never writes anywhere under the profile.

## Identifying its own run

The `user` record in `audit.jsonl` carries the submitted prompt verbatim in
`message.content`. The driver compares it and refuses any session that does not match. That
is what makes a collected result attributable to a submission.

The application caps the deep link prompt at 14336 characters and truncates silently above
it, so the driver refuses a longer prompt rather than grade an altered one.

## Failure taxonomy

A grading layer has to tell these apart, so the driver exits on distinct codes and never
collapses them.

| Code | Meaning                                                    |
| ---- | ---------------------------------------------------------- |
| 0    | Run completed and was collected                            |
| 2    | Refused before submission: prompt too long, or lint failed |
| 3    | Submission failed: `open` or `osascript` returned non-zero |
| 4    | No session directory appeared within the timeout           |
| 5    | More than one session directory appeared, cannot attribute |
| 6    | A session appeared but its audit prompt does not match     |
| 7    | The run did not complete within the timeout                |
| 8    | The run completed with no assistant output                 |

A tenant that enables `disableDeepLinkRegistration` shows as exit 4. It fails closed.

## The result document

One JSON object on stdout: the prompt, its sha256, the session directory, the submitted and
collected timestamps, `final_text`, the tool calls with each result paired to its call by
`tool_use_id`, the audit records, the files under `outputs/`, and the exit code.

## Cleanup

Manual, through the application. Read the run log to find what to remove. The driver deletes
nothing, ever.
