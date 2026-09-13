# Checks

## Summary

An assertion an author writes as code, run over what a run produced, deciding the run beside
the harness's own graders.

- **A check is one decorated function** in `checks/<name>.py` beside the case, in the
  consumer's own repository. Nothing in this package and nothing in the harness changes when
  one is added.
- **It runs on the host**, in this package's process, after the run is graded and after the
  artefacts are collected. It never enters the container and never enters the CoWork VM.
- **It asserts, it transforms and it asks a judge.** One mechanism, because all three are
  things a Python function does.
- **Its result is a grader result of type `check`** in the same `aggregate-result.json`, so a
  failed check fails the run under the condition that already fails a structural grader.
- **Its own imports are the consumer's dependency.** The CoWork wheel set does not bind it.
- **A run that kept no artefacts produces one skipped check per check**, and a skip fails the
  run.

The six grader types the format defines are fixed by a tool this repository does not own, so
an assertion outside them cannot be made: a `file_exists` grader says the spreadsheet appeared
and never what is in it. A check is that assertion. The grader types are
[eval_format.md](eval_format.md), pass and fail is
[running_evals.md](running_evals.md), and the boundary a check file sits on is
[library.md](library.md).

## The tree

A case gains one directory, beside the one it already has.

```
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md      # the harness's five types, unchanged
<plugin>/evals/<skill>/<case>/checks/<name>.py       # the author's code
```

Checks are discovered by convention. They are declared in no file: an unknown key in
`prompt.md` makes the harness refuse the case at load, and a key in `case.yaml` the harness
ignores would make the format no longer the harness's own.

`checks/` is added to a case and never replaces its `graders/`. The harness refuses a case
carrying no grader at all, measured on CLI 2.1.265 through the container: a case whose only
assertion directory is `checks/` fails to load with `invalid case.yaml: graders: Required`,
the suite writes no result document, and the command exits 1. The case never runs, so the
check never runs either.

## The function

```python
from cowork_evals.checks import Result, Run, check


@check
def totals_add_up(run: Run) -> None:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    assert book.active["D10"].value == 4200
```

`@check` takes no arguments. A check's name is `<file stem>.<function name>`, so the function
above is `assertions.totals_add_up` in every place a name appears: the result document, the
failure line and `checks.jsonl`. Every check has weight 1.

| The function            | The check                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| returns `None`          | passes                                                         |
| returns `True`          | passes                                                         |
| returns `False`         | fails                                                          |
| returns a `Result`      | is what the `Result` says                                      |
| raises                  | fails, carrying the exception's message                        |
| returns anything else   | fails, naming what it returned                                 |

`Result` carries `passed` and `explanation`, and nothing else. `explanation` is what the run's
grader entry and the `FAIL` line both print.

Nothing a check does raises out of the layer. An exception carries its message into the
explanation and its traceback into `checks.jsonl`.

### Discovery

Every `checks/*.py` of the case, in path order, and every decorated function in each, in
definition order.

| Rule                                                                     | Because                                                                 |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Each file is loaded under a module name unique to its case directory     | Two cases each holding `checks/assertions.py` would otherwise collide in `sys.modules` |
| The case's `checks/` directory is on `sys.path` while its files load      | So a check may import a sibling beside it                                  |
| A sibling imported that way is dropped from `sys.modules` afterwards      | So the next case's `helpers.py` is that case's own                       |
| A decorated function is discovered in the file that defines it, and once  | A file that imports one from a sibling gets the name it already has        |
| A file with no decorated function contributes nothing                    | A helper beside a check is a file like any other                          |

The path is off `sys.path` again once the files are loaded, so a check that imports a sibling
lazily, inside the function body, does not resolve. Import at the top of the file.

## Run

One collected run, as a check reads it.

| Field          | Is                                                                    |
| -------------- | ----------------------------------------------------------------------- |
| `workspace`    | the agent's working directory, as a path                              |
| `last_message` | the final assistant message, as text                                  |
| `trace`        | the transcript, as a path. The two backends write two formats         |
| `case_dir`     | the case directory on this host                                       |
| `run_dir`      | the collected run directory, and the judge's working directory        |
| `scratch`      | a directory a check may write into                                    |
| `index`        | which run of the case this is, 1-based, as the verdict prints it      |

`run.file(name)` resolves one name under `workspace`. A name that resolves to nothing, and a
name that leaves the workspace, each fail the check naming it.

There is no created-file list. The v1 run entry carries none, so there is nothing to read one
from on the container backend, and walking `workspace` sees more than a created-file list
does: it sees a file the run modified, which `file_exists` never does.

**A check writes to `run.scratch`, never to `run.workspace`.** The workspace is the record of
what the agent produced, and a transformation writing into it destroys that record. `scratch/`
is created before the first check of a run and is shared by every check of that run.

The two transcript formats are [running_evals.md](running_evals.md). A check that reads
`run.trace` reads whichever format the backend that produced the run wrote.

## The judge

```python
@check
def deck_is_readable(run: Run) -> Result:
    subprocess.run(["soffice", "--convert-to", "png", run.file("deck.pptx")], cwd=run.scratch)
    return run.judge("Every slide carries a title, and no text is clipped.", run.scratch)
```

`run.judge(prompt, *paths)` is `claude -p`, three votes, a majority of two, and it returns a
`Result` a check returns directly.

It is shown paths and never inlined material. A PDF, an image and a spreadsheet cannot be
shown as text, and reading a file is what the judge's `Read` tool is for. The `llm` grader
keeps inlining and is untouched: that grader matches the harness exactly so a case scores the
same on both backends, and a check is this package's own and nothing outside it defines its
behaviour.

| | The `llm` grader | `run.judge` |
| ------------------- | ---------------------------------- | ---------------------------------- |
| Is shown            | the material, as text on stdin     | the paths, and reads them itself   |
| Tools               | none                               | `Read`, `Glob`, `Grep`             |
| Working directory   | the caller's                       | the run directory                  |
| A binary focus      | a grader skip or a failed grader   | read like any other file           |
| Defined by          | the harness                        | this package                       |

A path under the run directory reaches the prompt relative to it. A path outside reaches it
absolute, and the argument list carries an `--add-dir` for it.

A call naming no path is a failed check saying so. There is no default of everything: a judge
shown the whole run directory is judging the transcript as well as the artefact.

The model is `judge.resolve_model`, the one ladder every other judge call resolves through, so
`--judge-model` beats `eval.judge_model`. There is no configuration key of the layer's own.

### What was measured

On CLI 2.1.270, `haiku`, over a text file, an 8 by 8 PNG and a one-page PDF written by the
measurement.

| Fact                                                                                         | Holds |
| ---------------------------------------------------------------------------------------------- | ----- |
| `--allowedTools Read,Glob,Grep` alone lets a non-interactive judge read a file in its working directory | yes |
| `--add-dir` alone lets it read a file outside that directory                                 | yes   |
| It reads the file rather than agreeing: the same claim inverted came back `FAIL`             | yes   |
| A tool-using judge answers with the bare word, so `judge.read_reply` reads it exactly        | yes   |

So the argument list carries no permission mode and no turn cap, and a check judge's reply is
read by the same function every other vote goes through. The CLI's own default binds the loop.

## Where it runs

A check runs on the host, in this package's process, and never inside the container or the
CoWork VM. The run has already finished and has already been graded, so nothing about the
session binds a check file: not the interpreter, not the wheel set, not the image. A check
file is under the eval path and is not code under test.

A check's own imports are the consumer's dependency, declared in the consumer's project. This
package depends on nothing a check might want. An author asserting over a spreadsheet adds
`openpyxl` to their own repository, exactly as they would for a unit test. See
[library.md](library.md).

## The run directory

A check reads the collected run directory, which is what both backends normalise to, so one
code path serves both. It writes two more names into it.

```
<log root>/<stamp>-<scope>/<plugin>/traces/<case>/run-<n>/
  trace.jsonl
  last_message.txt
  workspace/
  scratch/          # what a check wrote
  checks.jsonl      # one line per check
```

Both sit beside the three the collector left, so the `[artifacts: <dir>]` suffix on a failure
line names all five.

`checks.jsonl` carries one object per check: the name, the verdict, the explanation, the
duration, the traceback where there was one, and for each judge call the whole prompt, the
three replies and the cost. The result document's `evidence` is capped at 2000 characters, and
a person reading a failed judged check needs the whole exchange.

Under `--no-keep-traces`, and under `eval.keep_traces: false`, nothing is collected and there
is no run directory to read. Every check of that case is then a skip, and a skip fails the
run: a suite cannot go green by asserting nothing. No flag is forced and nothing new is
refused. See [cli.md](cli.md).

## What reaches the result document

| Where                        | What                                                                |
| ---------------------------- | ---------------------------------------------------------------------- |
| the case's `graders[]`       | one definition per check, `{name, type: check, weight: 1, config: {}}` |
| the run's `graders[]`        | one result per check, in the shape every grader result has          |
| the run's `score`, `passed`  | recomputed over every scored result, the checks included            |
| the case's `aggregates`      | `score` and `passRate` recomputed over the runs                     |
| the run's `judgeCostUsd`     | plus what a check judge spent                                       |
| the document's `costUsd`     | the same, so the panel and `eval.max_cost_total_usd` both see it    |
| the document's `aggregates`  | `overallScore` and `overallPassRate` recomputed over the cases      |

`casesTotal` and `casesPassed` are untouched. `--threshold` is pinned to 0, so every case
counts as passed there whatever a check said, and this package decides pass and fail.

A suite with no check anywhere leaves the document exactly as the backend wrote it. Nothing is
rewritten to say that nothing happened.

`verdict.py` needs no condition of its own. It joins a result to its definition by name and
asks whether the type is judged; `check` is not, so a failed check fails the run exactly as a
failed `regex` grader does, and the line reads `the check grader failed: <explanation>`.

Only the `with` arm is walked. The baseline arm runs without the plugin under test, so an
assertion about what the plugin produced has nothing to read there. A two-arm document's
`aggregates.delta` and its `meanDelta` are the harness's own and are not recomputed: a failed
check fails the case through its own grader result, not through the delta.

A case carrying `declaredUnrunnable` has no run and produces no check result. It is counted,
exactly as it is today.

## The validator

`checks/*.py` is Python, and the only way to know it imports is to import it. `cowork_evals
run` imports every check of every selected plugin root in its preflight, before anything runs,
and a violation exits 3.

| Rule                                                                    | Name               |
| ------------------------------------------------------------------------- | ------------------ |
| Every file under `checks/` imports                                      | `check-import`     |
| A `checks/` directory carries at least one `@check`                     | `check-empty`      |
| No two checks of one case share a name                                  | `check-duplicate`  |
| `context.add_dirs` names no path under `checks/`                        | `add-dirs-checks`  |

The last one is this repository's and is not redundant. The harness refuses the case's own
`graders/` itself, knows nothing about `checks/`, and would grant it as a fixture directory: a
case that stages its own assertions into the agent's working directory is telling the agent
what it is about to be judged on. See
[claude_code/plugin_eval_reference.md](claude_code/plugin_eval_reference.md).

A `checks/` directory holding no check asserts nothing while looking as if it does. A single
file holding none is not a violation, because a helper beside a check is a file like any
other, which is why the rule is over the directory and never over a file.

## The panel

`caseDigest` covers each `checks/*.py` after the graders. Without it, editing an assertion
would leave the `stale` column green and the panel would claim a result is current when what
it asserted has changed. See [panel.md](panel.md).

## What it costs

A check that asserts costs nothing: it is a function call on the host. A check that shells out
costs whatever it shelled out to, on the developer's machine and in the developer's time.

A check that calls `run.judge` costs three `claude -p` calls at `eval.judge_model` per call
per run. Each run of a case runs every check again, so a case at `runs: 3` carrying one judged
check costs nine. That spend reaches the run's `judgeCostUsd` and the document's `costUsd`, so
`eval.max_cost_total_usd` binds it like any other. The ceilings are
[running_evals.md](running_evals.md).

## What is not built

| Not built                                            | Because                                                                  |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| A free-form `run.ask` returning the judge's text     | A check is host code and may call `subprocess` itself. A second route to the same CLI is a split with no rule |
| A `@transform` decorator                             | A transformation that decides nothing is a function, and Python has functions |
| A weight or a name on `@check`                       | Nobody asked for either. Every check weighs 1                            |
| A configuration key of any kind                      | The judge model is `eval.judge_model`, and everything else is discovered  |
| A check on the `without` arm                         | Nothing the plugin produced is there to read                             |
| Any way to run a check inside the container or the VM | The run is graded before a check starts, and a check that ran inside the thing under test would be bound by the image wheel set for no gain |
