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

### What this means in practice

- **A check runs on the host, not in the session.** The host is whatever machine you ran
  `cowork_evals` on. The eval is over and already graded before a check starts, so a check may
  import anything your own project declares and shell out to anything that machine has:
  `openpyxl`, `pypdf`, `soffice`. The wheel set that binds a skill running in a CoWork session
  does not bind a check. See [library.md](library.md).
- **A check can ask a model, and it is shown files rather than text.** `run.judge` hands the
  judge the paths and the `Read` tool, so a PDF, an image and a spreadsheet can all be judged.
  The `llm` grader inlines the file as text and therefore cannot.
- **A failed check fails the case**, and prints a `FAIL` line naming the check, the reason and
  the directory holding the run's files.
- **A check cannot crash the run.** An assertion that fails, an exception, a file that is not
  there and a check file that will not import are each a failed check carrying the reason.
- **Checks need the run's collected files**, so `--no-keep-traces` and `eval.keep_traces:
  false` turn every check into a skip, and a skip fails the run. A suite cannot go green by
  asserting nothing.
- **A check is added to a case, never in place of its graders.** The harness refuses a case
  carrying no grader at all.

## Writing one

Three steps. There is nothing to register and no key to add to any case file.

**1. Make the directory.** A case that has checks carries one more directory, beside the
`graders/` it already has:

```
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md      # the harness's own, unchanged
<plugin>/evals/<skill>/<case>/checks/<name>.py       # your code
```

Keep the `graders/` directory. The harness refuses a case that carries no grader at all, so a
case whose only assertion directory is `checks/` never loads and never runs. `checks/` is
added to a case, never in place of its graders.

**2. Write the function.** Any file name works. Import the decorator, mark a function with it,
and take one argument:

```python
# evals/spreadsheets/monthly-totals/checks/assertions.py
import openpyxl

from cowork_evals.checks import Run, check


@check
def totals_add_up(run: Run) -> None:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    assert book.active["D10"].value == 4200
```

`run.file("totals.xlsx")` is the file the agent produced, as a path. Assert whatever you like
about it. If the assertion holds the check passes; if it raises the check fails and the
message reaches the failure line.

`openpyxl` is your dependency, not this package's. A check runs on the host after the eval has
finished, so add whatever you import to your own project exactly as you would for a unit test.

**3. Run the case as usual.** No new flag, no new verb:

```sh
cowork_evals run --docker <plugin>/evals/spreadsheets/monthly-totals
```

The harness grades the case, the run's files are collected, and then every `@check` in
`checks/` runs once per run. A failed check fails the case and the command exits 1.

Two things happen automatically and are worth knowing before you hit them. `cowork_evals run`
imports every check file during its preflight, so a syntax error or a missing import stops the
command with exit 3 before anything spends money. And a check needs the run's collected files,
so `--no-keep-traces` turns every check into a skip, which fails the run.

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

## The check function

`Writing one` above is the short version. This is every rule the decorator and the function
follow.

`@check` takes no arguments. There is no name parameter and no weight parameter: a check's
name is `<file stem>.<function name>`, so `totals_add_up` in `checks/assertions.py` is
`assertions.totals_add_up` everywhere a name appears, and every check has weight 1.

A check may return nothing, or say what it decided:

| The function            | The check                                                      |
| ----------------------- | ---------------------------------------------------------------- |
| returns `None`          | passes                                                         |
| returns `True`          | passes                                                         |
| returns `False`         | fails                                                          |
| returns a `Result`      | is what the `Result` says                                      |
| raises                  | fails, carrying the exception's message                        |
| returns anything else   | fails, naming what it returned                                 |

`Result` carries two fields, `passed` and `explanation`, and nothing else. Use it when the
reason matters to whoever reads the failure:

```python
from cowork_evals.checks import Result, Run, check


@check
def totals_add_up(run: Run) -> Result:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    total = book.active["D10"].value
    return Result(passed=total == 4200, explanation=f"D10 is {total}")
```

`explanation` is what the `FAIL` line prints, what the result document records, and what
`checks.jsonl` keeps. A check that raises instead gets the exception's message there, and its
traceback in `checks.jsonl`.

Nothing a check does can stop the command. Every failure mode above is a failed check carrying
its reason, and the rest of the suite goes on.

### Several files, and helpers

Split checks across as many files under `checks/` as you like. Every `*.py` in the directory
is imported, in path order, and every decorated function in each file is collected in the
order that file defines them. That order is the order they run in and the order they appear in
the result.

A check file may import a helper module sitting beside it, because the `checks/` directory is
on `sys.path` while the files load:

```python
from helpers import expected_total  # checks/helpers.py, beside this file
```

Import it at the top of the file. The directory comes off `sys.path` once loading is done, so
an import inside a function body runs too late and fails.

A file under `checks/` that has no `@check` in it is a helper and nothing else. It is not an
error. What is an error is a `checks/` directory in which no file anywhere has a check: that
directory asserts nothing while looking as if it does, and the preflight says so.

Two cases may each have a `checks/assertions.py` without colliding: each file is loaded under
a module name unique to its own case directory, and a helper one of them imported is dropped
afterwards, so the next case's `helpers.py` is that case's own.

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

To find out what the agent produced, walk `run.workspace` yourself. There is no list of
created files on the `Run`: the result document carries none on the container backend, so
there would be nothing to build one from. Walking the directory also finds a file the agent
modified rather than created, which `file_exists` never sees.

**A check writes to `run.scratch`, never to `run.workspace`.** The workspace is the record of
what the agent produced, and a transformation writing into it destroys that record. `scratch/`
is created before the first check of a run and is shared by every check of that run.

The two transcript formats are [running_evals.md](running_evals.md). A check that reads
`run.trace` reads whichever format the backend that produced the run wrote.

## The judge

Some things are not decidable in code: whether a slide is clipped, whether a chart is
readable, whether prose answers the question. `run.judge(prompt, *paths)` asks a model. It
runs `claude -p` three times, takes the majority of the three votes, and returns a `Result`,
so a check can return it straight back.

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

That check does two things a grader cannot: it converts the deck to images with a tool on the
host, and then asks a model about the images. `soffice` is the host's, like `openpyxl` in
`Writing one`. A check is ordinary Python, so it may shell out to anything that machine has.

The judge is never handed the file's text. It is handed the path and the tools to open it,
which is what makes a binary judgeable at all. The `llm` grader works the other way and is
unchanged by any of this:

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

## Common mistakes

Each of these is silent or confusing the first time it happens.

| What you did                                              | What happens                                                       |
| ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| Put `checks/` on a case and deleted its `graders/`        | The case does not load at all. The harness refuses a case with no grader, so the suite writes no result and the command exits 1 |
| Ran with `--no-keep-traces`                               | Every check is a skip, and a skip fails the run. There is nothing collected to check |
| Wrote a `checks/` directory whose files have no `@check`  | The preflight refuses the tree with exit 3. A directory that asserts nothing looks like one that asserts something |
| Imported a helper inside the function body                | `ModuleNotFoundError`. The `checks/` directory is on `sys.path` only while the files load, so import at the top |
| Wrote into `run.workspace`                                | The workspace is the record of what the agent produced, and you have just edited it. Write to `run.scratch` |
| Called `run.judge` on a case at `runs: 3`                 | Three judge calls per run, nine in total. Every check runs again for every run of the case |
| Expected a check to run on the `without` arm              | It does not. `--ablation with-without` runs the baseline arm with no plugin loaded, and checks run on the with-arm only |

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

If you went looking for one of these, it is not there and is not coming. Each was considered
while the layer was designed.

| You might expect                                     | It is not there because                                                  |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| A `@transform` decorator, to convert a file before asserting on it | Converting a file is something a Python function does, and a check is a Python function. Call `subprocess` and then assert, in the same check |
| A `run.ask` that returns the judge's answer as text  | Same reason. A check may run `claude -p` itself if it needs something `run.judge` does not give it |
| A `name=` or `weight=` argument on `@check`          | Nobody asked for either. The name is the file and function, and every check weighs 1 |
| A configuration key for the layer                    | There is nothing to configure. The judge model is `eval.judge_model`, and the rest is discovered from the tree |
| Checks on the baseline arm of `--ablation with-without` | That arm runs with no plugin loaded, so nothing the plugin produces exists there to assert on |
| A way to run a check inside the container or the VM  | The eval is finished and graded before a check starts. Running one inside the thing under test would bind it to the CoWork wheel set and buy nothing |
