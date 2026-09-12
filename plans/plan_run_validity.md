# Run validity: an eval that never got its tool fails instead of scoring

An eval sends a prompt to a model and grades the answer. If the model never got a tool it
needed, that answer says something about this repository's configuration and nothing about
the plugin. It is scored anyway.

Two ways that happens, both measured on 2026-09-12 and recorded in
[`../docs/running_evals.md`](../docs/running_evals.md). A `Write` call the permission mode
refused left a record in the trace, and the eval scored. A shell tool that was never offered
left no record at all, and the eval scored.

This plan fails those evals, stops the summary line contradicting the failures printed above
it, and states the kept artefact layout as a contract a consumer's content checker reads.

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

The grant was going to be part of this plan. It was done on 2026-09-12 instead, because a
check for a tool the model never got would fail every eval in the suite while the grant
itself was still wrong.

## Skipping a case with a glob is not possible

`plan_believable_results.md` planned an option to exclude a case from one command, so that
nobody has to move the case directory. It cannot be built.

`claude plugin eval --case <glob>` takes one glob matching the case name, with `*` and `?`.
There is no negation and no list, and `--tag` only includes. On Docker the harness finds and
picks the cases, so this package has nothing to filter: it hands over one glob and that is
all. Excluding a case would mean calling the harness once per case, which writes one result
file per case, and the log layout and the gate both expect one per plugin.

So the option is dropped. What is built instead is the counts: how many cases were found, how
many were picked, and how many ran. Phase 5 writes this into
[`../docs/cli.md`](../docs/cli.md) so nobody works it out again.

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

Two checks, one per failure mode. Both read the trace the run already kept, and both write
what they found into the result file, so the gate still reads only that file.

- [ ] `traces.py` reads each kept trace once, for the final message as it does now and for
      both checks
- [ ] Check one: every `permission_denied` record whose `decision_reason_type` is `mode`
      gives up its `tool_name`
- [ ] Check two: the `init` record lists the tools the run offered the model. Every granted
      tool missing from that list is named. The grant comes from `RunOptions`, which the
      backend already has, and is not read from the config file again
- [ ] Both go into that run's entry in the result file, beside the `tracePath` that `collect`
      already rewrites. Neither is written when there is nothing to write, so a healthy file
      is unchanged
- [ ] `gate.py` fails a run carrying either, one line each, naming the tools and the
      directory holding that run's trace
- [ ] A denial from the plugin's own hook does not fail anything. Check one matches on the
      reason, never on the tool name
- [ ] Nothing changes on CoWork. A session has no permission mode and writes no tool list, so
      neither field ever appears and one gate still covers both backends
- [ ] A run that hit its turn cap or timed out already carries `error` and already fails.
      Check that against the gate table and add nothing

### Phase 3: honest counts

The last line the gate prints says how many cases passed, and it is wrong twice.

Measured 2026-09-12. `cowork_evals run --docker plugins/smoke --allow-tools Read`, one case,
its only grader failed. It printed `FAIL ...` and then, on the next line,
`1 cases, 1 passed, overall score 0.00`. The count comes from `casesPassed` in the result
file, which the harness sets for any case scoring at or above `--threshold`, and we pin that
threshold to 0 so our own gate decides instead. So every case counts as passed there, always.

The second way is the one in the report: a sweep the cost ceiling stopped early still reads
as if every case ran.

The exit code is right in both. Only the line is wrong.

- [ ] The command already reads the case tree before it runs anything. It hands the gate two
      numbers, how many cases it found and how many it picked, the way it already hands over
      `extra`
- [ ] The line names four numbers: found, picked, ran, passed, then the score. `passed` is
      the gate's own count, never `casesPassed`
- [ ] A result file marked `partial` makes the line say the sweep stopped early and why
- [ ] Picked and ran differing is not a failure. The harness counts one and this package
      counts the other, so both are printed and neither is checked against the other

### Phase 4: write down what a run leaves on disk

Documentation only. No code.

Every run keeps its transcript, its final message and its working directory. A consumer
writes their own checker over that, to look at the files an eval produced, so the layout has
to be something they can rely on.

- [ ] [`../docs/running_evals.md`](../docs/running_evals.md) gives the path, one directory
      per run, the three names in it, and that nothing here writes into it afterwards
- [ ] It says that `home/` and `tmp/` inside a kept sandbox are locked at mode 000 on
      purpose, that `logs.unseal` opens them, and that a checker should read the collected
      `workspace/` instead
- [ ] It says that a checker's verdict does not reach the result file and does not fail
      anything. That stays out until somebody asks for it

### Phase 5: write down that you cannot exclude a case

Documentation only.

- [ ] [`../docs/cli.md`](../docs/cli.md) says that `--case` takes one glob over the case name
      and `--tag` only includes, so neither can leave a case out, and points at the harness
      reference for it
- [ ] It gives the one thing that does work: put a tag on the case and select on tags

### Phase 6: tests

Unit tier throughout. Nothing here needs a model.

- [ ] A trace holding a mode denial yields the tool names, over a fixture trace written in
      the test
- [ ] A trace holding a hook denial yields none
- [ ] A trace whose `init` list is missing a granted tool yields that tool's name
- [ ] A trace whose `init` list carries every granted tool yields none
- [ ] A trace with no `init` record yields none. A run that wrote no tool list says nothing
      about what it had
- [ ] A trace with neither problem yields neither, and the result file is unchanged
- [ ] The gate fails a result file carrying either field, and the line names the tools and
      the directory holding the trace
- [ ] The gate passes a result file with neither, so a file written before this existed reads
      as it did
- [ ] The last line carries the four counts, and says so when a sweep stopped early
- [ ] Every gate test that already exists still passes, or its change goes in the same commit
      with the reason in the message

### Phase 7: documentation

- [ ] The gate table in [`../docs/running_evals.md`](../docs/running_evals.md) gains the new
      condition
- [ ] The same file says what the four counts on the last line mean
- [ ] It says what the two new fields in the result file are, next to where it describes the
      `tracePath` rewrite
- [ ] [`../docs/approaches.md`](../docs/approaches.md) says this check is Docker only,
      because CoWork has no permission mode
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 8: run it for real

- [ ] `plugins/smoke/` on Docker, from the integration tier, passes
- [ ] A case asking for a `Write` call under a grant without `Write`, from the integration
      tier, fails, and the line names `Write`. Phase 1 already ran this by hand
- [ ] `scripts/test.sh` and `ruff` clean
