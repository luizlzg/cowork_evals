# Checks

## Summary

A check is a Python function you write beside an eval case. It receives the files one
execution of that case produced, and it passes or fails. Its verdict counts exactly as a
grader's does, so a failed check fails the case.

### The problem it solves

An eval case is scored by graders. A grader is a Markdown file under the case's `graders/`
directory, and its `type:` is one of these six, which is every type the `claude plugin eval`
harness defines:

| Type          | Asserts                                                     |
| ------------- | ----------------------------------------------------------- |
| `regex`       | a pattern matches the answer text, the trace or a file      |
| `tool_used`   | a named tool was called, so many times                      |
| `tool_order`  | one tool call came before another                           |
| `file_exists` | the agent created a file matching a glob                    |
| `llm`         | a judge model read some text and voted on a rubric          |
| `baseline`    | a judge model compared this trajectory against a recorded one |

The fields each one takes are [eval_format.md](eval_format.md). What matters here is that the
list is closed. The harness is a Claude Code command this repository does not own and cannot
extend, and it rejects a grader whose `type:` is not one of the six.

So an assertion that is not one of those six cannot be written at all. The assertion that
comes up most often, and does not fit, is one about the contents of a file the agent produced.

Take an example. A plugin has a skill that builds spreadsheets, and the author writes an eval
case for it. The prompt asks the agent to produce a file named `totals.xlsx`, and what the
author wants to assert is that the total in cell D10 came out as 4200. Three of the six types
can look at a produced file, and each of the three stops short of that:

| The grader                                 | What it does with `totals.xlsx`                                  |
| ------------------------------------------ | ------------------------------------------------------------------- |
| `file_exists`                              | reports that the file is there, and nothing about what is inside it |
| `regex` with `target: {source: file, ...}` | reads the file as UTF-8 text. A `.xlsx` is a ZIP archive, so it is not text and the grader fails on the read |
| `llm` with `focus: {source: file, ...}`    | shows a judge model that same text, so a binary is a failed grader or a skipped one |

The limit is not only that the file is binary. Even on a file that is plain text, a regular
expression cannot compute: it cannot open a workbook, sum a column, evaluate a formula, or
compare the result against 4200.

So the case can assert that `totals.xlsx` was created, and nothing else about it. It passes
when D10 holds the wrong number. It passes again when the file is corrupt and no application
can open it. The eval is green and it checked nothing.

A check is how the author writes the assertion they wanted. They open the workbook in Python,
in their own repository, and assert the total. That exact check is under
[The function](#the-function) below, and a whole case with checks is under
[A worked example](#a-worked-example).

### How it works

One execution of a case is a *run*. Each run leaves three things on the host: its transcript,
its final assistant message, and the working directory the agent wrote into. That happens on
both backends, under the same three names, and it happens after the harness has finished
grading. See [running_evals.md](running_evals.md).

A check reads those. `cowork_evals run` grades a case as it always did, collects the run's
files, and then imports the case's `checks/*.py` and calls each decorated function once per
run, handing it an object that names the workspace, the final message and the transcript. The
function asserts whatever it likes. Its verdict is appended to the same
`aggregate-result.json` the graders wrote into, as a grader result of type `check`, and pass
and fail read it there. Nothing else in the pipeline changes.

### What follows from that

- **A check runs on the host, not in the session.** The host is whatever machine you ran
  `cowork_evals` on. The run is over and already graded before a check starts, so a check may
  import anything your own project declares and shell out to anything that machine has:
  `openpyxl`, `pypdf`, `soffice`. The CoWork wheel set binds the code under test and does not
  bind a check. See [library.md](library.md).
- **One mechanism, not three.** Asserting, converting a file to something readable, and asking
  a model about it are all things a Python function does, so all three are one decorated
  function. There is no separate transform step and no separate judge step.
- **A check can ask a model, and it is shown files rather than text.** `run.judge` grants the
  judge `Read`, `Glob` and `Grep` and names the paths, so a PDF, an image and a spreadsheet
  are all judgeable. The `llm` grader cannot do that, and is untouched.
- **A failed check fails the run** under the condition that already fails a `regex` grader.
  The verdict gained no rule for it.
- **Checks need the collected files, so `--no-keep-traces` gives them up.** With nothing
  collected each check is a skip, and a skip fails the run. A suite cannot go green by
  asserting nothing.
- **A check is added to a case, never in place of its graders.** The harness refuses a case
  carrying no grader at all.

A worked example is below: a case in this repository, its three files, the command that runs
it, and what that command printed.

## The tree

A case that has checks carries one more directory, beside the `graders/` it already has.

```
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md      # the harness's own, unchanged
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

## A worked example

`plugins/smoke/evals/plugin/checked-file` is a case with checks, in this repository, and it
runs. Every block below is that case's own file or that run's own output, verbatim. The
failure line is wrapped to fit; it is one line.

```
plugins/smoke/evals/plugin/checked-file/prompt.md
plugins/smoke/evals/plugin/checked-file/graders/writes-written-txt.md
plugins/smoke/evals/plugin/checked-file/checks/assertions.py
```

`prompt.md` asks for a file:

```markdown
---
name: checked-file
description: A check reads the file the run wrote, and decides on what is inside it.
tags: [plugin]
plugins: ["../../.."]
runs: 1
---

Write the single word WRITTEN into a file named `written.txt` in the working directory. Reply
with the word WRITTEN and nothing else.
```

`graders/writes-written-txt.md` says the file appeared, which is all a grader type can say:

```markdown
---
type: file_exists
path: written.txt
---
```

`checks/assertions.py` says what is inside it. One check passes and one fails, so the case
shows both:

```python
from cowork_evals.checks import Result, Run, check


@check
def the_file_says_written(run: Run) -> None:
    assert run.file("written.txt").read_text(encoding="utf-8").strip() == "WRITTEN"


@check
def the_file_is_a_workbook(run: Run) -> Result:
    return Result(passed=False, explanation="written.txt is not a workbook")
```

Run it:

```sh
cowork_evals run --docker plugins/smoke --case checked-file --runs 1
```

The harness grades the case and reports it green, because its own grader passed. The layer
then runs the two checks, and the verdict is this package's:

```
CASE          SCORE PASS% RUNS COST    NOTES
checked-file  1.00  100%  1    $0.06

1 case(s) · 7s · $0.06
Report: /work/logs/report.html
FAIL smoke/checked-file: run 1: assertions.the_file_is_a_workbook: the check grader failed:
  written.txt is not a workbook [artifacts: logs/evals/20260913-131331-smoke/smoke/traces/checked-file/run-1]
4 found, 1 picked, 1 ran, 0 passed, 0 declared unrunnable, overall score 0.67
```

The exit code is 1. The harness's own table and the verdict under it disagree because they are
two things: the first is the harness reporting what it graded, and the second is this package
deciding the run over everything that graded it. `Report: /work/logs/report.html` is the
harness's report, named by the path it had inside the container; the file is beside
`aggregate-result.json` on the host. The `[artifacts: ...]` directory holds what the run left and what
the checks left:

```
traces/checked-file/run-1/trace.jsonl
traces/checked-file/run-1/last_message.txt
traces/checked-file/run-1/workspace/
traces/checked-file/run-1/scratch/
traces/checked-file/run-1/checks.jsonl
```

`checks.jsonl`, verbatim:

```json
{"name": "assertions.the_file_says_written", "passed": true, "explanation": "the check raised nothing", "durationSeconds": 0.0014283749987953342}
{"name": "assertions.the_file_is_a_workbook", "passed": false, "explanation": "written.txt is not a workbook", "durationSeconds": 4.334004188422114e-06}
```

What that case is the fixture for is `plugins/README.md`.

## The function

A check is a function marked with the `@check` decorator. It takes one argument, a `Run`
object describing the execution it is judging, and it returns nothing when it passes. This is
the shape a check usually has, an assertion about a file the run produced:

```python
import openpyxl

from cowork_evals.checks import Run, check


@check
def totals_add_up(run: Run) -> None:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    assert book.active["D10"].value == 4200
```

`openpyxl` is the consumer's own dependency, declared in the consumer's project. This package
does not depend on it.

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

Discovery imports every `checks/*.py` of the case, in path order, and collects every decorated
function in each file, in the order the file defines them.

| Rule                                                                     | Because                                                                 |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Each file is loaded under a module name unique to its case directory     | Two cases each holding `checks/assertions.py` would otherwise collide in `sys.modules` |
| The case's `checks/` directory is on `sys.path` while its files load      | So a check may import a sibling beside it                                  |
| A sibling imported that way is dropped from `sys.modules` afterwards      | So the next case's `helpers.py` is that case's own                       |
| A decorated function is discovered in the file that defines it, and once  | A file that imports one from a sibling gets the name it already has        |
| A file with no decorated function contributes nothing                    | A helper beside a check is a file like any other                          |

The path is off `sys.path` again once the files are loaded, so a check that imports a sibling
lazily, inside the function body, does not resolve. Import at the top of the file.

## The Run object

Each check is called with one `Run`. It describes one execution of the case: where that
execution's files are on this host, what the agent said last, and which of the case's runs
this is. Every field is something `traces.collect` left under the run directory, so the same
fields are there whichever backend produced the run.

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

A check may ask a model. Some things are not decidable in code: whether a slide is clipped,
whether a chart is readable, whether prose answers the question. `run.judge` asks `claude -p`
about files and returns a verdict a check returns directly.

```python
import subprocess

from cowork_evals.checks import Result, Run, check


@check
def deck_is_readable(run: Run) -> Result:
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "png", run.file("deck.pptx")],
        cwd=run.scratch,
        check=True,
    )
    return run.judge("Every slide carries a title, and no text is clipped.", run.scratch)
```

`soffice` is the host's, like `openpyxl` above. A check is host code, so it may shell out to
anything the machine running `cowork_evals` has.

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
CoWork VM. The host is the machine `cowork_evals` was run on: a laptop, a desktop, or a
server, and nothing about a check prefers one over another.

A check adds no requirement to that machine beyond Python 3.10, which the package already
needs, and whatever the check itself imports. What does constrain the machine is the backend,
and it constrains it the same way with checks as without: `--docker` needs a reachable Docker
daemon and runs headless, so a build server is fine, and `--cowork` needs macOS, the desktop
application and the keyboard, so it has no headless route at all. See
[approaches.md](approaches.md).

The run has already finished and has already been graded, so nothing about the session binds a
check file: not the interpreter, not the wheel set, not the image. A check file sits under the
eval path and is not code under test.

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

The layer rewrites the plugin's `aggregate-result.json` after the backend wrote it. The
changes are these, and nothing else in the document moves.

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

Each of these was considered and rejected. None of them is pending.

| Not built                                            | Because                                                                  |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| A free-form `run.ask` returning the judge's text     | A check is host code and may call `subprocess` itself. A second route to the same CLI is a split with no rule |
| A `@transform` decorator                             | A transformation that decides nothing is a function, and Python has functions |
| A weight or a name on `@check`                       | Nobody asked for either. Every check weighs 1                            |
| A configuration key of any kind                      | The judge model is `eval.judge_model`, and everything else is discovered  |
| A check on the `without` arm                         | Nothing the plugin produced is there to read                             |
| Any way to run a check inside the container or the VM | The run is graded before a check starts, and a check that ran inside the thing under test would be bound by the image wheel set for no gain |
