# Run validity: a run that never executed the tool fails instead of scoring

One run is one execution of one case: what `runs: N` counts, what the gate prints as
`run N`, and what gets a directory at `traces/<case>/run-<n>/`. A whole `cowork_evals run`
is an invocation, and this plan never calls one a run.

A run in which the agent never got the tool it needed is not a measurement of the plugin. It
is a measurement of this repository's configuration, and it is scored like any other run.
Measured on 2026-09-12 and recorded in [`../docs/running_evals.md`](../docs/running_evals.md):
a `Write` call the permission mode refused left a record in the trace and the run still
scored, and a shell tool that was never offered left no record at all and the run still
scored.

This plan makes such a run fail loudly, makes the summary counts honest, and states the kept
artefact layout as a contract that a consumer's post-suite content checker reads.

The rule it implements, and what it follows from, is the decisions table in
[`plan_believable_results.md`](plan_believable_results.md). Do not re-derive it here.

Branch: `feat/run-validity`.

## What this plan does not do

| Not in scope                                                     | Where it is instead                        |
| ----------------------------------------------------------------- | -------------------------------------------- |
| Merging a verdict produced outside the harness into the result document | Nowhere. Deferred by the problem report's own recommendation |
| The content checker that reads the kept workspace                | Outside this package. This repository is a library: [`../docs/library.md`](../docs/library.md) |
| The baseline arm, and anything reading a second arm               | [`plan_ablation.md`](plan_ablation.md)      |
| The backend declaration on a case                                | [`plan_runnability.md`](plan_runnability.md) |
| The tool grant                                                   | Already done. `eval.allow_tools` is the session mirror in [`../docs/running_evals.md`](../docs/running_evals.md) |

The grant was the rider this plan was going to carry. It landed on 2026-09-12 instead,
because a validity check over a grant this repository got wrong would redden every suite for
its own misconfiguration. There is nothing left of it here.

## What an exclusion glob turned out to be

`plan_believable_results.md` decided that report item 5 splits into a backend declaration and
an exclusion glob typed on one invocation. The declaration is
[`plan_runnability.md`](plan_runnability.md). The glob is not built, and the reason is a fact
about the harness rather than a judgement.

`claude plugin eval --case <glob>` takes one glob over the case name, supporting `*` and `?`
and nothing else. It has no negation, it takes no list, and `--tag` includes only. On the
Docker backend the harness discovers and selects, so this package has nothing to filter: it
can only hand the harness one glob. Expressing an exclusion there would mean one harness
invocation per case, which is one result document per case, which breaks the one document per
plugin the log layout and the gate both rest on.

So the exclusion is dropped and the other half of that rider is built: the counts say how
many cases were discovered, how many were selected and how many ran, which is what makes a
filtered or truncated sweep readable. Phase 5 writes the fact into
[`../docs/cli.md`](../docs/cli.md) so that the next person does not re-derive it.

## Orientation

| Fact                                                    | Where                                              |
| --------------------------------------------------------- | ---------------------------------------------------- |
| The kept trace, and the one pass that reads it            | `src/cowork_evals/traces.py`, `collect`, `last_message` |
| The gate, and the one arm it reads                        | `src/cowork_evals/gate.py`, `ARM`, `_judge_run`      |
| The summary line                                          | `src/cowork_evals/gate.py`, `_Totals.summary`        |
| Case discovery, tags and the case glob                    | `src/cowork_evals/cases.py`, `discover`              |
| Where the CLI selects, validates and calls the gate       | `src/cowork_evals/cli.py`, `_run`, `_validate`       |
| The result document this repository writes                | `src/cowork_evals/results.py`                        |
| The kept artefact layout, and the gate table              | [`../docs/running_evals.md`](../docs/running_evals.md) |
| What a harness trace holds, record type by record type    | [`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md) |

## Phases

### Phase 1: measure the denial record

Done on 2026-09-12, before this plan was written. The record is real, it is reproducible, and
its fields are recorded in [`../docs/running_evals.md`](../docs/running_evals.md) with the
four runs that produced them. Nothing in this phase is outstanding.

- [x] The record, from a container run granted `Bash` alone whose case asked for a `Write`
      call:
      `{"type":"system","subtype":"permission_denied","tool_name":"Write","tool_use_id":"...","decision_reason_type":"mode","message":"..."}`
- [x] An ungranted tool fails in two ways, not one. It is offered and refused at the call,
      which writes that record, or it is not offered at all, which writes nothing and leaves
      the model to say in prose that it could not do the thing
- [x] The second way is still detectable: the `system` record of subtype `init` carries the
      run's whole offered tool list, so a configured grant can be held against it
- [x] `Skill` is not what the old grant denied. A skill fired and scored under `Bash` alone

### Phase 2: the check

Two checks, because phase 1 found two failure modes. Both read the kept trace, and both put
their finding into the result document so that the gate keeps reading one thing.

- [ ] `traces.py` scans each kept trace in the same pass that already reads it for
      `last_message`. One read of one file, not three
- [ ] Check one, the denial. Every `system` record of subtype `permission_denied` carrying
      `decision_reason_type: mode` yields its `tool_name`
- [ ] Check two, the silent absence. The `system` `init` record's `tools` list is held
      against the grant the run was given, and every granted tool missing from it yields its
      name. The run's grant reaches the scan from `RunOptions`, which the backend already
      holds, rather than being re-read from configuration
- [ ] Both findings go into that run's entry in the result document, as this repository's own
      added fields beside the `tracePath` rewrite `collect` already does. Each is absent when
      empty, so a healthy document is unchanged
- [ ] `gate.py` fails a run carrying either, one line each, naming the tools and carrying the
      `[artifacts: ...]` suffix every line somebody investigates already carries
- [ ] A denial from a plugin's own hook does not gate. Check one matches on the reason type
      and never on the tool name
- [ ] Nothing changes on the CoWork backend. A session has no permission mode and no `init`
      record, both fields never appear, and one gate still covers both backends
- [ ] A run that hit its turn cap or timed out already carries `error` and already gates.
      Confirm that against the gate table and add nothing

### Phase 3: honest counts

The summary line lies in two ways, and one of them needs no truncation at all. Measured
2026-09-12: a `cowork_evals run --docker plugins/smoke --allow-tools Read` whose only grader
failed printed `FAIL ...` and then `1 cases, 1 passed, overall score 0.00` on the next line.
`casesPassed` is the harness's rule, a case scoring at or above the threshold, and the
threshold is pinned to 0 so that the gate decides instead. Every case therefore counts as
passed in that line whatever the gate said. The truncated sweep the report describes is the
second way.

The exit code is right in both. The summary line is what lies.

- [ ] The CLI already discovers the case tree in its preflight. It passes the discovered
      count and the selected count into the gate, the way it already passes `extra`
- [ ] The summary line names four numbers: discovered, selected, ran, and how many the gate
      passed, with the overall score after them. `passed` is the gate's own count and never
      `casesPassed`, which counts a case the gate failed
- [ ] A document carrying `partial: true` makes the summary say the sweep was truncated and
      name the reason, so the last line a person reads says it as well as the failure line
- [ ] Selected and ran differing is not itself a failure. On the Docker backend the harness
      discovers and this package's count is a second opinion, so the two are printed and
      neither is asserted against the other

### Phase 4: the kept artefact layout, as a contract

Documentation only. No code changes in this phase.

- [ ] [`../docs/running_evals.md`](../docs/running_evals.md) states the layout a consumer's
      post-suite content checker reads: the exact path per run, one directory per run, the
      three names in it, and that the tree is read-only
- [ ] The same section states that `home/` and `tmp/` inside a kept sandbox are sealed on
      purpose, that `logs.unseal` is what opens them, and that a checker reads the collected
      `workspace/` rather than a sandbox
- [ ] It states what is out of scope and stays out: nothing merges a verdict produced outside
      the harness into the result document, so a checker's finding does not gate

### Phase 5: what selection can and cannot say

Documentation only.

- [ ] [`../docs/cli.md`](../docs/cli.md) records that `--case` takes one glob over the case
      name, that `--tag` includes only, and that neither can express an exclusion, with the
      harness reference as the source
- [ ] It records the one route that does exist: a case a person wants out of a sweep carries
      a tag of its own and the sweep selects on tags

### Phase 6: tests

Unit tier throughout. Nothing here needs a model.

- [ ] A trace holding a mode denial yields the tool names, over a fixture trace written in
      the test
- [ ] A trace holding a hook denial yields none
- [ ] A trace whose `init` list is missing a granted tool yields that tool's name
- [ ] A trace whose `init` list carries every granted tool yields none
- [ ] A trace with no `init` record yields none, because a run that wrote none says nothing
      about its tools
- [ ] A trace holding neither finding yields neither, and the document is byte for byte what
      it was
- [ ] The gate fails a document whose run carries the field, and the line names the tools and
      the artefacts directory
- [ ] The gate passes a document with no such field, so an old document reads as it did
- [ ] The summary line carries the four counts, and says truncated on a partial document
- [ ] Every existing gate test still passes unchanged, or its change is in the same commit
      with the reason in the message

### Phase 7: documentation

- [ ] The gate table in [`../docs/running_evals.md`](../docs/running_evals.md) carries the
      new condition
- [ ] The summary line's four counts are stated where that file describes the gate's last
      line
- [ ] The added result-document field is stated where that file describes what this
      repository writes into the harness's document, beside the `tracePath` rewrite
- [ ] [`../docs/approaches.md`](../docs/approaches.md) says that the check is a Docker
      backend fact, because CoWork has no permission mode
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 8: integration

- [ ] `plugins/smoke/` on the Docker backend, from the integration tier, green
- [ ] A fixture case asking for a `Write` call, granted `Bash` alone, from the integration
      tier, red, with the failure line naming `Write`. That is the run phase 1 already made
      by hand
- [ ] `scripts/test.sh` and `ruff` clean
