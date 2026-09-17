# A check scores both arms, so a suite of checks has a delta

## The problem

A real suite was built where every assertion that could say anything about the deliverable was a
check, because the deliverable was a workbook and no grader type reads a cell. It ran under
`--ablation with-without` and reported a delta of `+0.00` on every case but one.

The baseline arm had run. Its artefacts were on disk under `traces/<case>/without/run-<n>`, collected
exactly like the with-arm's. The checks had simply never been executed over them:
`checks.run`'s per-case walk read `arms[ARM_WITH]` and nothing else, while the collector, the run
directory layout and `results._aggregates` were all already arm-agnostic. One hardcoded key, three
layers down from the flag.

So a suite whose assertions are checks could not answer the second of the two questions a suite
exists to answer, and it answered it wrongly rather than not at all: `+0.00` reads as *the skill adds
nothing*, and it meant *nothing was measured*.

Branch: `fix/checks-both-arms`.

## What this plan does

Every arm a case carries is walked, and the case's numbers are recomputed per arm.

It adds no command, no option and no configuration key. The flag that runs the second arm already
exists; this is the check layer honouring it.

## Decisions

| Decision                                      | Chosen                                                              | By            |
| --------------------------------------------- | -------------------------------------------------------------------- | ------------- |
| Whether a check runs on the baseline arm      | yes, on every arm the case carries                                   | the developer |
| Whether a missing delta is resurrected        | no. Recompute only where the document already carries one            | this plan     |
| What decides an arm's runs                    | `results.ARMS`, so a third arm needs no change here                  | this plan     |

**The delta is recomputed only where the harness already put one.** The harness omits `delta`, and
`scoreWithout` with it, when the two arms were graded under different rules, and that judgement stays
the harness's. A check moving a score is not a reason to declare two arms comparable that the document
says are not.

## Phase 1: the walk

- [x] `_each_case` iterates `results.ARMS` instead of reading `ARM_WITH`, so the runs of every arm
      are collected, checked and written into.
- [x] `_case_aggregates`, new: `score` and `passRate` over the with-arm's runs, `scoreWithout` and
      `passRateWithout` over the baseline arm's, and `delta` over the two, each recomputed only where
      the key is already present.
- [x] `_recount` recomputes `meanDelta` over the case deltas that are defined, by the same rule
      `results._aggregates` uses, because a check now moves the deltas it averages.
- [x] A case carrying `declaredUnrunnable` still produces no check result, on either arm.

## Phase 2: tests

- [x] A check that passes on one arm and fails on the other moves the case's delta, asserted on a
      hand-written two-arm document.
- [x] A document carrying no `delta` does not gain one, and a document carrying no `scoreWithout`
      does not gain one.
- [x] `meanDelta` over a suite where one case has no delta averages the ones that do.
- [x] The one-arm path is unchanged: a `--ablation none` document comes out as it did.
- [x] `scripts/lint.sh` and `scripts/test.sh` pass.

## Phase 3: the documents

- [x] [`../docs/checks.md`](../docs/checks.md): every arm is walked, the baseline's artefacts are
      checked like any other run, and the rule that the delta is recomputed only where one exists.
- [x] The same file carries the consequence for the author: a check that cannot hold without the
      plugin inflates the delta, so assert the deliverable and never the route to it.
- [x] [`../docs/running_evals.md`](../docs/running_evals.md), wherever it says which arm a check
      runs on.

## Phase 4: verification

- [x] The suite that produced the symptom re-run under `--ablation with-without`: the case whose
      baseline genuinely differs reports a delta, and the cases that tie report `+0.00` because they
      tie rather than because nothing ran.
- [x] `plans/README.md` gains this plan, and this file is written into `done/`.

## Out of scope

`@check(arm=...)`, an assertion an author declares as one-arm-only. Nothing needed it: an assertion
that cannot hold on the baseline is an assertion aimed at the route rather than the deliverable, and
[`../docs/checks.md`](../docs/checks.md) now says so. The one case that genuinely wants it is a judged
rubric over a transcript, and `plan_trace_judge` handles that with a path guard in the check itself.
