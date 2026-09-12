# Run validity: do not score an eval the model could not have passed

## The problem

An eval gives a plugin a score. That score can be wrong, and the output does not say so.

There are two ways it goes wrong.

**The model did not have a tool it needed.** It says so in its reply, the grader scores that
reply, and the score comes out as a fact about the plugin. It is usually 0, and it is 1 if
the grader's pattern happens to match the refusal.

The default grant is not the cause of this, and the basic tools are in it.
`eval.allow_tools` mirrors what a CoWork session can do: `Bash Read Glob Grep Write Edit
WebFetch Skill`.

A run loses a tool anyway, and which way decides whether this plan can catch it. The two
forms are measured in [`../docs/running_evals.md`](../docs/running_evals.md).

| The tool was                                    | The trace holds                        | Caught by |
| ----------------------------------------------- | -------------------------------------- | --------- |
| Granted, and the call refused                   | a `permission_denied` record naming it | check one |
| Granted, and never offered to the model         | an `init` list missing it              | check two |
| Never granted, so never offered and never tried | nothing                                | neither   |

The third row is the bound on this plan and it is not closable. Both checks start from the
grant, so a tool nobody granted is a tool nothing here knows the case wanted. That is the
case for a plugin's own MCP server, whose tools are `mcp__plugin_<plugin>_<server>__<tool>`
and which no built-in default can name, and for `WebSearch`, which the mirror omits. Phase 7
writes the bound down so nobody reads a green suite as proof the case got everything.

The first two rows are what the plan closes, and the grant being right is not a reason to
leave them open. `eval.allow_tools` and `--allow-tools` replace the value rather than adding
to it, so a widened grant must name every tool it still wants and a mistyped one drops the
rest silently. When that happens the suite prints a score as though the run had the tool, and
nothing in the output says otherwise.

**The last line disagrees with the lines above it.** `verdict.py` prints one line per failure
and then a summary, and that summary takes its pass count from the harness's result file. The
harness counts a case as passed when its score is at or above `--threshold`, and this package
pins that to 0 on purpose: the verdict is this repository's, decided once across every
backend, rather than the harness's over one plugin. Handing it over is right.

Reading the loser's count back and printing it as the verdict is not. `casesPassed` under a
threshold of 0 is every case, always, so a run can print a failure and then say every case
passed on the next line. The exit code is correct throughout. Only the line lies.

## What this plan does

Three things.

Read each run's trace. If the model never got the tool, fail the eval instead of scoring what
it wrote without it.

Make the summary line report what was decided, and say when a sweep stopped early.

Write down where a run's files are kept. A consumer wants to check what an eval actually
produced, such as whether the `.pptx` a skill wrote will open, so they write their own script
over those files. That script needs a layout that does not move.

Why one kind of refusal invalidates a run and another does not, decided and not reopened
here: a `permission_denied` carrying `decision_reason_type: mode` invalidates it whatever
tool it names, and a denial from the plugin's own hook does not. A session has no permission
mode and is never refused a tool by one, so a mode denial is the container failing to behave
like a session and nothing else. A hook denial is the plugin's own behaviour, which a session
has too, and for a case testing a hook it is the correct behaviour under test. The rule
matches on the reason and never on the tool, because narrowing it to tools a grader names
would miss every denial that broke a run through a tool no grader mentions.

Branch: `feat/run-validity`.

## What this plan does not do

| Not in scope                                                        | Where it is instead                                                                                              |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Merging a verdict produced outside the harness into the result file | Nowhere. Nobody has asked for it                                                                                 |
| The content checker that reads the kept workspace                   | Outside this package. This repository is a library: [`../docs/library.md`](../docs/library.md)                   |
| The baseline arm, and anything reading a second arm                 | [`plan_ablation.md`](plan_ablation.md)                                                                           |
| The backend declaration on a case                                   | [`plan_runnability.md`](plan_runnability.md)                                                                     |
| The tool grant                                                      | Already done. `eval.allow_tools` is the session mirror in [`../docs/running_evals.md`](../docs/running_evals.md) |

## Skipping a case with a glob is not possible

An option to exclude a case from one invocation was wanted, so that nobody has to move the
case directory out of the tree. It cannot be built.

`claude plugin eval --case <glob>` takes one glob matching the case name, with `*` and `?`.
There is no negation and no list, and `--tag` only includes. On Docker the harness finds and
picks the cases, so this package has nothing to filter: it hands over one glob and that is
all. Excluding a case would mean calling the harness once per case, which writes one result
file per case, and both the log layout and the pass and fail rules expect one per plugin.

So the option is dropped. What is built instead is the counts: how many cases were found, how
many were picked, and how many ran. Phase 5 writes this into
[`../docs/cli.md`](../docs/cli.md) so nobody works it out again.

## Orientation

| Fact                                                       | Where                                                                                          |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| The kept trace, and the one pass that reads it             | `src/cowork_evals/traces.py`, `collect`, `last_message`                                        |
| What decides pass and fail, and the one arm it reads       | `src/cowork_evals/verdict.py`, `ARM`, `_judge_run`                                             |
| The summary line                                           | `src/cowork_evals/verdict.py`, `_Totals.summary`                                               |
| Case discovery, tags and the case glob                     | `src/cowork_evals/cases.py`, `discover`                                                        |
| Where the CLI selects, validates and decides pass and fail | `src/cowork_evals/cli.py`, `_run`, `_validate`                                                 |
| The result document this repository writes                 | `src/cowork_evals/results.py`                                                                  |
| The kept artefact layout, and the pass and fail table      | [`../docs/running_evals.md`](../docs/running_evals.md)                                         |
| What a harness trace holds, record type by record type     | [`../docs/claude_code/plugin_eval_reference.md`](../docs/claude_code/plugin_eval_reference.md) |

## Phases

### Phase 1: what the trace says when a tool is missing

Already done, and written into
[`../docs/running_evals.md`](../docs/running_evals.md). Read it there; it is not repeated
here. In short: a refused call leaves one record naming the tool and why it was refused, and
a tool that was never offered leaves nothing at all. What catches the second one is the run's
opening record, which lists every tool the model was given.

- [x] All of it, in that file

### Phase 2: the check

Two checks, one per failure mode. Both read the trace the run already kept, and both write
what they found into the result file, so pass and fail still read only that file.

Check two compares two lists of tool names, and nothing here has read the second one under
the grant that ships. The first box measures it, and the two boxes after it are written
against what it records.

- [x] Run `plugins/smoke/` on Docker under the default `eval.allow_tools` and record, dated,
      in [`../docs/running_evals.md`](../docs/running_evals.md): the exact strings the `init`
      record's tool list carries for all eight granted names. The snapshot already there
      measured two narrowed grants and not this one
- [ ] A granted name and an offered name are compared on the part before any `(`. The
      reference records that a bare `Read`, `Glob` or `Grep` reaches the child as a
      path-scoped grant, and `eval.allow_tools` may name `WebFetch(domain:...)`, so a literal
      comparison would report every run as missing a tool it had. If the measurement shows a
      granted name reaching the list in a shape this rule does not close, that name is
      excluded by name in one place, with the measurement cited beside it
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
- [ ] `verdict.py` fails a run carrying either, one line each, naming the tools and the
      directory holding that run's trace
- [ ] A denial from the plugin's own hook does not fail anything. Check one matches on the
      reason, never on the tool name
- [ ] Nothing changes on CoWork. A session has no permission mode and writes no tool list, so
      neither field ever appears and one decision still covers both backends
- [ ] A run that hit its turn cap or timed out already carries `error` and already fails.
      Check that against the pass and fail table and add nothing

Both checks read the trace `traces.collect` kept, and `cli.py` calls `collect` only when the
run was keeping traces. Off, the harness is handed no `--keep-temp`, no sandbox reaches the
host, and there is no trace to read: the two checks do not run and neither field reaches the
result file. That is the honest behaviour, and a failure condition that quietly stops applying
under an option is the shape of defect this plan exists to remove, so it is written down
rather than worked around.

- [ ] Nothing fails and nothing warns when traces are off. A run that kept no trace says
      nothing about what it had, which is the same rule as a trace with no `init` record.
      Phase 7 writes it down

### Phase 3: honest counts

The last line is wrong twice. It reads `casesPassed` back from the result document, which the
problem statement above covers, and a sweep the cost ceiling stopped early still reads as if
every case ran. The exit code is right in both. Only the line is wrong.

- [ ] The command already reads the case tree before it runs anything. It hands `verdict.py`
      two numbers, how many cases it found and how many it picked, the way it already hands
      over `extra`
- [ ] The line names four numbers: found, picked, ran, passed, then the score. `passed` is
      this package's own count, never `casesPassed`
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
- [ ] A grant of `WebFetch(domain:example.com)` against an `init` list carrying `WebFetch`
      yields none, and a bare `Read` against a list carrying only `Read(//home/**)` yields
      none. The comparison is on the part before the `(`
- [ ] A trace with no `init` record yields none. A run that wrote no tool list says nothing
      about what it had
- [ ] A trace with neither problem yields neither, and the result file is unchanged
- [ ] A result file carrying either field fails, and the line names the tools and the
      directory holding the trace
- [ ] A result file carrying neither field passes. That is not a courtesy to old documents:
      the CoWork backend never writes either field, so every `--cowork` document is this
      shape and one set of rules still covers both backends
- [ ] The last line carries the four counts, and says so when a sweep stopped early
- [ ] Every `verdict.py` test that already exists still passes, or its change goes in the
      same commit with the reason in the message

### Phase 7: documentation

- [ ] The pass and fail table in [`../docs/running_evals.md`](../docs/running_evals.md)
      gains the new condition, and says both conditions need a kept trace, so
      `--no-keep-traces` gives up both
- [ ] The same file says what the four counts on the last line mean
- [ ] It says what the two new fields in the result file are, next to where it describes the
      `tracePath` rewrite
- [ ] [`../docs/cli.md`](../docs/cli.md) says against `--no-keep-traces` that the option
      gives up both conditions, which is where a person reading it finds out
- [ ] [`../docs/approaches.md`](../docs/approaches.md) says this check is Docker only,
      because CoWork has no permission mode
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md) states the bound: both checks
      start from the grant, so a tool the case needed and nobody granted is caught by
      neither, and a green suite is not proof the run had everything it asked for
- [ ] [`../plugins/README.md`](../plugins/README.md): the fixture case phase 8 adds
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 8: run it for real

- [ ] `plugins/smoke/` on Docker, from the integration tier, passes
- [ ] A `plugins/smoke/` case asking for a `Write` call, run under a deliberately narrowed
      `--allow-tools` that omits `Write`, from the integration tier, fails, and the line names
      `Write`. The narrowing is the test's, and the default grant is untouched
- [ ] `scripts/test.sh` and `ruff` clean
