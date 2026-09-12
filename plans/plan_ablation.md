# Ablation: the baseline arm, and a gate that decides on the delta

`harness.py` pins `ABLATION = "none"` and exposes nothing. A suite therefore answers "do the
cases pass" and never answers "did the plugin change anything". Under `--ablation
with-without` the harness runs every case twice, with the plugin loaded and with no plugin at
all, and the score delta is the evidence.

This plan unpins it, adds the option and the setting, collects the second arm's traces, and
rewrites the gate to decide on the delta.

It is last of the four, because it rewrites the gate that
[`plan_run_validity.md`](plan_run_validity.md) and
[`plan_runnability.md`](plan_runnability.md) both change.

Branch: `feat/ablation`.

## Docker only, and that is not a gap

There is no baseline arm on CoWork, and no plan builds one. The reason is measured, in
section 5 of [`../docs/cowork_desktop.md`](../docs/cowork_desktop.md): a session's skill set is
the profile's mounted, application-managed tree, so a plugin is absent only in a profile it
was never installed into, and the desktop application chooses the active profile rather than
this package. A second arm there means a second profile and an application restart between
arms.

The arm is a statistical control, and a control belongs on the cheap backend. CoWork is the
expensive one that checks the real thing. The decisions table in
[`plan_believable_results.md`](plan_believable_results.md) holds this and it is not reopened
here.

## The two settings

| Setting          | Values                   | Default          |
| ---------------- | ------------------------ | ---------------- |
| `eval.ablation`  | `none`, `with-without`   | `none`           |
| `eval.delta_threshold` | a number from 0 to 1 | `0`              |

`--ablation` and `--delta-threshold` are the command-line options over them, and the command
line beats the file as it does for every other option.

Off by default, because under `with-without` the harness stops scoring a `tool_used: Skill`
grader and reports it as an indicator carrying `withOnly: true` and `scored: false`. On by
default would silently stop gating skill activation, which is the defect the problem report
opened with.

## What the gate compares

Per case: the with-arm's score minus the without-arm's score, failing below
`eval.delta_threshold`.

Per case and not per suite, because a suite average hides the one case the plugin made worse.
`--threshold` stays pinned to 0 so that the harness hands pass and fail to this gate, which
is why the number lives here and not there.

Under `--ablation none` there is one arm and no delta, and the gate decides exactly as it
does today.

## The `scored: false` condition has to move

The gate today fails any grader carrying `scored: false`, on the stated ground that
`--ablation none` drops no grader from the score. That ground disappears in the two-arm run:
the harness drops a `tool_used: Skill` grader from the score in both arms on purpose.

| Run                | `scored: false` on a grader                          |
| ------------------ | ------------------------------------------------------- |
| `--ablation none`  | A skip, and it fails the gate, exactly as today       |
| `with-without`     | Expected on a with-only grader, and it is reported as an indicator rather than failed |

Getting this wrong in either direction is the whole risk in this plan. Too strict and every
two-arm run is red; too loose and a real skip goes green in the one-arm run everybody uses.

## What this plan does not do

| Not in scope                                   | Where it is instead                            |
| ------------------------------------------------- | ------------------------------------------------ |
| A baseline arm on CoWork                        | Nowhere, and the section above says why         |
| `arm:` on a grader                              | Already read by both backends, and inert today. This plan makes it live on Docker |
| Failing a run that never executed its tool      | [`plan_run_validity.md`](plan_run_validity.md)  |

## Orientation

| Fact                                                      | Where                                             |
| ------------------------------------------------------------ | --------------------------------------------------- |
| The pinned ablation and threshold                           | `src/cowork_evals/harness.py`, `ABLATION`, `THRESHOLD` |
| The gate, and the one arm it reads                          | `src/cowork_evals/gate.py`, `ARM`, `_judge_case`   |
| The `scored: false` condition                               | `src/cowork_evals/gate.py`, `_judge_grader`       |
| Trace collection, and the same single arm                   | `src/cowork_evals/traces.py`, `ARM`, `_each_run`  |
| What the harness does with two arms, and `withOnly`         | [`../docs/running_evals.md`](../docs/running_evals.md) |
| The model calls a suite makes, counted                      | [`../docs/plugin_eval.md`](../docs/plugin_eval.md) |
| The `arm:` table, and what a case author controls           | [`../docs/running_evals.md`](../docs/running_evals.md) |

## Phases

### Phase 1: measure a two-arm run

Nothing in this repository has read a two-arm result document. Every field below is the
vendored reference's and not a measurement.

- [ ] Run `docs/claude_code/eval_smoke/` through the container with `--ablation with-without`
      and keep the result document. That fixture has a skill, a `tool_used: Skill` grader and
      an over-trigger case, so it exercises every shape the arm changes
- [ ] Record, dated and called a snapshot, in
      [`../docs/running_evals.md`](../docs/running_evals.md): what `arms` holds, what the
      without-arm's key is called, which graders carry `withOnly` and `scored`, and whether
      the document carries a delta of its own or the gate computes one
- [ ] Record what the without-arm's runs carry in place of `tracePath`, which decides phase 3
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
      the gate
- [ ] The pinned-flag table in [`../docs/running_evals.md`](../docs/running_evals.md) moves
      `--ablation` from pinned to optioned

### Phase 3: the traces

- [ ] `traces.py` collects both arms, one directory per arm per run, so a failing delta can
      be read as two transcripts rather than one
- [ ] The layout keeps one directory per run and adds the arm to the path. The name is fixed
      here and stated in [`../docs/running_evals.md`](../docs/running_evals.md)
- [ ] A one-arm run's layout is unchanged, byte for byte, so every existing trace path still
      resolves
- [ ] `tracePath` is rewritten for both arms, so the gate's `[artifacts: ...]` suffix names
      the right directory on a line about either

### Phase 4: the gate

- [ ] The gate reads both arms when the document holds two
- [ ] Per case, with minus without, failing below `eval.delta_threshold`, one line naming
      both scores and the delta
- [ ] The `scored: false` condition splits along the table above: a skip in a one-arm run, an
      indicator in a two-arm run
- [ ] A case whose graders are all with-only is the harness's stated exception, scored
      normally in both arms. The gate reads what the document says and does not re-derive it
- [ ] Every other gate condition is unchanged and applies to the with-arm, which is what a
      structural grader failing still means
- [ ] The summary line names the mean delta beside the counts, when there are two arms

### Phase 5: tests

Unit tier, over recorded documents, except phase 1's run.

- [ ] A one-arm document gates exactly as it does today, over the existing fixtures
- [ ] A two-arm document whose delta is above the threshold passes
- [ ] A two-arm document whose delta is below it fails, and the line names both scores
- [ ] A `scored: false` grader fails a one-arm document and does not fail a two-arm one
- [ ] A case whose graders are all with-only passes in a two-arm document
- [ ] `--ablation with-without` on `--cowork` exits 2
- [ ] The default resolves to `none`, so an unconfigured repository runs one arm

### Phase 6: documentation

- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): the baseline arm stops being
      described as an investigation run by hand and becomes an option. The gate table gains
      the delta condition and the split `scored: false` condition. The trace layout gains the
      arm
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
