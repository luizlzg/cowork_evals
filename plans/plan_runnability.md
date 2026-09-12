# Runnability: a case that cannot run on a backend says so, and is not counted as a failure

## The problem

Some cases cannot run on CoWork. A case that caps the number of turns, or picks a model, or
stages files into the workspace, is asking for something a live CoWork session does not
offer.

Right now the backend works this out while the suite is running, skips the case, and the gate
fails the suite because a case was skipped. The case is fine, the backend is fine, and the
suite is red every time it runs. There is nothing to fix, so people learn to ignore the red.

There is also no way to tell from the case itself. To know that a case cannot run on CoWork,
you have to read this package's source.

## What this plan does

Put a tag on the case: `no-cowork`.

The validator checks it both ways, so a case that needs the tag and does not have it is an
error, and so is a case that has the tag but would have run fine. The second check is what
stops the tag becoming a way to quietly switch a case off.

The CoWork backend reads the tag instead of working it out mid-run, and the gate counts such
a case instead of failing the suite.

Why a tag rather than a new frontmatter key is in the decisions table in
[`plan_believable_results.md`](plan_believable_results.md), and the fact it rests on is in
[`../docs/eval_format.md`](../docs/eval_format.md).

Branch: `feat/runnability`.

## The tag

`no-cowork`, in the `tags:` list a case already carries.

| Property                  | Value                                                            |
| ------------------------- | ------------------------------------------------------------------ |
| Spelling                  | `no-cowork`, reserved, and no other reserved tag exists           |
| Where                     | `tags:` in `prompt.md`, beside the `<skill>` tag already required |
| On the Docker backend     | Nothing. It is a tag, and the harness filters on tags it is given |
| On the CoWork backend     | The case is not submitted, and is counted rather than failed      |
| Counterpart               | None. There is no `no-docker`, and the decisions table says why   |

A case carrying it is still selected by `--tag <skill>`, because a case carries both tags.

## Both directions

The validator reports each of these, and `run` exits 3 on either.

| The case                                                            | Why it is an error                                  |
| --------------------------------------------------------------------- | ----------------------------------------------------- |
| Writes a key the CoWork backend cannot honour, and carries no `no-cowork` | The fact is true and unreadable, which is the state this plan removes |
| Carries `no-cowork` and writes nothing the CoWork backend cannot honour | The tag is then a silencer, excluding a case that would have run |

The second direction is the whole point. Without it the tag is a `skip:` field wearing
another name, and `plan_believable_results.md` refused that.

## The one run-time skip that stays

An `llm` grader whose focus turns out to be an image. The file is produced by the run, so
nothing before the run can know. It stays a grader skip decided after the run, exactly as
[`../docs/cowork_backend.md`](../docs/cowork_backend.md) records it, and it still fails the
gate.

Every other skip in `cowork_backend.skips` becomes a validator error or a counted case.

## What this plan does not do

| Not in scope                                            | Where it is instead                           |
| --------------------------------------------------------- | ----------------------------------------------- |
| An exclusion glob on the invocation                     | Not built. [`plan_run_validity.md`](plan_run_validity.md) says why |
| A `no-docker` counterpart                               | Nowhere. Nothing names a case key the Docker backend cannot honour |
| Failing a run that never executed its tool              | [`plan_run_validity.md`](plan_run_validity.md) |
| The baseline arm                                        | [`plan_ablation.md`](plan_ablation.md)         |

## Orientation

| Fact                                                   | Where                                                    |
| --------------------------------------------------------- | ---------------------------------------------------------- |
| What a CoWork run cannot honour, key by key              | `src/cowork_evals/cowork_backend.py`, `UNHONOURED_CASE_KEYS`, `CONTEXT_PREFIX` |
| Where a case skip is decided today                       | `src/cowork_evals/cowork_backend.py`, `skips`, `_run_case` |
| The frontmatter key set, and the tag rule                | `src/cowork_evals/validate.py`, `PROMPT_KEYS`, `_prompt_violations` |
| Discovery, tags and the case glob                        | `src/cowork_evals/cases.py`, `discover`                   |
| The gate's skip condition                                | `src/cowork_evals/gate.py`, `_judge_case`                 |
| The document's `skipped` and `casesPassed`               | `src/cowork_evals/results.py`, `_aggregates`              |
| The key-by-key skip rule, and that a skip gates          | [`../docs/running_evals.md`](../docs/running_evals.md)    |
| What each backend honours                                | [`../docs/approaches.md`](../docs/approaches.md)          |

## Phases

### Phase 1: the tag, read and written

- [ ] `cases.py` names the reserved tag in one place and exposes whether a case carries it.
      No other module spells the string
- [ ] `validate.py` enforces both directions of the table above, one rule name each, and the
      message names the key that makes the case unrunnable
- [ ] A case carrying the tag is still selected by `--tag <skill>`, and a test says so
- [ ] The tag is not added to `PROMPT_KEYS`. It is a tag value, not a key, so nothing about
      the key set changes

### Phase 2: the backend reads it

- [ ] `cowork_backend.skips` stops deciding a case skip from `UNHONOURED_CASE_KEYS`. The keys
      stay, because the validator reads them to enforce direction one
- [ ] A case carrying the tag is not submitted, and produces a case entry saying it was not
      run on this backend, with the tag as the reason
- [ ] The entry is not a skip. It carries a field of this repository's own, distinct from
      `skipped`, so a reader and the gate can tell a declared case from a skipped one
- [ ] `plan.submissions` counts it as zero, so the rate ceiling arithmetic is unchanged
- [ ] Nothing changes on the Docker backend

### Phase 3: the gate counts it

- [ ] A case declared unrunnable on the backend that ran is counted, never failed
- [ ] The gate still fails a case reporting `skipped`, so the one run-time grader skip and
      every harness skip gate exactly as they did
- [ ] The summary line names how many cases were declared unrunnable, so a counted case is
      visible rather than silently absent
- [ ] `results._aggregates` subtracts a declared case from `casesTotal` the way it already
      subtracts a skipped one from `casesPassed`, so a suite of one declared case does not
      read as a suite that ran

### Phase 4: tests

Unit tier throughout, except the last box.

- [ ] Direction one: a case writing `max_turns` without the tag is a violation naming
      `max_turns`
- [ ] Direction two: a case carrying the tag and writing nothing unhonourable is a violation
- [ ] A case writing `max_turns` and carrying the tag is valid
- [ ] A case carrying the tag is still returned by a `--tag <skill>` selection
- [ ] The CoWork backend submits nothing for a declared case, and the driver is never called
- [ ] The gate passes a document whose only case is declared, and the summary says so
- [ ] The gate still fails a document whose case reports `skipped`
- [ ] One `plugins/smoke/` fixture case carrying the tag, run on `--cowork` from the
      integration tier, green and counted

### Phase 5: documentation

Four documents, and the rule that a skip gates is amended in one of them.

- [ ] [`../docs/eval_format.md`](../docs/eval_format.md): the reserved tag, both directions,
      and that `tags:` is where it lives
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): the key-by-key table stops
      saying `Skipped` for a key the case writes out and says the case declares it instead.
      The gate table gains the counted condition. The rule that a skip gates stays, and is
      narrowed to say what is still a skip
- [ ] [`../docs/approaches.md`](../docs/approaches.md): the honoured-feature table says a
      case declares what this backend cannot run
- [ ] [`../docs/cowork_backend.md`](../docs/cowork_backend.md): the added field, and that the
      image-focus grader skip is the one skip this backend still decides after a run
- [ ] [`../plugins/README.md`](../plugins/README.md): the fixture case phase 4 adds
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 6: integration

- [ ] `plugins/smoke/` on both backends, from the integration tier, green
- [ ] `scripts/test.sh` and `ruff` clean
