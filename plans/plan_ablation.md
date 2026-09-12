# Ablation: check the plugin did anything, not just that the cases passed

## The problem

A suite that passes does not tell you the plugin works. The model may have done the task on
its own.

Ask a model to build a spreadsheet and it will probably build one whether or not your
spreadsheet plugin is loaded. Every grader passes, the suite is green, and you have learned
nothing. A suite that is green because the plugin is good and a suite that is green because
the plugin is irrelevant look identical.

The harness can settle it: run each case twice, once with the plugin loaded and once with
nothing loaded, and compare the two scores. This package pins that setting to off and offers
no way to change it.

The pin has a reason. Under `with-without` the harness stops scoring a `tool_used: Skill`
grader and demotes it to an indicator, so the arm turns off the check that the skill fired at
all. Off is therefore the right default, and it stays the default after this plan. What is
wrong is that there is no way to ask for the arm.

## What this plan does

Adds the option and the config key, keeps the traces from both runs, and decides on the
difference between the two scores rather than on the score alone.

Off by default, because it runs every case twice and so costs twice as much.

Last of the four plans, because it rewrites the pass and fail rules that
[`plan_run_validity.md`](plan_run_validity.md) and
[`plan_runnability.md`](plan_runnability.md) both change.

Branch: `feat/ablation`.

## Docker only, and that is not a gap

There is no baseline arm on CoWork, and no plan builds one. A session gets its skills from
the profile the desktop application is running, and that tree is the application's to manage.
So a plugin is absent only in a profile it was never installed into, and nothing here chooses
which profile is active. A second arm would mean a second profile and restarting the
application between the two. The measurement behind that is in
[`../docs/cowork_desktop.md`](../docs/cowork_desktop.md).

The arm is a statistical control, and a control belongs on the cheap backend. CoWork is the
expensive one that checks the real thing. Decided, and not reopened here.

## The two settings

| Setting                | Values                 | Default |
| ---------------------- | ---------------------- | ------- |
| `eval.ablation`        | `none`, `with-without` | `none`  |
| `eval.delta_threshold` | a number from 0 to 1   | `0`     |

`--ablation` and `--delta-threshold` are the command-line options over them, and the command
line beats the file as it does for every other option.

`eval.ablation` stays off by default, for the reason the problem statement gives, and because
the arm runs every case twice and so costs twice as much.

## What is compared

Per case: the with-arm's score minus the without-arm's score, failing below
`eval.delta_threshold`.

Per case and not per suite, because a suite average hides the one case the plugin made worse.
`--threshold` stays pinned to 0 so the harness hands the verdict over, which is why the
number lives in this package and not in that flag.

Under `--ablation none` there is one arm and no delta, and the verdict is reached exactly as
it is today.

## The `scored: false` condition has to move

A grader carrying `scored: false` fails the run today, on the stated ground that
`--ablation none` drops no grader from the score. That ground disappears in the two-arm run:
the harness drops a `tool_used: Skill` grader from the score in both arms on purpose.

| Run               | `scored: false` on a grader                                                           |
| ----------------- | ------------------------------------------------------------------------------------- |
| `--ablation none` | A skip, and it fails the run, exactly as today                                        |
| `with-without`    | Expected on a with-only grader, and it is reported as an indicator rather than failed |

Getting this wrong in either direction is the whole risk in this plan. Too strict and every
two-arm run is red; too loose and a real skip goes green in the one-arm run everybody uses.

## What this plan does not do

| Not in scope                               | Where it is instead                                                                           |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| A baseline arm on CoWork                   | Nowhere, and the section above says why                                                       |
| `arm:` on a grader                         | Carried into the document by both backends and inert today. This plan makes it live on Docker |
| Failing a run that never executed its tool | [`plan_run_validity.md`](plan_run_validity.md)                                                |

## Orientation

| Fact                                                         | Where                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------ |
| The pinned ablation and threshold                            | `src/cowork_evals/harness.py`, `ABLATION`, `THRESHOLD` |
| The same two names on the CoWork document, which stay pinned | `src/cowork_evals/results.py`, `ABLATION`, `THRESHOLD` |
| What decides pass and fail, and the one arm it reads         | `src/cowork_evals/verdict.py`, `ARM`, `_judge_case`    |
| The `scored: false` condition                                | `src/cowork_evals/verdict.py`, `_judge_grader`         |
| Trace collection, and the same single arm                    | `src/cowork_evals/traces.py`, `ARM`, `_each_run`       |
| What the harness does with two arms, and `withOnly`          | [`../docs/running_evals.md`](../docs/running_evals.md) |
| The model calls a suite makes, counted                       | [`../docs/plugin_eval.md`](../docs/plugin_eval.md)     |
| The `arm:` table, and what a case author controls            | [`../docs/running_evals.md`](../docs/running_evals.md) |

## Phases

### Phase 1: measure a two-arm run

Nothing in this repository has read a two-arm result document. Every field below is the
vendored reference's and not a measurement.

The option this phase needs does not exist until phase 2, and `cowork_evals run` pins
`--ablation none`. So this phase calls the harness by hand, which is what
[`../docs/running_evals.md`](../docs/running_evals.md) already describes a baseline arm as.
Build the command line from `harness.eval_argv` with `--ablation with-without` substituted,
and run it in the container the same way `Docker.run` does.

- [ ] Run `docs/claude_code/eval_smoke/` through the container with `--ablation with-without`
      and keep the result document. That fixture has a skill, a `tool_used: Skill` grader and
      an over-trigger case, so it exercises every shape the arm changes
- [ ] Write into [`../docs/running_evals.md`](../docs/running_evals.md), dated: what `arms`
      holds, what the second arm's key is called, which graders carry `withOnly` and
      `scored`, and whether the result file carries a delta of its own or `verdict.py` has
      to work one out
- [ ] Record what the without-arm's runs carry in place of `tracePath`, which decides phase 3
- [ ] Record what the document holds when the arms are not comparable. The reference says
      `delta` and `scoreWithout` are omitted when the without-arm is empty or a run skipped
      paid graders, and phase 4 needs to know which of the two it is looking at
- [ ] It costs two agent runs per case. Three cases at one run each is six, and
      [`../docs/plugin_eval.md`](../docs/plugin_eval.md) counts the rest

Phases 2 to 4 are written against what this phase records. If the without-arm's key is not
what the reference says, the constant changes and nothing else does.

### Phase 2: the option and the setting

- [ ] `eval.ablation` and `eval.delta_threshold` in the `eval:` section, with the defaults
      above
- [ ] `--ablation` and `--delta-threshold` on `run`, Docker only, refused on `--cowork` with
      exit 2 naming why
- [ ] `harness.ABLATION` stops being a constant and becomes the resolved option.
      `harness.THRESHOLD` stays pinned to 0, and the docstring says the delta number lives in
      `verdict.py`
- [ ] `results.ABLATION` and `results.THRESHOLD` are untouched. They are what the CoWork
      document records, that backend runs one arm, and the section above says why
- [ ] The pinned-flag table in [`../docs/running_evals.md`](../docs/running_evals.md) moves
      `--ablation` from pinned to optioned

### Phase 3: the traces

- [ ] `traces.py` collects both arms, one directory per arm per run, so a failing delta can
      be read as two transcripts rather than one
- [ ] The layout keeps one directory per run and adds the arm to the path. The name is fixed
      here and stated in [`../docs/running_evals.md`](../docs/running_evals.md)
- [ ] A one-arm run's layout is unchanged, byte for byte. One arm is the default, so this is
      the layout almost every run produces, and `tracePath` and the `[artifacts: ...]` suffix
      both keep naming it
- [ ] `tracePath` is rewritten for both arms, so the `[artifacts: ...]` suffix names
      the right directory on a line about either

### Phase 4: deciding pass and fail

- [ ] `verdict.decide` takes the resolved `eval.delta_threshold`, the way it already takes
      `extra`. It reads no configuration file of its own, so one invocation still resolves
      every setting once and it stays a function of the run directory and its arguments
- [ ] Both arms are read when the document holds two
- [ ] Per case, with minus without, failing below `eval.delta_threshold`, one line naming
      both scores and the delta
- [ ] A two-arm case the document says is not comparable fails. A two-arm run that produced
      no delta did not do what the invocation asked, and passing it would be the
      green-on-nothing this plan exists to remove
- [ ] The line names which of the two reasons it was when phase 1 found the document
      distinguishes them, and says only that the arms were not comparable when it does not.
      The failure is the same either way, so the measurement decides the wording and nothing
      else
- [ ] The `scored: false` condition splits along the table above: a skip in a one-arm run, an
      indicator in a two-arm run
- [ ] A case whose graders are all with-only is the harness's stated exception, scored
      normally in both arms. `verdict.py` reads what the document says and does not
      re-derive it
- [ ] Every other condition is unchanged and applies to the with-arm, which is what a
      structural grader failing still means
- [ ] The summary line names the mean delta beside the counts, when there are two arms

### Phase 5: tests

Unit tier, over recorded documents, except phase 1's run.

- [ ] A one-arm document decides exactly as it does today, over the existing fixtures
- [ ] A two-arm document whose delta is above the threshold passes
- [ ] A two-arm document whose delta is below it fails, and the line names both scores
- [ ] A two-arm document whose case carries no delta fails, and the line names the reason
- [ ] A `scored: false` grader fails a one-arm document and does not fail a two-arm one
- [ ] A case whose graders are all with-only passes in a two-arm document
- [ ] `--ablation with-without` on `--cowork` exits 2
- [ ] The default resolves to `none`, so an unconfigured repository runs one arm

### Phase 6: documentation

- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): the baseline arm stops being
      described as something you do by calling the harness yourself, and becomes an option.
      The pass and fail table gains the delta condition, the incomparable-arms condition
      beside it, and the split `scored: false` condition. The trace layout gains the arm
- [ ] [`../docs/cli.md`](../docs/cli.md): the two options, and that both are Docker only
- [ ] [`../docs/approaches.md`](../docs/approaches.md): `arm:` on a grader stops being inert
      on Docker, and stays inert on CoWork
- [ ] [`../docs/plugin_eval.md`](../docs/plugin_eval.md): the model-call count for a two-arm
      suite is what a reader is pointed at for the cost
- [ ] [`../docs/cowork_backend.md`](../docs/cowork_backend.md): one line saying that backend
      runs one arm and why, pointing at the measurement rather than restating it
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 7: integration

- [ ] `plugins/smoke/` on the Docker backend with one arm, green, and the trace layout
      unchanged
- [ ] `docs/claude_code/eval_smoke/` with two arms, from the integration tier, with the
      delta printed
- [ ] `plugins/smoke/` on CoWork, green, unaffected
- [ ] `scripts/test.sh` and `ruff` clean
