# Plan: evals on Claude Code, under the CoWork mirror

Build the eval runner over `claude plugin eval`, with the CoWork Python mirror on `PATH` so
a skill that shells out to `python3` gets Python 3.10 and the CoWork wheel set.

The design is [docs/running_evals.md](../docs/running_evals.md): the case layout, the run
scopes, the pinned flags, the gate, the logs, the cadence and the cost ceilings. Read it.
This plan builds it and is then deleted. Anything durable this plan learns goes into that
page before the plan is removed.

Also read: [docs/plugin_eval.md](../docs/plugin_eval.md) for the harness,
[docs/environments.md](../docs/environments.md) for the mirror.

Branch `evals-venv-cowork`, off `main`.

## Scope

| In scope                                     | Out of scope                           |
| -------------------------------------------- | -------------------------------------- |
| The runner scripts and the three run scopes  | An eval case for a real skill          |
| Case layout validation                       | Raising any plugin's eval coverage     |
| The result gate                              | Judging whether any skill passes       |
| The log layout and pruning                   | A CI job. Nothing here runs on CI      |
| Documentation and tests for the above        | Docker, and driving CoWork             |

One smoke plugin proves the plumbing. **This plan writes no eval case for a real skill.**

## The one thing to establish first

`claude plugin eval` runs each case in a fresh `claude -p` session. The per-run sandbox
replaces `HOME` and `CLAUDE_CONFIG_DIR`. Whether it inherits `PATH` is what makes this
approach work: if it does, putting `.venv_cowork/bin` first makes a bare `python3` inside a
case resolve to 3.10 with the CoWork wheels.

Phase A verifies it with a probe case. If `python3 -V` inside a run does not report 3.10, no
environment variable can fix it, this approach cannot mirror the interpreter, and the
container is the only route to that fidelity. Record the outcome in
`docs/running_evals.md`, not here: the finding outlives this plan.

## Phases

Follow the execution discipline in [README.md](README.md): one box, verified, ticked,
committed, before the next.

### Phase A: prove the harness and the mirror

- [ ] Confirm `claude plugin eval` is enabled: run it in an empty directory. `No eval cases
      found` means enabled, `early access` means gated. If gated, export
      `CLAUDE_CODE_WALNUT_SPIRE=1` per `docs/plugin_eval.md` and record there that it was
      needed here.
- [ ] Run `docs/claude_code/eval_smoke/run.sh`. All three vendored cases must pass. This
      proves the harness before anything in this repository is written, so a later failure
      is attributable.
- [ ] Create `plugins/smoke/`: `.claude-plugin/plugin.json`, one skill
      `skills/probe/SKILL.md` that runs `python3 -c 'import sys; print(sys.version)'` and
      prints the result, and an empty `hooks.json`. No MCP server, so nothing outside the
      harness can fail.
- [ ] Create `plugins/smoke/evals/probe/interpreter/` per the layout in
      `docs/running_evals.md`, with two graders: `tool_used` on `Skill` with the
      skill-fired `input_match`, and `regex` matching `3\.10\.` in the last message.
- [ ] Write `scripts/eval.sh` with the scopes, flags and log layout in
      `docs/running_evals.md`. It exports `CLAUDE_CODE_WALNUT_SPIRE`.
- [ ] Run `scripts/eval.sh smoke/probe --allow-tools Bash`. It must exit 0 and the `regex`
      grader must pass, which proves `PATH` inheritance and the mirror together.
- [ ] Record the `PATH` inheritance finding in `docs/running_evals.md`.
- [ ] Record the smoke case's wall clock and `costUsd` in the cost table of
      `docs/running_evals.md`.
- [ ] Confirm the log directory holds all six artefacts and the `latest` symlink.
- [ ] Set `scripts/eval.sh` to yes in the status table of `docs/running_evals.md`.

**Gate:** the smoke case exits 0, the interpreter grader passes, and the log directory is
complete.

### Phase B: the gate and the sweep

- [ ] Write `scripts/eval_gate.py` to the semantics in `docs/running_evals.md`.
- [ ] Write `tests/test_eval_gate.py`: a passing document exits 0, a failed structural
      grader exits 1, a failed judged grader exits 0 and prints, `partial: true` exits 1, a
      missing file exits 1, an unparsable file exits 1, and an unknown top-level field is
      tolerated. Fixtures under `tests/data/`, no live run.
- [ ] Write `scripts/eval_all.sh`, including the total cost ceiling and early stop.
- [ ] Write `scripts/validate_cases.py` and `tests/test_validate_cases.py`, one failing
      fixture per layout rule: an unexpected directory under `evals/`, a `tags` mismatch, a
      wrong `plugins` path, a grader file with no `---` delimiters, a `tool_used` grader
      with `max: 0` and no `min: 0`, and a `case.yaml` missing `schema_version` or `name`.
- [ ] Add `scripts/validate_cases.py` to `scripts/lint.sh`.
- [ ] Break the smoke case's `regex` grader deliberately, run `scripts/eval.sh smoke`, and
      confirm the gate exits 1 and names the case and its log path. Restore the grader.
- [ ] Run `scripts/eval_all.sh` and confirm it exits 0, writes one `<stamp>-all` directory,
      and gates once.
- [ ] Run `scripts/eval_all.sh` with `EVAL_MAX_COST_TOTAL_USD=0` and confirm it stops early
      and exits non-zero.
- [ ] Record the sweep's wall clock and `costUsd` in `docs/running_evals.md`.
- [ ] Set the remaining scripts to yes in the status table of `docs/running_evals.md`.
- [ ] `scripts/test.sh` and `scripts/lint.sh` clean.

**Gate:** the gate exits 1 on a broken structural grader and 0 on a broken judged one, the
sweep runs, and the cost ceiling stops it.

### Phase C: close out

- [ ] Re-read `docs/running_evals.md` end to end. Every statement must now be true of the
      built system, every status row set, every measurement filled.
- [ ] Run every command in `docs/running_evals.md` and confirm each behaves as written.
- [ ] Add the eval rows to `scripts/README.md`.
- [ ] Add a `## Evals` section to `.github/pull_request_template.md`: one box for
      `scripts/eval.sh <plugin>` per touched plugin with the summary pasted, one box for
      not applicable.
- [ ] Apply the public repository check in the root `README.md` to every file this plan
      added.
- [ ] Confirm nothing outside `plans/` links to this plan, delete it, and remove its
      row from `plans/README.md`.

**Gate:** `docs/running_evals.md` describes a built system with no unfilled row, every
command in it was run, and this file is deleted.
