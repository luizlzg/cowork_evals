# plans

Work in progress. Each plan is executed on its own branch off `main` and merged back when
its checklist is complete.

**A plan is never deleted by Claude.** The developer decides when a plan goes, and says so.
A completed plan stays until then, because it is the record of which decisions were asked
for and which were proposed, and that record is what anyone needs when a design decision is
questioned later. Git history does not answer that: every commit here is authored by the
developer with Claude as co-author, so it cannot tell the two apart.

A plan is still not a place to record anything durable. It links to `docs/`, and `docs/`
never links back. Whatever a plan establishes that outlives the work is written into `docs/`
while the work happens.

## Plans

Five plans, in build order. Each is written when the one before it is merged, so a later
plan is informed by what the earlier one measured. `status` is the plan's own state, not the
system's: what is built and usable is
[`../docs/running_evals.md`](../docs/running_evals.md).

| # | Plan                     | Builds                                                                            | Status      | Branch              |
| - | ------------------------ | ----------------------------------------------------------------------------------- | ----------- | ------------------- |
| 1 | `plan_cowork_tools.md`   | The CoWork driver: submit one prompt, wait, return what the session produced      | implemented | `feat/cowork-tools` |
| 2 | `plan_docker.md`         | The image, its digest, `scripts/parity.sh`, and the harness run inside a container | not written |                     |
| 3 | `plan_venv.md`           | The staged relocatable 3.10 runtime, and the harness run under it                 | not written |                     |
| 4 | `plan_cowork_backend.md` | The case reader and the CoWork grader over the driver                             | not written |                     |
| 5 | `plan_cli.md`            | Scope resolution, the run directory, the gate, and the command                    | not written |                     |

| Status        | Means                                                              |
| ------------- | -------------------------------------------------------------------- |
| `not written` | The plan file does not exist yet                                    |
| `written`     | The plan file exists, and its checklist is not finished             |
| `implemented` | Every box is ticked and the branch is merged. The file stays        |

Plans 2 and 3 each build one backend whole. Running an eval on those two backends is
`claude plugin eval`, which discovers the cases, runs them, grades them and writes
`aggregate-result.json` itself, so there is nothing above the backend to put in a plan of its
own. Only the host changes between them. See
[`../docs/approaches.md`](../docs/approaches.md).

Plan 4 is separate because CoWork is not symmetric with the other two. The driver returns one
session document for one prompt. Reading the case tree, deciding which case the backend can
honour, grading it and writing the v1 result document are all built there, and are what the
harness provides for free elsewhere. See
[`../docs/cowork_driver.md`](../docs/cowork_driver.md).

Docker comes before the venv, although the venv is cheaper to build.
[`../docs/running_evals.md`](../docs/running_evals.md) records that a `Bash`-granting run is
refused on this host, and every case that shells out needs that grant. The container installs
bubblewrap and runs with `seccomp=unconfined`, so it may be the only backend on this machine
that can grant `Bash`. Measuring that early is worth more than the cheaper build.

### The contract that keeps plan 5 last

A backend is a function. It takes a case path and an output directory, and it returns the
path to the `aggregate-result.json` it produced.

A backend never names the run directory, never writes `env.txt` or the `latest` symlink,
never prunes, never parses an option and never decides pass or fail. Plan 5 owns all of it.

Plans 2, 3 and 4 hold to that, so plan 5 assembles what exists and rebuilds none of it. A
backend that writes a log layout of its own breaks the one gate that covers all three. The
layout and the gate are [`../docs/running_evals.md`](../docs/running_evals.md), and the
command is [`../docs/cli.md`](../docs/cli.md).

## How a plan is written

Writing rules are in [`../CLAUDE.md`](../CLAUDE.md). These are the rules specific to a
plan.

- It points at `docs/`. It never restates a document, and nothing in `docs/` points back.
- Its design lives in `docs/`. The plan holds scope, phases, checklists and gates only.
- It is self-contained and executable with a cleared context.
- It is complete. No open question, no TBD, no decision left to the reader. Where a fact
  was unknown at writing time, the plan says which phase measures it and what ships if the
  measurement fails.
- Every phase is one commit and has a gate. Do not start a phase before the previous gate
  passes.
- Testing and documentation are phases, not afterthoughts.

## How a plan is executed

Work one box, verify it, tick it in the plan file, commit. Do not batch ticks. The plan
file is the state, so a cleared context can resume from it.

A measurement is written into the `docs/` page that owns it, not into the plan, because the
plan will not survive. A row in `docs/` still reading `not yet measured` means the box that
fills it is not ticked.
