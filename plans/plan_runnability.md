# Runnability: a case that cannot run on a backend says so, and is not counted as a failure

## The problem

Some cases cannot run on CoWork. A case that caps the number of turns, picks a model, stages
files into the workspace, or leans on the harness's MCP stand-ins, is asking for something a
live CoWork session does not offer.

Right now the backend works this out while the suite is running and skips the case, and the
suite fails because a case was skipped. Failing on a skip is right in general: a skip is how
a backend goes green by honouring nothing, so a skip that never fails is a backend that
cannot be caught doing it. What the rule cannot do is tell that skip apart from a case nobody
could ever run here.

So the case is fine, the backend is fine, the rule is doing what it was built to do, and the
suite is red every time it runs. There is nothing to fix, so people learn to ignore the red.

There is also no way to tell from the case itself. To know that a case cannot run on CoWork,
you have to read this package's source.

## What this plan does

Put a tag on the case: `no-cowork`.

The validator checks it both ways, so a case that needs the tag and does not have it is an
error, and so is a case that has the tag but would have run fine. The second check is what
stops the tag becoming a way to quietly switch a case off.

The CoWork backend reads the tag instead of working it out mid-run, and such a case is counted
instead of failing the suite.

A tag and not a new frontmatter key, decided and not reopened here. `tags:` is already
free-form and the harness only filters on it, while an unknown `prompt.md` frontmatter key is
refused at load and the whole suite then writes no result document. That measurement is in
[`../docs/eval_format.md`](../docs/eval_format.md). A new key would risk the Docker backend
rejecting every case that carried it.

Branch: `feat/runnability`.

## The tag

`no-cowork`, in the `tags:` list a case already carries.

| Property              | Value                                                             |
| --------------------- | ----------------------------------------------------------------- |
| Spelling              | `no-cowork`, reserved, and no other reserved tag exists           |
| Where                 | `tags:` in `prompt.md`, beside the `<skill>` tag already required |
| On the Docker backend | Nothing. It is a tag, and the harness filters on tags it is given |
| On the CoWork backend | The case is not submitted, and is counted rather than failed      |
| Counterpart           | None. There is no `no-docker`, and the decisions table says why   |

A case carrying it is still selected by `--tag <skill>`, because a case carries both tags.

## What makes a case unrunnable

`cowork_backend.skips` decides a case skip from three sources, not one. The tag declares all
three, and the validator reads all three.

| Source                                         | Written in                         | Why a session cannot honour it                                 |
| ---------------------------------------------- | ---------------------------------- | -------------------------------------------------------------- |
| A key in `UNHONOURED_CASE_KEYS`                | `prompt.md` frontmatter            | Each key carries its own reason in that mapping                |
| A key under `CONTEXT_PREFIX`                   | `case.yaml`                        | Nothing stages files into the VM                               |
| A `mocks/` directory on the case's layer chain | `evals/mocks/`, or beside the case | Stand-ins are the harness's, and the MCP servers here are real |

The third is a directory and not a key, and the case that inherits it may be several
directories below. It is tagged at each case rather than at the directory, which is explicit
where a reader is looking and survives the case being moved. A plugin
whose `evals/mocks/` covers every case therefore tags every case.

One function decides unrunnability, and the validator and the backend both call it. Deriving
the same fact twice is what lets the two disagree, and a validator that passed a case the
backend then declared would put the suite back where this plan found it.

## Both directions

The validator reports each of these, and `run` exits 3 on either.

| The case                                                  | Why it is an error                                                    |
| --------------------------------------------------------- | --------------------------------------------------------------------- |
| Carries any source in the table above, and no `no-cowork` | The fact is true and unreadable, which is the state this plan removes |
| Carries `no-cowork` and no source in the table above      | The tag is then a silencer, excluding a case that would have run      |

The second direction is the whole point. Without it the tag is a `skip:` field wearing
another name, and there is no `skip:` field in a case tree and will not be one: it is a
permanent silent pass that outlives whoever wrote it, and `CLAUDE.md` already says never
skip.

## The one run-time skip that stays

An `llm` grader whose focus turns out to be an image. The file is produced by the run, so
nothing before the run can know. It stays a grader skip decided after the run, exactly as
[`../docs/cowork_backend.md`](../docs/cowork_backend.md) records it, and it still fails the
run.

Every other skip in `cowork_backend.skips` becomes a validator error or a counted case.

## What this plan does not do

| Not in scope                               | Where it is instead                                                |
| ------------------------------------------ | ------------------------------------------------------------------ |
| An exclusion glob on the invocation        | Not built. [`plan_run_validity.md`](plan_run_validity.md) says why |
| A `no-docker` counterpart                  | Nowhere. Nothing names a case key the Docker backend cannot honour |
| Failing a run that never executed its tool | [`plan_run_validity.md`](plan_run_validity.md)                     |
| The baseline arm                           | [`plan_ablation.md`](plan_ablation.md)                             |

## Orientation

| Fact                                                                              | Where                                                                          |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| What a CoWork run cannot honour, key by key                                       | `src/cowork_evals/cowork_backend.py`, `UNHONOURED_CASE_KEYS`, `CONTEXT_PREFIX` |
| Where a case skip is decided today, all three sources                             | `src/cowork_evals/cowork_backend.py`, `skips`, `_mock_layers`, `_run_case`     |
| The frontmatter key set, and the tag rule                                         | `src/cowork_evals/validate.py`, `PROMPT_KEYS`, `_prompt_violations`            |
| Where the validator already holds the plugin root a `mocks/` chain is walked from | `src/cowork_evals/validate.py`, `_case_violations`                             |
| Discovery, tags and the case glob                                                 | `src/cowork_evals/cases.py`, `discover`                                        |
| Where a skipped case is failed                                                    | `src/cowork_evals/verdict.py`, `_judge_case`                                   |
| The document's `skipped` and `casesPassed`                                        | `src/cowork_evals/results.py`, `_aggregates`                                   |
| The key-by-key skip rule, and that a skip fails the run                           | [`../docs/running_evals.md`](../docs/running_evals.md)                         |
| What each backend honours                                                         | [`../docs/approaches.md`](../docs/approaches.md)                               |

## Phases

### Phase 1: the tag, read and written

- [ ] `cases.py` names the reserved tag in one place and exposes whether a case carries it.
      No other module spells the string
- [ ] `cowork_backend` exposes the reasons a case is unrunnable, all three sources, as the
      one function both the validator and the backend call. It takes the case and the plugin
      root, which is what `_mock_layers` already needs, and it is what `skips` reads today
- [ ] `validate.py` enforces both directions of the table above over that function, one rule
      name each. The message names what makes the case unrunnable: the key, or the `mocks/`
      directory as a path
- [ ] A case carrying the tag is still selected by `--tag <skill>`, and a test says so
- [ ] The tag is not added to `PROMPT_KEYS`. It is a tag value, not a key, so nothing about
      the key set changes

### Phase 2: the backend reads it

- [ ] `cowork_backend.skips` stops turning any of the three sources into a case skip. It
      still reads them, through the function phase 1 exposed, because the validator enforces
      direction one over the same reasons
- [ ] A case carrying the tag is not submitted, and produces a case entry saying it was not
      run on this backend, with the tag as the reason
- [ ] The entry is not a skip. It carries a field of this repository's own, distinct from
      `skipped`, so a reader and `verdict.py` can tell a declared case from a skipped one
- [ ] `plan.submissions` counts it as zero, so the rate ceiling arithmetic is unchanged
- [ ] Nothing changes on the Docker backend

### Phase 3: a declared case is counted

- [ ] A case declared unrunnable on the backend that ran is counted, never failed
- [ ] A case reporting `skipped` still fails, so the one run-time grader skip and every
      harness skip fail exactly as they did
- [ ] The summary line names how many cases were declared unrunnable, beside the counts
      [`plan_run_validity.md`](plan_run_validity.md) put there, so a counted case is visible
      rather than silently absent
- [ ] A declared case leaves all four numbers in `results._aggregates`, not one. It is out of
      `casesTotal`, out of `casesPassed`, and out of both means. Subtracting it from
      `casesTotal` alone would leave it counted as passed, because `casesPassed` counts a
      case that is not `skipped` and a declared case is not skipped, and would leave its 0.0
      dragging `overallScore` down for a case that never ran
- [ ] A suite whose every case is declared reports zero cases and a score of 0.0, which is
      the same shape `_aggregates` already produces for a suite of no cases at all

### Phase 4: tests

Unit tier throughout, except the last box.

- [ ] Direction one, once per source: a case writing `max_turns`, a case writing a
      `context.*` key, and a case under an `evals/mocks/` directory, each without the tag, is
      a violation naming what made it unrunnable
- [ ] Direction two: a case carrying the tag and carrying no source is a violation
- [ ] A case writing `max_turns` and carrying the tag is valid
- [ ] A case whose only source is an `evals/mocks/` directory several layers above it, and
      which carries the tag, is valid. The chain is walked from the plugin root, not from the
      case's own directory
- [ ] A case carrying the tag is still returned by a `--tag <skill>` selection
- [ ] The CoWork backend submits nothing for a declared case, and the driver is never called
- [ ] A document whose only case is declared passes, and the summary says so
- [ ] A document whose case reports `skipped` still fails
- [ ] `_aggregates` over one declared case reports zero cases, zero passed and a score of 0.0
- [ ] One `plugins/smoke/` fixture case carrying the tag, run on `--cowork` from the
      integration tier, green and counted. It writes `max_turns`, so it satisfies direction
      two, and it runs on Docker unchanged

### Phase 5: documentation

Five documents, and the rule that a skip fails the run is amended in one of them.

- [ ] [`../docs/eval_format.md`](../docs/eval_format.md): the reserved tag, all three sources
      that require it, both directions, and that `tags:` is where it lives
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): the key-by-key table stops
      saying `Skipped` for a key the case writes out and says the case declares it instead.
      The pass and fail table gains the counted condition. The rule that a skip fails the
      run stays, and is narrowed to say what is still a skip
- [ ] [`../docs/approaches.md`](../docs/approaches.md): the honoured-feature table says a
      case declares what this backend cannot run
- [ ] [`../docs/cowork_backend.md`](../docs/cowork_backend.md): the added field, that a
      `mocks/` directory is declared per case and not per directory, and that the image-focus
      grader skip is the one skip this backend still decides after a run
- [ ] [`../plugins/README.md`](../plugins/README.md): the fixture case phase 4 adds
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 6: integration

- [ ] `plugins/smoke/` on both backends, from the integration tier, green
- [ ] `scripts/test.sh` and `ruff` clean
