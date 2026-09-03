# Plan: evals on CoWork, driven directly

Build the driver that submits a prompt to a real CoWork session without a human keystroke
and collects the result from the host filesystem.

The design is [docs/cowork_driver.md](../docs/cowork_driver.md): the scope, the two
decisions and their limits, the completion signal and its fallback, the configuration, the
failure taxonomy, the result document and the cleanup procedure. Read it. This plan builds
it and is then deleted. Anything durable this plan learns goes into that page before the
plan is removed.

Also read: [docs/cowork_desktop.md](../docs/cowork_desktop.md) for the measured application
internals, the authorizations and the coupling list.

**Independent of the other two plans.** It shares the log layout and nothing else. It does
not use `claude plugin eval`.

Branch `evals-cowork`, off `main`.

## Scope

| In scope                                           | Out of scope                     |
| -------------------------------------------------- | -------------------------------- |
| Submitting a prompt without a human keystroke      | Graders of any kind              |
| Proving the collected session is the one submitted | A case format                    |
| Parsing transcript, audit log and outputs          | Any pass or fail decision        |
| The result document                                | CI, scheduling                   |
| The prompt linter                                  | Attachments, plugin staging      |

Mapping the result document onto grader classes is later work, and it needs this driver to
exist first.

## Phases

Follow the execution discipline in [README.md](README.md): one box, verified, ticked,
committed, before the next.

### Phase A: submit and collect one run

- [ ] Confirm every authorization in `docs/cowork_desktop.md` is granted. The permission
      rules cannot be written by an assistant: the user creates
      `.claude/settings.local.json`, which is git-ignored.
- [ ] Write `scripts/prompt_lint.py` and `tests/test_prompt_lint.py`: a read-only prompt
      passes, and one prompt per deny-list rule is refused.
- [ ] Write `scripts/cowork/cowork.py` with a `run` subcommand implementing the mechanism,
      the configuration and the exit codes in `docs/cowork_driver.md`. Python 3.14,
      standard library only, one file.
- [ ] Run a token prompt. `final_text` must equal the token, with no human keystroke, exit 0.
- [ ] Run a bash probe. The tool call carrying the workspace bash tool name must have a
      result containing the guest `uname` string, paired by `tool_use_id`.
- [ ] Run ten consecutive token prompts. Every one returns a session whose recorded prompt
      equals the one submitted. No exit 4, no 5, no 6.
- [ ] Confirm the run log has ten lines and that the driver modified no file under the
      profile.

**Gate:** ten consecutive runs collect correctly, and both probe shapes work: a pure text
answer, and a tool-using run with an effect inside the VM.

### Phase B: the completion signal

- [ ] Read `audit.jsonl` from all ten phase A runs and list every distinct
      `command_lifecycle` state observed.
- [ ] Record the terminal state in `docs/cowork_driver.md`, or record there that none was
      observed and the quiescence fallback ships.
- [ ] Key completion on whichever the previous box recorded.
- [ ] Run a prompt whose first output is slower than `COWORK_IDLE_SECONDS`. It must not be
      reported finished early.
- [ ] Run a prompt with a long pause mid-run. It must not be reported finished early.

**Gate:** the completion signal is recorded in `docs/cowork_driver.md`, implemented, and
does not fire early on either slow start or mid-run pause.

### Phase C: the failure taxonomy

- [ ] Produce each exit code from 2 to 8 deliberately at least once, and record in
      `docs/cowork_driver.md` how each was produced.
- [ ] Run a prompt with two tool calls and confirm each result attaches to its own call.
- [ ] Start a run while another application holds focus. It must either succeed or exit
      non-zero. It must never submit into the wrong window and report success.
- [ ] Write `tests/test_cowork.py` over recorded transcript, audit and directory fixtures in
      `tests/data/`: prompt matching, tool pairing, subagent sidechains, the completion
      signal, and every exit code. No live run in a test.

**Gate:** every exit code was produced deliberately, focus theft cannot report a false
success, and the tests pass over fixtures with no live run.

### Phase D: close out

- [ ] Re-read `docs/cowork_driver.md` end to end. Every statement must be true of the built
      driver and the status line updated.
- [ ] Run every command in `docs/cowork_driver.md` and confirm each behaves as written.
- [ ] Re-verify the coupling list in `docs/cowork_desktop.md` against the running
      application version, and update the recorded version and capture date.
- [ ] Add the driver rows to `scripts/README.md`, and set the CoWork driver to yes in the
      status table of `docs/running_evals.md`.
- [ ] Apply the public repository check in the root `README.md` to every file this plan
      added. Test fixtures are the risk here: they are recorded from a live session.
- [ ] Confirm nothing outside `plans/` links to this plan, delete it, and remove its
      row from `plans/README.md`.

**Gate:** `docs/cowork_driver.md` describes a built driver, the fixtures carry no
identifiers, tests and lint are clean, and this file is deleted.

## Risks

| Risk                                          | Mitigation                                                       |
| --------------------------------------------- | ---------------------------------------------------------------- |
| Application internals change on any release   | The coupling list in `docs/cowork_desktop.md`. Cheap to re-probe |
| Keystroke lands in the wrong application      | Phase C focus check. Long term, a dedicated machine              |
| Profile corruption                            | The driver never writes anywhere under the profile               |
| Tenant enables `disableDeepLinkRegistration`  | The approach ends. It fails closed and shows as exit 4           |
| Quiescence fires during a long pause mid-run  | Phase B replaces it with the lifecycle state where observed      |
| Sessions accumulate in a real account history | `COWORK_MAX_RUNS`, the run log, manual cleanup. Accepted         |
| A prompt mutates real data                    | `prompt_lint.py`, plus review. A filter, not a sandbox           |
