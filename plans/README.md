# plans

Work in progress. Each plan is executed on its own branch off `main`, merged back when its
checklist is complete, and then deleted.

A plan is therefore not a place to record anything durable. It links to `docs/`, and
`docs/` never links back. Whatever a plan establishes that outlives the work is written
into `docs/` before the plan is removed, and every plan's last phase says so explicitly.

A row is added below when a plan is written, and removed when the plan is deleted.

No plan is open.

Build order, when the backend plans are written: the package skeleton and the CLI first,
because they own the command surface, the gate and the log layout. Then the venv backend,
then Docker, which changes only where the harness executes. The CoWork backend is
independent of both.

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
