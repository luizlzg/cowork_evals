# A judge that says why, the route it judges, and an advisory check

## The problem

Three problems, each found by the one before it, on a real suite over a spreadsheet skill.

**A grader and a check both read what the run produced, and neither can see how it got there.** A
workbook written by the command a skill documents is byte-comparable with one a script reimplemented.
Measured: a case scored 1.00 on a run that called the skill's own dedup command and then saved a
Python script's output over the workbook that command had just written. Every assertion on the case
passed, because the delivered file was deduplicated. So the suite could not tell using a skill from
bypassing it, which is the question ablation exists to answer.

**A judge could not be asked about it.** `judge.read_reply` required a reply to be exactly `PASS` or
`FAIL` and kept only a boolean. That rule is fine for a short question — *is this slide clipped* — and
is a ceiling on a long one: a judge given a 200 KB transcript and read-only tools works through what it
found and then concludes, and that working is how it gets the answer right. Every vote on two different
rubric shapes came back `LOST` while the narration reached the right conclusion.

**And once it could be asked, it was not reliable enough to gate a suite.** Over three runs whose right
answer was known from their traces, `haiku` got two and `sonnet` got one, both erring towards leniency
by reading the skill's escape to a Python script more broadly than it is written. The only way to
report without deciding was for the check to swallow the verdict and return a pass with the word FAIL
inside a string, which is a convention every author has to remember and which destroys the data: a miss
cannot be counted, so nothing calibrates the rubric.

Branch: `feat/trace-judging`, off `fix/checks-both-arms`.

## What this plan does

A judged assertion can read a transcript, say why, and decide nothing until it is calibrated.

Three products. A judge that returns its reasoning beside its verdict, out of the CLI's own structured
output. `@check(advisory=True)`, the marker that makes a check report without deciding. And the design
guidance for the assertion the first two exist for, in
[`../docs/eval_design.md`](../docs/eval_design.md).

## Decisions

| Decision                                      | Chosen                                                                | By            |
| --------------------------------------------- | ---------------------------------------------------------------------- | ------------- |
| How a reply carries reasoning                 | `claude -p --json-schema`, so the CLI enforces the shape               | the developer |
| An older host CLI                             | keep the bare-word parse as a fallback                                 | the developer |
| The vote count                                | configurable, `eval.judge_votes`, default 3                            | the developer |
| Whether the judged assertion gates a suite     | no. Advisory until calibrated                                          | the developer |
| Where advisory lives                          | a marker in the harness, not a convention in the check                 | the developer |
| The judge model                               | `haiku`. Measured better than `sonnet` here, at a third of the cost    | the developer |

`--json-schema` was measured before it was designed against, on CLI 2.1.273: the envelope gains a
parsed `structured_output` object, it works with a tool-using judge, and `stop_reason` comes back
`tool_use` because structured output is a tool call underneath, so nothing may read that as an error.

## Phase 1: the judge says why

- [x] `VERDICT_SCHEMA`, `{reasoning: string, verdict: enum[PASS, FAIL]}`, required, no additional
      properties, and `judge_argv` carries it, so the check judge and the CoWork backend's judged
      graders get it from one place.
- [x] `Reply` gains `reasoning`. `read_reply` reads `structured_output` where the document carries it
      and falls back to the exact word otherwise, and the rule is in its docstring.
- [x] `tally` carries the winning side's reasoning: a head of it in the explanation, which is what a
      `FAIL` or `NOTE` line prints, and as much as `EVIDENCE_LIMIT` allows in the document's evidence.
- [x] The instructions stop demanding one word and ask for substance, since the schema enforces shape.
- [x] `eval.judge_votes`, default 3, in `EvalSection`, in the example configuration as a commented
      default, and explained in [`../docs/running_evals.md`](../docs/running_evals.md).
- [x] `majority(votes)` is `votes // 2 + 1`, so one vote needs one and three need two.
- [x] Fixtures are real trimmed CLI envelopes, not hand-written shapes, including one carrying
      `structured_output` with no usable verdict, which has to be a lost vote.

## Phase 2: the advisory marker

- [x] `@check` takes `advisory`, in both the bare and the called form, and marks the function.
- [x] `Check` and `Outcome` carry the flag, discovery reads it off the function, and `execute` puts it
      on every outcome it builds, the two exception paths included.
- [x] An advisory definition carries its own grader type, `check-advisory`, because
      `verdict._judge_grader` learns a result's class from its definition and has no other route.
- [x] Its result carries its real `passed` and `scored: false`, so a `FAIL` stays a `FAIL` in the
      document and can be counted, and the score does not move.
- [x] The advisory branch in `verdict._judge_grader` sits ahead of the `scored: false` branch, which on
      one arm reads an unscored result as a skip and fails it.
- [x] A failure prints a `NOTE` naming the reasoning, and never a `FAIL`.

## Phase 3: the design guidance

- [x] [`../docs/eval_design.md`](../docs/eval_design.md) gains `## The deliverable does not show the
      route`: why a third assertion exists, the three questions it asks and no more, and its rules.
- [x] The judge is shown the task as well, because a collected trace opens on a `system` record and
      carries no record of what was asked. The case's own `prompt.md` is the source, read rather than
      restated.
- [x] Write it advisory until it is calibrated, with the measurement that says why.
- [x] Show the judge the skill and not a summary of it, and never demand a route the skill ships no
      command to take. Both cost a wasted verification pass to learn.
- [x] [`../docs/checks.md`](../docs/checks.md) gains `## An advisory check`, and its line saying a
      check has no equivalent of the harness's unscored indicator is now a pointer to the one it has.
- [x] The shipped `cowork-evals` skill carries both in its own register.

## Phase 4: verification

- [x] `scripts/lint.sh` and `scripts/test.sh`. 862 unit tests pass.
- [x] An advisory failure asserted end to end through real discovery: verdict `FAIL`, document
      `passed: false, scored: false`, definition `check-advisory`, score unmoved, one `NOTE` printed.
- [x] The two traces the exact-word parser lost its votes on, re-judged: the same verdicts, with
      readable reasoning, and no lost vote.
- [x] A consumer suite of nine cases run at `--runs 3 --ablation with-without` with the assertion in
      seven of them, in `enterprise-ai-claude-marketplace`: ten of twenty-one with-arm runs pass, no
      delta moves, and the failures name the instruction they broke.
- [x] `plans/README.md` gains this plan, and this file is written into `done/`.

## Out of scope

Calibrating the rubric until the judged assertion can gate a suite. What it costs to get there is a
labelled set of traces per skill, and the assertion is advisory precisely so that work can happen
against recorded verdicts rather than against a red suite.

Extracting the ordered command list from a trace in Python and handing the judge that beside the
transcript, which would make the checkable half deterministic. Proposed and declined: the judge is
meant to read the run, and a pre-digested run is a different assertion.
