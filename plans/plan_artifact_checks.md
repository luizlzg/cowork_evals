# Artifact checks

Branch: `feat/artifact-checks`.

## What we are trying to do

**The problem.** An eval here can assert only what `claude plugin eval`'s five grader types
can express: a regular expression over text, a tool was called, two calls happened in order,
a file was created, or a judge model read some text. That vocabulary is fixed by a tool this
repository does not own and cannot extend. Anything an author needs to assert that does not
fit one of the five cannot be made, and the case runs green having checked nothing.

For example, a skill writes `totals.xlsx`, `deck.pptx` or `report.pdf`, which is a common
case. The only available assertion is that the file appeared. So the right file with the
wrong content in it scores what a correct one scores, and so does a corrupted file no
application can open.

**What we want.** An author who can write code can express any assertion about what a run
produced, and that assertion decides pass and fail beside the harness's own graders. The
assertion is written by the person who needs it, in their own repository, without a change to
this package and without a change to the harness.

**Where it sits.** After the run is graded, on either backend. `--docker` grades through
`claude plugin eval` and `--cowork` grades through this package's own backend, and both keep
doing exactly what they do now. This layer runs after whichever of them graded, over what the
run produced, and adds its assertions to the same result. A case that passed below can fail
here.

This repository builds the mechanism and writes no eval for a shipped plugin:
`docs/library.md`.

## Reference

`pydantic-evals`, from the `pydantic-ai` project, solves the same shape of problem, and its
concepts are where this design starts: `Dataset`, `Case`, `Evaluator`, `EvaluatorContext`,
how a custom evaluator is registered, and how results are scored and reported.

The package is not a dependency, and decision D1 says why. What is taken is the shape of one
custom evaluator: a function that receives a context object describing one execution and
returns a verdict. `Evaluator.evaluate(ctx)` is `check(run)` here.

## The shape

A case gains one directory, beside the one it already has.

```
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md      # the harness's five types, unchanged
<plugin>/evals/<skill>/<case>/checks/<name>.py       # the author's code
```

**A check runs on the developer's laptop, in this package's process.** It never enters the
container and never enters the CoWork VM. It is the first row of the three kinds of code in
`CLAUDE.md`, not the second: the run is over before a check starts, and what a check reads is
what that run left on the host. So a check may import anything the consumer's own environment
carries, and the image wheel set does not bind it. `soffice` and `openpyxl` in the example
below are the laptop's.

One check is one decorated function. It asserts, it transforms, and it asks a judge, because
all three are things a Python function does.

```python
from cowork_evals.checks import check, Run


@check
def totals_add_up(run: Run) -> None:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    assert book.active["D10"].value == 4200


@check
def deck_is_readable(run: Run):
    subprocess.run(["soffice", "--convert-to", "png", run.file("deck.pptx")], cwd=run.scratch)
    return run.judge("Every slide carries a title, and no text is clipped.", run.scratch)
```

## Decisions

Each one is a decision this plan is executed under, and none of them is open.

| #  | Decision                                                                                  | Why                                                                                          |
| -- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| D1 | `pydantic-evals` is not a dependency. The concepts are rebuilt in one module               | The framework carries its own dataset format and its own report. Both would be a second case format and a second result document, against `CLAUDE.md` |
| D2 | Checks are discovered by convention, in `checks/`, and are declared in no file             | An unknown key in `prompt.md` makes the harness refuse the case at load, and a key in `case.yaml` the harness ignores would make the format no longer the harness's own |
| D3 | One mechanism, not three. Asserting, transforming and judging are one function             | A transformation that decides nothing is a function, and Python has functions. A split with no rule is a defect |
| D4 | A check result is a grader result of type `check` in the run's `graders[]`                | `verdict._judge_grader` joins a result to its definition by name and asks whether the type is judged. `check` is not, so a failed check fails the run with no new condition anywhere |
| D5 | `run.judge` takes paths, never inlined material                                            | A PDF, an image and a spreadsheet cannot be shown as text. The judge is Claude Code, and reading a file is what its `Read` tool is for |
| D6 | The `llm` grader keeps inlining and is untouched                                            | It is the harness's grader, and `grader.py` and `judge.py` match the harness exactly so a case scores the same on both backends. A check is this package's own and nothing outside it defines its behaviour. That is the rule the two sides of the split are decided by |
| D7 | `@check` takes no arguments. A check's name is `<file stem>.<function name>`               | A name parameter and a weight parameter are features nobody asked for. Every check has weight 1 |
| D8 | A check runs over the collected run directory, after `traces.collect`                     | Both backends normalise to the same three names there, so one code path serves both |
| D9 | Under `--no-keep-traces` a check is a skip, and a skip fails the run                       | There is nothing for it to read. The existing rule is that a skip fails the run, so a suite cannot go green by asserting nothing. No flag is forced and no new refusal is invented |
| D10 | A check writes to `run.scratch`, never to `run.workspace`                                 | The workspace is the record of what the agent produced, and a transformation writing into it destroys that record |
| D11 | The full judge prompt and the three replies go to `checks.jsonl` in the run directory      | The document's `evidence` is capped at 2000 characters. A person reading a failed check needs the whole exchange |
| D12 | `panel._defining` hashes `checks/*.py`                                                     | Without it, editing an assertion leaves the panel's `stale` column green, and the panel claims a result is current when what it asserted has changed |
| D13 | A check runs on the host, in this package's process, and never inside the container or the CoWork VM | The run has already finished and has already been graded. A check reads what it left on the host, so nothing about the session binds it: not the interpreter, not the wheel set, not the image |
| D14 | A check's own imports are the consumer's dependency, declared in the consumer's project | This package depends on nothing a check might want. An author who asserts over a spreadsheet adds `openpyxl` to their own repository, exactly as they would for a unit test |
| D15 | `Run` carries no created-file list. A check walks `run.workspace`                        | The v1 run entry carries no such list, so there is nothing to read one from on the container backend. Walking the workspace is also more than `file_exists` can see, which counts a created file and never a modified one |
| D16 | The check judge writes no turn cap and no permission mode beyond its grant              | A cap is a restriction nobody asked for. The CLI's own default binds the loop |
| D17 | The check judge's model is `judge.resolve_model`, so `--judge-model` beats `eval.judge_model` | It is the one ladder every other judge call already resolves through, and a second route would be a second source for one value |

## What changes

| File                                  | Change                                                                              |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| `src/cowork_evals/checks.py`          | New. `Run`, `Result`, `@check`, discovery, execution, and the document and directory it writes |
| `src/cowork_evals/judge.py`           | A second argument list and a second material rule, for the check judge alone        |
| `src/cowork_evals/cases.py`           | `Case` carries the case's checks, read the way it reads graders                     |
| `src/cowork_evals/validate.py`        | Import every check file, refuse `checks/` in `context.add_dirs`, refuse a duplicate check name |
| `src/cowork_evals/panel.py`           | `_defining` hashes `checks/*.py`                                                    |
| `src/cowork_evals/cli.py`             | One call in `_each_plugin`, after `traces.collect`                                  |
| `src/cowork_evals/verdict.py`         | Nothing                                                                             |
| `src/cowork_evals/results.py`         | Nothing. `checks.py` writes into the document `results.py` defines                  |
| `cowork_evals.yaml`                   | Nothing. The judge model is `eval.judge_model`, and no key is added                 |

## Phases

Work one box, verify it, tick it, commit. Do not batch ticks.

### Phase 1: the check layer

- [x] `src/cowork_evals/checks.py`, with `Run`, `Result` and the `@check` decorator.
- [x] `Run` carries `workspace`, `last_message`, `trace`, `case_dir`, `run_dir`, `scratch`
      and `index`, and the method `file(name)`. There is no `files`, for the reason in D15.
- [x] `Result` carries `passed` and `explanation`, and nothing else. `explanation` is what
      the run's grader entry and the `FAIL` line both print.
- [x] Discovery: every `checks/*.py` of a case, in path order, and every decorated function
      in it in definition order. The name is `<file stem>.<function name>`.
- [x] A file is loaded under a module name unique to its case, so two cases each holding
      `checks/assertions.py` do not collide in `sys.modules`.
- [x] The case's `checks/` directory is on `sys.path` while its files are loaded, so a check
      may import a sibling in the same directory, and is off it again afterwards.
- [x] `run.file(name)` resolves under `run.workspace`. A name that resolves to nothing is a
      failed check naming it, and a name that leaves the workspace is a failed check too.
- [x] Execution: `None` or `True` passes, `False` fails, a returned `Result` decides, and any
      exception is a failed check carrying its message and its traceback. Nothing raises out
      of the module.
- [x] `run.scratch` is created before the first check of a run and is shared by every check of
      that run.
- [x] `tests/unit/test_checks.py`, over hand-written run directories under
      `tests/data/checks/`. No model, and no judge.

### Phase 2: the judge over paths

- [x] `run.judge(prompt, *paths)` in `checks.py`, over `judge.py`.
- [x] `judge.py` gains the check judge's argument list: `claude -p --output-format json
      --model <eval.judge_model> --strict-mcp-config`, with `Read`, `Glob` and `Grep`
      granted, the run directory as the working directory, and `--add-dir` for each path
      outside it. `judge_argv` is untouched.
- [x] The prompt names each path, relative to the working directory where it is under one.
- [x] Three votes and a majority of two, through the existing `read_reply` and `tally`.
      `run.judge` returns a `Result`, so a check returns it directly.
- [x] A call naming no path is a failed check saying so. There is no default of everything.
- [x] Phase 2 measures two facts about a tool-using `claude -p`, and each has a fallback that
      ships if the measurement fails.

      | Fact                                                                      | If it does not hold                                                          |
      | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
      | `--allowedTools Read,Glob,Grep` alone lets a non-interactive judge read a file | The argument list also carries the permission mode the measurement names       |
      | A tool-using judge answers with the bare word, so `read_reply` reads it       | The check judge reads the last word of `result`. `read_reply` stays exact, per D6 |

      Both go into `docs/checks.md` as measured behaviour, with the CLI version they hold for.
- [x] `tests/unit/test_judge.py` gains the check judge's argument list and its prompt.
- [x] `tests/integration/test_judge.py` gains one `live` test: a real `claude -p` judging a
      real PNG and a real PDF written by the test.

### Phase 3: into the result and into the run directory

- [x] Each check result is appended to that run's `graders[]`, and each definition to the
      case's `graders[]` with `type: check`.
- [x] The run's `score` and `passed`, and the case's `aggregates.score` and
      `aggregates.passRate`, are recomputed after the append.
- [x] A check judge's spend is added to that run's `judgeCostUsd` and to the document's
      `costUsd`, so the panel and `eval.max_cost_total_usd` both see it.
- [x] `checks.jsonl` is written into `traces/<case>/run-N/`: one line per check, carrying the
      name, the verdict, the explanation, the duration, and for a judge call the whole prompt,
      the three replies and the cost.
- [x] Only the `with` arm is walked. A `--ablation with-without` run leaves the baseline arm
      alone, for the reason in the out of scope table.
- [x] A case carrying `declaredUnrunnable` has no run and produces no check result. It is
      counted, not skipped, exactly as it is today.
- [x] `cli._each_plugin` calls the layer after `traces.collect`, once per plugin.
- [x] A case with checks and no collected artefacts produces one skipped check result per
      check, which fails the run.
- [x] `tests/unit/test_checks.py` covers the document it writes, field by field, and the
      recomputation.
- [x] A failed check produces a `FAIL` line from `verdict.decide` with no change to
      `verdict.py`. Asserted in `tests/unit/test_verdict.py`.
- [x] That line's `[artifacts: ...]` suffix names the directory holding `scratch/` and
      `checks.jsonl`, because `verdict.artifacts` names the parent of `tracePath` and both sit
      beside it. Asserted rather than assumed.
- [x] `verdict.artifacts`'s docstring stops saying the directory is the session's transcript
      directory on CoWork. `traces._one_run` rewrites `tracePath` to the collected copy on
      both backends, so the suffix names `traces/<case>/run-N` either way.

### Phase 4: the validator and the panel

- [ ] The validator imports every `checks/*.py` of every selected plugin root before anything
      runs. An import failure is a violation and exits 3.
- [ ] A duplicate check name within one case is a violation.
- [ ] A `checks/` directory holding no check at all is a violation. A single file holding
      none is not, because a helper beside a check is a file like any other.
- [ ] `context.add_dirs` naming `checks/` is a violation, exactly as naming `graders/` is.
      The harness refuses `graders/` itself and would grant `checks/` as a fixture directory,
      so this rule is this repository's and is not redundant. See
      `docs/claude_code/plugin_eval_reference.md`.
- [ ] `panel._defining` hashes each `checks/*.py` in path order, after the graders.
- [ ] `tests/unit/test_validate.py` and `tests/unit/test_panel.py` cover all four.

### Phase 5: the fixture and the integration tier

- [ ] `plugins/smoke/evals/plugin/checked-file/`, a case that writes a file and asserts its
      content with a check. It carries no `no-cowork` tag, because a check needs nothing a
      session cannot do.
- [ ] `plugins/README.md` gains the case and says what it is the fixture for.
- [ ] `tests/README.md` gains the `unit/test_checks.py` row and the new integration tests.
- [ ] `tests/integration/test_cli.py` gains one `live` test: the fixture case through
      `cowork_evals run --docker`, asserting the `FAIL` line, the appended grader result,
      `checks.jsonl` and `scratch/`.
- [ ] `scripts/test.sh` is green, and `scripts/lint.sh` is clean.
- [ ] `scripts/test.sh -m integration` is green.

### Phase 6: the documentation

- [ ] `docs/checks.md`, new: what a check is, that it runs on the host after the run is
      graded, `Run`, the judge, the run directory, and how a result reaches the document. It
      is a mechanism file.
- [ ] `docs/README.md` gains its row, among the mechanism files.
- [ ] `docs/eval_format.md` gains the `checks/` layer of the tree, the `add_dirs` refusal, the
      validator rules, the traps, and the statement that a check file is host code and is not
      bound by the image wheel set. The traps are that a check reads only a collected run,
      that a `checks/` file with no decorated function asserts nothing, and that each run of a
      case runs every check again, so `runs: 3` costs three of every judge call.
- [ ] `docs/running_evals.md` gains the status row, the skip under `--no-keep-traces`, and
      what a check judge costs.
- [ ] `docs/approaches.md` gains the row saying both backends honour a check.
- [ ] `docs/panel.md` says the digest covers the check files.
- [ ] `docs/cli.md` says what `--no-keep-traces` does to a case that has checks.
- [ ] `docs/library.md` gains `checks.py` in the ships table, and its "Where the
      restrictions are" section gains the row for a check and the exception to the sentence
      that reads every file under the path as code under test. A `checks/*.py` is under that
      path and is not code under test.
- [ ] `docs/runtime.md` says in "Rules for code that runs in a session" that a check is not
      one, beside the sentence that already excludes this package.
- [ ] `CLAUDE.md`'s three kinds of code table carries the same exception, because it names
      every file under the eval path and then enumerates skill, command, agent and hook. The
      enumeration is right and the leading phrase is not.
- [ ] `README.md` names the third kind of assertion where it names the other two.
- [ ] `src/cowork_evals/data/skills/cowork-evals/SKILL.md` carries the `checks/` directory,
      one copy-paste check and one copy-paste judge call.
- [ ] `tests/unit/test_resources.py` is green against the changed skill.
- [ ] `plans/README.md` row 16 moves to `implemented`, and this file moves to
      `done/plan_artifact_checks.<YYYYMMDD>.md` on the merge.

## Out of scope

| Not built                                            | Because                                                                    |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| A free-form `run.ask` returning the judge's text      | A check is host code and may call `subprocess` itself. A second route to the same CLI is a split with no rule |
| A `@transform` decorator                             | D3                                                                         |
| A weight or a name on `@check`                        | D7                                                                         |
| A configuration key of any kind                      | The judge model is `eval.judge_model`, and everything else is discovered    |
| A check on the `without` arm                         | The baseline arm runs without the plugin, so an assertion about what the plugin produced has nothing to read there |
| Any way to run a check inside the container or the VM | D13. The run is graded before a check starts, and a check that ran inside the thing under test would be bound by the image wheel set for no gain |
