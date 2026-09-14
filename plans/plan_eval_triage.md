# Eval triage: what a verdict says to change, and who approves the change

## The problem

`cowork_evals run` writes a verdict and a transcript, and stops there. No file in this
repository says what to do with a finding. [`../docs/running_evals.md`](../docs/running_evals.md)
owns what a run writes and what each finding means, and stops before an edit.
[`../docs/eval_design.md`](../docs/eval_design.md) owns which cases a suite needs, and it answers
that question before a run exists.

The shipped `cowork-evals` skill carries `## Reading a failure`, which names where the evidence
is and nothing else. It does not separate a broken skill from a broken grader, it proposes no
edit, and it never mentions approval. So a session that reads a failing verdict has nothing to
tell it why the run failed. The easiest change is to edit the case until it passes. That change
hides the failure instead of fixing it, and nothing reports that it happened, because the next
run is green.

## What this plan does

One document owns triage, and a third shipped skill runs it: read `verdict.txt`, open the
evidence each failing line names, classify each finding by cause, propose the edits, get the
developer's approval, apply the approved ones one at a time, and hand back the command to
re-run.

It adds no command, no option, no configuration key and no validator rule. Post-hoc reading of a
run stays the consumer's own script, which is
[`../docs/running_evals.md`](../docs/running_evals.md).

Branch: `plan/eval-triage`.

## Decisions

| Decision                                  | Chosen                                                        | By            |
| ----------------------------------------- | ------------------------------------------------------------- | ------------- |
| Where the guidance lives                  | a new document, `docs/eval_triage.md`                         | the developer |
| The skill shape                           | a third shipped skill, not a section                          | the developer |
| The rule that separates the skills        | is there a verdict to read?                                   | the developer |
| Where `## Reading a failure` lives         | the new skill, moved out of `cowork-evals`                     | the developer |
| Who applies an approved change            | the skill applies it, one item at a time                      | the developer |
| Scope                                     | failures only. A passing run gets nothing                     | the developer |
| A new verb                                | no                                                            | the developer |
| The names `cowork-triage` and `eval_triage` | this plan's proposal, and renameable before Phase 1 starts    | the plan      |

The developer chose the split rule and the scope. The cause classes, and the mapping from each
verdict finding kind onto one of them, are this plan's. Neither invents a finding kind: every
kind named is one `src/cowork_evals/verdict.py` already emits.

## The two split rules

[`../CLAUDE.md`](../CLAUDE.md) requires a rule wherever one thing divides across two files. Two
divisions open here, so this plan writes two rules, and both go into
[`../docs/README.md`](../docs/README.md) beside the splits already there.

**Between the skills. Is there a verdict to read?** No, and it is `cowork-evals`: which cases a
skill needs, the case format, the configuration file, and a command that could not run at all,
meaning exit 2 and exit 3, where nothing was written. Yes, and it is `cowork-triage`: a run
happened, `verdict.txt` exists, and the question is what to change. `cowork-ask` is unchanged and
still fires on what a live session does.

**Between the documents. Does the statement decide an edit?** No, and it is
[`../docs/running_evals.md`](../docs/running_evals.md). Yes, and it is `docs/eval_triage.md`. The
same question separates the new document from
[`../docs/eval_design.md`](../docs/eval_design.md): design is what a suite needs before a run
exists, and triage is what a verdict says to change after one.

Both rules are checked against every statement already in the three documents and the two
skills before Phase 1 is ticked. `## Reading a failure` is the only section the check is already
known to move.

## What the new document owns

| Owns                                | Which is                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------------------------------- |
| The workflow, in order              | locate the run, read `verdict.txt`, separate the failing lines from the notes, open the evidence each failing line names, classify, propose, get approval, apply one item at a time, hand back the command to re-run |
| The cause classes                   | the skill under test is wrong; the case is wrong, which includes a check that asserts the wrong thing; the access is wrong; the run is non-deterministic; there is nothing to fix. A finding the evidence does not decide is reported undecided |
| Finding kind to cause               | one row per kind `verdict.py` emits, so a new kind has a place to land. The kinds and their texts stay in `verdict.py`, and the document links |
| The default hypothesis              | the skill under test is wrong. A case is edited only where the evidence shows the case is wrong, and never to turn a failing run green |
| Approval, and what a run costs      | no file changes before the developer approves that item, and the skill runs no suite itself: it proposes the scoped `cowork_evals run` command and stops |
| What the evidence settles           | `## Reading a failure` in full: the `[artifacts: ...]` suffix, every file a kept run leaves, the two `trace.jsonl` formats, and what `--no-keep-traces` gives up |

Each cause class other than the skill under test says what the evidence has to show before an
edit is proposed.

| Cause class                  | The evidence has to show                                                                                    |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------- |
| The case is wrong            | the prompt does not ask for what the grader asserts, or the pattern is misanchored, or the target or the grader type is wrong, or a check asserts something the prompt never asked for |
| The access is wrong          | a tool was never offered, or a tool was refused, or a fixture is absent, or the case needed `no-cowork`       |
| The run is non-deterministic | two runs of one case disagree                                                                                |

## What this plan does not do

| Not in scope                                    | Where it is instead                                                                          |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------- |
| A `report` or an `analyse` verb                  | Nowhere. Post-hoc reading of a run is the consumer's own script, and that is [`../docs/running_evals.md`](../docs/running_evals.md). `panel` reads the history a run appends and not a verdict, so it is not that route: [`../docs/panel.md`](../docs/panel.md) |
| Anything about a passing run                    | Nowhere. What a suite should hold is [`../docs/eval_design.md`](../docs/eval_design.md)        |
| A new grader type, option or configuration key   | Nowhere. Nothing here needs one                                                              |
| Code under `src/cowork_evals/`, beyond one string | Nowhere. `resources.skills()` reads the directory, so `init` installs a third skill with no code change |
| Running a suite on the developer's behalf        | Nowhere. The skill proposes the command                                                      |
| An eval for the new skill                        | Nowhere. This is a library, and the rule is [`../CLAUDE.md`](../CLAUDE.md)                     |

## Orientation

| Fact                                                     | Where                                                        |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| A skill states no fact of its own                        | [`../docs/library.md`](../docs/library.md)                    |
| Every finding kind, and its exact text                    | `src/cowork_evals/verdict.py`                                 |
| What a failed check is, and what it leaves behind          | [`../docs/checks.md`](../docs/checks.md)                      |
| What state a case tree is in between runs                  | [`../docs/panel.md`](../docs/panel.md)                        |
| Which grader class decides the exit code                  | [`../docs/running_evals.md`](../docs/running_evals.md)        |
| What a run leaves, and under which names                  | [`../docs/running_evals.md`](../docs/running_evals.md)        |
| Which case feature the CoWork backend cannot honour        | [`../docs/approaches.md`](../docs/approaches.md)              |
| Which cases a skill needs, and the interview that decides  | [`../docs/eval_design.md`](../docs/eval_design.md)            |
| Where `init` writes a skill, and how a skill is refreshed  | [`../docs/cli.md`](../docs/cli.md)                            |
| The skill checked against the documents it condenses       | `tests/unit/test_resources.py`                                |
| The installed skill count                                  | `tests/unit/test_cli_docs_init.py`                            |

`tests/unit/test_resources.py` reads the skill list sorted and asserts on index 0, so a third
name changes that list and the assertion is re-read rather than assumed.

## Phases

### Phase 1: the document

- [ ] `docs/eval_triage.md`: the workflow in order, the cause classes and what the evidence has
      to show for each, the finding kind table, which covers the check kinds beside the grader
      ones, the default hypothesis, the approval rule, the cost rule, and the evidence section
- [ ] [`../docs/README.md`](../docs/README.md): the row, the count in the divide prose, and both
      split questions beside the ones already there
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): the sentence that says a consumer
      writes their own script keeps its position and its meaning, and what a finding says about
      an edit points at the new document. No verb is added
- [ ] [`../docs/eval_design.md`](../docs/eval_design.md): the one sentence that separates design
      from triage
- [ ] `README.md`: the row in the documentation table
- [ ] `scripts/build.sh`: the new document is a wheel member, and the comment counts four

### Phase 2: the skill

- [ ] `src/cowork_evals/data/skills/cowork-triage/SKILL.md`: the condensed form of the document,
      in the shape the two existing skills use, opening with the document that owns it
- [ ] `src/cowork_evals/data/skills/cowork-evals/SKILL.md`: `## Reading a failure` leaves, the
      trigger loses the failing-command item and gains the could-not-run half, and the routing
      table names the new document
- [ ] [`../docs/library.md`](../docs/library.md): three skills, the rule that separates them, the
      new row with what it fires on and what it holds, and the sentence naming the documents each
      one condenses
- [ ] `src/cowork_evals/resources.py`: the `CLAUDE.md` block names the third skill. The marker is
      unchanged, so a consumer who already ran `init` keeps the old block, which
      [`../docs/cli.md`](../docs/cli.md) already states
- [ ] [`../docs/cli.md`](../docs/cli.md): the `init` target rows, why each skill is its own file,
      and the refresh recipe
- [ ] `README.md`: the `init` comment, the skills table and the paragraph under it, and the
      refresh recipe
- [ ] `scripts/build.sh`: the new `SKILL.md` is a wheel member

### Phase 3: the tests

Unit tier, over the real files, in the pattern already there.

- [ ] `tests/unit/test_resources.py`: the expected skill names and the expected documents both
      gain the new one, and the index-0 assertion is corrected or still holds
- [ ] `tests/unit/test_cli_docs_init.py`: the installed skill count
- [ ] Every cause class the document defines appears in the skill, read out of the document's own
      table so no class is spelled in the test
- [ ] Every finding kind `verdict.py` emits appears in the document, so a new kind has to land in
      a cause class
- [ ] The default hypothesis and the approval rule are in both files
- [ ] `cowork-evals` carries no `## Reading a failure` and the new skill does, which pins the
      split so a later edit cannot put it back
- [ ] `scripts/lint.sh` and `scripts/test.sh` pass

### Phase 4: the index

- [ ] [`README.md`](README.md): the row, the count, and the paragraph. Written when the plan file
      is written, so the index never names a plan that does not exist
- [ ] The status is moved off `not started` on the first tick above, and the row is corrected in
      the same commit

### Phase 5: verification

- [ ] `scripts/lint.sh`, `scripts/test.sh`, `scripts/build.sh`
- [ ] `cowork_evals docs eval_triage` resolves in an install and in a checkout
- [ ] In a consumer repository, a session shown a failing run reads the verdict, opens the
      evidence, proposes one line per finding, changes no file before approval, and hands back
      the command to re-run rather than running it
- [ ] The same session, given a finding the evidence does not decide, says so instead of choosing
      a cause
- [ ] The same session, shown a passing run, proposes nothing
- [ ] The integration tier, at the end and after the merge, as
      [`../tests/README.md`](../tests/README.md) requires
