# Run validity: do not score an eval the model could not have passed

## The problem

An eval gives a plugin a score. That score can be wrong, and the output does not say so.

There are two ways it goes wrong.

**The model did not have the tool.** A case asks it to write a file. The container decides
which tools the model gets, and `Write` is not among them. The model replies that it cannot
write files. The grader checks that reply against its pattern and produces a score. The score
is about the tool list, not about the plugin. It is usually 0, and it is 1 if the pattern
happens to match the reply.

This happens in two forms. Either the tool is in the list and the container refuses the call,
which puts a record in the trace, or the tool is not in the list at all and the model never
tries, which puts nothing in the trace. Both are described in
[`../docs/running_evals.md`](../docs/running_evals.md).

**The last line disagrees with the lines above it.** The gate prints one line per failure and
then a summary. The summary takes its pass count from the harness's result file, which counts
a case as passed if its score is at or above a threshold we set to 0. So it is every case,
always. The gate can print a failure and then say every case passed.

## What this plan does

Three things.

Read each run's trace. If the model never got the tool, fail the eval instead of scoring what
it wrote without it.

Make the summary line report what the gate decided, and say when a sweep stopped early.

Write down where a run's files are kept. A consumer wants to check what an eval actually
produced, such as whether the `.pptx` a skill wrote will open, so they write their own script
over those files. That script needs a layout that does not move.

Why an eval fails on one kind of refusal and not another is the decisions table in
[`plan_believable_results.md`](plan_believable_results.md). Do not work it out again here.

Branch: `feat/run-validity`.

## What this plan does not do

| Not in scope                                                     | Where it is instead                        |
| ----------------------------------------------------------------- | -------------------------------------------- |
| Merging a verdict produced outside the harness into the result file | Nowhere. Nobody has asked for it |
| The content checker that reads the kept workspace                | Outside this package. This repository is a library: [`../docs/library.md`](../docs/library.md) |
| The baseline arm, and anything reading a second arm               | [`plan_ablation.md`](plan_ablation.md)      |
| The backend declaration on a case                                | [`plan_runnability.md`](plan_runnability.md) |
| The tool grant                                                   | Already done. `eval.allow_tools` is the session mirror in [`../docs/running_evals.md`](../docs/running_evals.md) |

The grant was going to be part of this plan. It was done first and separately, because a
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

### Phase 1: what the trace says when a tool is missing

Already done, and written into
[`../docs/running_evals.md`](../docs/running_evals.md). Read it there; it is not repeated
here. In short: a refused call leaves one record naming the tool and why it was refused, a
tool that was never offered leaves nothing, and the run's opening record lists every tool the
model was given, which is what the second case is caught with.

- [x] All of it, in that file

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

It can print a failure and then, on the very next line, say every case passed. The count
comes from `casesPassed` in the result file, which the harness sets for any case scoring at
or above `--threshold`. We pin that threshold to 0 so our own gate decides instead, so every
case counts as passed there, always.

The other way: a sweep the cost ceiling stopped early still reads as if every case ran.

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
      tier, fails, and the line names `Write`
- [ ] `scripts/test.sh` and `ruff` clean
