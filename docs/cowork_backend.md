# CoWork backend

## Summary

The layer over the CoWork driver. It reads the same case tree as the container backend,
submits each case's prompt body through the driver, grades the session document that comes
back, and writes the same `aggregate-result.json` v1 document into the same log directory. It
is reached as `cowork_evals run --cowork <path>`.

- **The split from the driver is one question**: does the statement need to know what a case
  is? Yes, and it is here. No, and it is in [cowork_driver.md](cowork_driver.md), which holds
  the transport and nothing else.
- **It does not call `claude plugin eval`.** That harness must load a plugin, and only Claude
  Code knows how. The case format is shared with it. The execution is not.
- **Grading is total.** Nothing in the grading layer raises: an unknown grader type, an
  uncompilable pattern and an unreadable file are each a failed grader carrying the reason.
- **A produced file means a file under `outputs/`.** That is the one place a produced file is
  readable from the host, and it is what a kept run's `workspace/` is copied from.
- **Nothing under the profile is written.** The traces are copied out of a session directory,
  never moved, and the session is left exactly as the application left it.
- **Skips are recorded, never silent**, and a run that reports one fails. A case this backend
  cannot run declares it, is not submitted and is counted, which is not a skip.
- **The plugin under test is not loaded.** A case path selects which cases run, not which code
  runs.
- **The suite ceiling is refused before the first submission**, not one case at a time.

Which part of the case format survives this route is [approaches.md](approaches.md), the
key-by-key rule is [running_evals.md](running_evals.md), the case format itself is
[eval_format.md](eval_format.md), and the command over it is [cli.md](cli.md). What of this is
built is the status table in [running_evals.md](running_evals.md).

## Grading the session document

The CoWork backend evaluates a case's graders, defined in
[eval_format.md](eval_format.md), against the session document defined in
[cowork_driver.md](cowork_driver.md). It takes that document and the case directory, runs on
the host inside the `cowork_evals` process, and returns one result per grader. It prints nothing, exits nothing and decides no pass or fail. It submits
nothing, so it re-runs over a stored session document for free.

| Grader        | Read from                                    |
| ------------- | -------------------------------------------- |
| `regex`       | The resolved target below                    |
| `tool_used`   | `tool_calls`, matched on name and on the JSON-encoded input |
| `tool_order`  | `tool_calls`, in call order, because `before` and `after` each take an `input_match` |
| `file_exists` | The produced-file list below, as a glob      |
| `llm`         | a judge call on `focus`, 2 of 3              |
| `baseline`    | a judge call against `baseline_file`, 2 of 3 |

Grader targets map onto the session document as `last_message` to `final_text`, `trace` to
`turns` and `tool_calls`, `files` to the produced-file list, and `{source: file, path}` to
that path under `<session_dir>/outputs/`, which is the one place a produced file is readable
from the host. `mock_calls` has no equivalent here, because the MCP servers are the real
ones.

**The produced-file list is `outputs` with its `outputs/` prefix stripped.** That prefix is
in the session document because the document names files relative to the session directory.
The backend strips it once, and every grader that names a produced file names it relative to
`outputs/`. That is what makes `path: report.md` mean here what it means under the harness,
where the created-file list is relative to the workspace. A `path` that resolves outside
`outputs/` is a failed grader carrying the reason, because the reference confines a file
target to the workspace and `outputs/` is the workspace here.

**`target: trace` renders this backend's way** and is not the harness's `trace.jsonl`: one
JSON object per line, every entry of `turns` followed by every entry of `tool_calls`. A
`regex` grader over `trace` is therefore not portable between backends. Every other target
is.

**A `regex` pattern is a JavaScript RegExp source compiled with Python's `re`.** The two
engines are not the same. The flags `i`, `m` and `s` map onto `re.I`, `re.M` and `re.S`;
`re.ASCII` is added unless the flags carry `u` or `v`, which is what makes `\d` and `\w`
ASCII-only as they are in JavaScript; and `d`, `g` and `y` are ignored, because none of them
changes what a grader reads. A named group, a lookaround or a backreference that both
engines accept behaves the same; a construct only JavaScript has does not compile, and that
is a failed grader naming the error. Every pattern in the format goes through that one
function, `input_match` on `tool_used` and `tool_order` included.

Nothing in the grading layer raises. An unknown grader type, an uncompilable pattern and an
unreadable file are each a failed grader carrying the reason.

## The judge

`llm` and `baseline` are answered by `claude -p --output-format json --model <model>
--strict-mcp-config`, with the rubric, the material and a closing instruction sent as one
text on stdin. Three votes, and the grader passes on two `PASS` answers. A reply that is
neither word is a lost vote and is not a `PASS`; three lost votes are a failed grader naming
the reason. `--strict-mcp-config` keeps the developer's own MCP servers out of a text vote.

The model is `--judge-model` where one was given and `eval.judge_model` otherwise. The
signed-in `claude` on `PATH` is the one credential route, which is why [cli.md](cli.md) makes
it part of the `--cowork` preflight. `CLAUDE_CODE_WALNUT_SPIRE` is not exported: it enables
`claude plugin eval`, and this is `claude -p`.

An `llm` grader whose file focus turns out to be an image is a grader skip, not a failure:
the harness shows the judge the image, and one text call cannot. It is detected from the
file's bytes, as the harness detects it, so it is decided after the run and not before it. It
is the one skip this backend decides after a run, and with the `mock_calls` grader skip it is
one of the only two it decides at all. Any other binary is a failed grader naming what the
file is.

## What the result document says that the reference does not

Both backends write the same v1 `aggregate-result.json`, so one verdict covers both. The
contract is additive-only, which is what permits these. Nothing else here departs from
[claude_code/plugin_eval_reference.md](claude_code/plugin_eval_reference.md).

| Field                              | On                | Is                                                      |
| ---------------------------------- | ----------------- | --------------------------------------------------------- |
| `declaredUnrunnable`, `declaredReason` | a case        | That the case carries `no-cowork`, and what the tag declares. `arms.with` is empty |
| `skipped`, `skipReason`            | a grader result   | Why that grader was not scored                           |
| `cowork.sessionDir`                | a run             | The session, which is what re-grades a stored run without submitting again, and where the run's artefacts are copied from |
| `cowork.timeoutSeconds`            | a run             | The timeout that run ran under, which is the override where one was given. It is the one place an effective value is recorded |
| `scored`                           | a grader result   | `not skipped`, widening the reference's `not withOnly` to the one other exclusion this backend has |

`withOnly` is always `false`: `ablation` is `none` here and nothing is dropped for an arm.

**This backend runs one arm, and that arm is the with-arm.** A session gets its skills from
the profile the desktop application is running, and a plugin is absent only in a profile it
was never installed into, which is why a baseline arm here would mean a second profile and a
restart between the two. What a session loads and where it loads it from is
[cowork_desktop.md](cowork_desktop.md). So `ablation` and `threshold` are constants in
`results.py` rather than settings, and `--ablation` and `--delta-threshold` are a usage error
on this backend. See [cli.md](cli.md).

**The `cowork` key is also what says which backend produced a run.** The harness writes no
such key, so its presence is the rule that decides where one run's artefacts are read from
when the traces are collected: a session directory here, and a kept sandbox there. It is the
key and never its value, because a run the driver could not start carries the key with a null
`sessionDir`. See [running_evals.md](running_evals.md).

`tracePath` is the session's transcript when the document is written, and is rewritten to the
copy under the run's log directory once that copy is made. The session itself is still named,
in `cowork.sessionDir`. That is what makes a failure line say the same thing on both backends.

**A case carries `declaredUnrunnable` and never `skipped`.** The two are different, and a
reader and the verdict both tell them apart by the field: a skip fails the run, and a declared
case is counted. This backend decides no case skip at all.

One behaviour departs as well. The four aggregates are over the cases this backend ran, so a
declared case is out of `casesTotal`, out of `casesPassed` and out of both means. `threshold`
is 0 here, so a declared case left in `casesTotal` alone would count as passed, and its 0.0
would drag `overallScore` down for a case that never ran. Nothing reads them to decide
anything: the pass and fail rules in [running_evals.md](running_evals.md) read the grader
results, `skipped` and `declaredUnrunnable`.

Two fields mean something narrower here than they do under the harness.

| Field           | Here                                                                              |
| --------------- | ----------------------------------------------------------------------------------- |
| `claudeVersion` | The host `claude --version`. No CLI ran this suite, and that version is the judge's |
| `costUsd`       | The judge spend, and nothing else. A CoWork run is billed to the account and is not observable from the host. It is never estimated |

A CoWork run writes `aggregate-result.json` and the run's artefacts under `traces/`. There is
no `report.html` on this backend, and the artefacts carry the same three names the container
backend leaves. The log layout is [running_evals.md](running_evals.md).

Skips are recorded, never silent. A grader with no equivalent is written into the result
document as skipped with the reason, and a run fails when it reports a skip, so a suite cannot
go green on CoWork by grading nothing.

A case is different. What this backend cannot run is written into the case as the `no-cowork`
tag, the validator holds the case and this backend to the same rule, and the backend reads the
tag rather than deciding anything. The reasons behind the tag are still read here, and they
are what `declaredReason` carries. A key the case leaves to its default is not one of them;
the rule and the key-by-key table are in [running_evals.md](running_evals.md).

**A `mocks/` directory is declared per case, not per directory.** The layer chain runs from
`evals/` down to the case, so a suite-wide `evals/mocks/` reaches every case in the plugin and
every one of those cases carries the tag. That is explicit where a reader is looking, and it
survives the case being moved.

## The plugin under test is not loaded

The deep link carries a prompt. It does not install a plugin, and nothing on the host writes
into the VM's configuration. A CoWork run therefore exercises the plugin set already
deployed to the signed-in account.

A case path selects which cases run. It does not select which code runs. A local edit to a
skill is invisible to this backend until it is deployed. Nothing checks it, because it is
not verifiable from the host.

## What one suite costs, and what a grader can be told here

A snapshot, captured 2026-09-09, from `tests/integration/test_cowork_backend.py` against the
`python-version` case of `plugins/smoke/`, which writes `runs: 1`.

| Measured                                    | Value                                        |
| ------------------------------------------- | ---------------------------------------------- |
| Wall clock of one case                      | 6.1 s, the run's `durationSeconds`. It runs from the audit `user` record to the collection, so it excludes the deep link, the settle and the discovery |
| Ceiling entries one suite costs             | One per run. That selection is one case at `runs: 1`, so one entry |
| `costUsd` of that suite                     | 0. The case carries no judged grader, and a CoWork run is not observable from the host |

Two facts about the grader mapping cannot be read from a file, and both were measured
against the sessions in a real profile, with one run fired to provoke what the profile did
not already show.

| Measured                                            | Value | Consequence                                   |
| --------------------------------------------------- | ----- | ----------------------------------------------- |
| A transcript carries a `Skill` `tool_use` record   | yes   | The skill-fired idiom in [eval_format.md](eval_format.md) is gradable here |
| A session writes a produced file under `outputs/`  | yes   | `file_exists`, and a `{source: file, path}` target, are gradable here |

## The ceiling over a suite

The driver refuses one submission at a time, at step 1 of its sequence; see
[cowork_driver.md](cowork_driver.md). The backend refuses a whole suite before the first
submission: it sums each case's effective run count, which is `--runs` where one was given,
the declared `runs` where the case wrote one, and 1 otherwise, adds `recent()`, and raises
code 2 when the total is above `max_runs`. A case carrying `no-cowork` submits nothing and
costs no ceiling entry.

