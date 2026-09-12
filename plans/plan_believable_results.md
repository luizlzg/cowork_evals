# Believable results: what was measured, what follows from it, and the four plans

This plan writes no code. It holds the state of a design conversation that ran on
2026-09-12, so that a cleared context resumes from here. Its product is four plan files.

Work it after plan 8 is implemented and merged. Phase 1 used the `ask` verb that plan built,
and the row for it is in [`README.md`](README.md).

## The principle every decision here follows from

Claude Code in a container is simulating a CoWork session so that an eval can be run cheaply
and repeatedly. CoWork is the expensive backend that checks the real thing. Every question
below was answered by applying that sentence, and none of them was a judgement call.

Where the two differ and the difference is not a deliberate, stated property of the
simulation, the simulation is wrong and is changed. That is the whole rule.

## Decisions

Do not reopen these. Each is argued, and each states what it follows from.

| Decision                                                                 | Reason                                                                 |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| No `skip:` field in a case tree, ever                                     | It is a permanent silent pass that outlives whoever wrote it, and it would need the gate to stop failing on skips. `CLAUDE.md` already says never skip |
| A case that a backend cannot run says so in its own file                  | The fact must be readable without reading `cowork_evals` source          |
| The declaration is a reserved tag, `no-cowork`, unless a measurement shows the harness tolerates an unknown frontmatter key | `tags:` is already free-form and upstream only filters on it. A new key risks the Docker backend rejecting the case |
| The validator enforces the declaration in both directions                 | A case writing an unhonourable key without the tag is an error, and a case carrying the tag with nothing that stops a CoWork run is also an error. The second is what stops the tag being a silencer |
| A case tagged out of a backend is counted, never failed                   | A sweep that is permanently red for something nobody can fix trains people to ignore red |
| No `no-docker` counterpart                                               | Nothing in the code or in `docs/approaches.md` names a case key the Docker backend cannot honour. Building the symmetric half is inventing a restriction |
| `evals/mocks/` is handled by tagging each case, not the directory         | Explicit at the case, and it survives the case being moved                |
| An absent environment variable named for passthrough refuses at the preflight | A missing precondition fails. It never forwards an empty string           |
| Environment passthrough is never a route for Claude's own credentials     | The container login is the one credential route                           |
| The artifact content checker is built outside this package                | The report established that no harness change is needed. This repository is a library |
| The container's tool grant mirrors a session, and is not a judgement | The Docker backend exists to run the same case the same way a session does. A session grants nothing and acts, so a container run denied a tool a session has measures this package's configuration rather than the plugin. Closed on 2026-09-12 and implemented the same day, so `plan_run_validity` inherits a grant that is already right: `docs/running_evals.md` |
| The real gap under report item 5 is selection, and it is an exclusion glob on the invocation | `--case` takes one glob and `--tag` only includes, so there is no way to say `everything except X` without moving the directory. A glob typed on one invocation is visible in that invocation and silences nothing tomorrow. It rides in `plan_run_validity`, which is already making the selection counts honest |
| A `permission_denied` carrying `decision_reason_type: mode` invalidates the run, whatever tool it names. A denial from a plugin's own hook does not | A session has no permission mode and is never refused a tool by one, so a mode denial is the simulation being wrong and nothing else. A hook denial is the plugin's own behaviour, which a session has too, and for a hook-gate case it is the correct behaviour under test. Narrowing the rule to tools a grader names would miss every denial that broke a run through a tool no grader mentions |
| There is no baseline arm on CoWork, and no plan builds one | The arm is a statistical control, and a control belongs on the cheap backend. On CoWork a plugin's presence is a property of the profile and the application chooses the profile, so a second arm means a second profile and an application restart between arms. Measured in section 5 of `docs/cowork_desktop.md` |
| The baseline arm is off by default | Under `with-without` the harness stops scoring a `tool_used: Skill` grader and reports it as an indicator. On by default would silently stop gating skill activation, which is report item 1 |
| The gate compares per case, with-arm minus without-arm, against a threshold defaulting to 0 | A suite-level average hides a case the plugin made worse. `--threshold` is already pinned to 0 so that this gate owns the number, so the number lives here |

## What the problem report said

The report is dated 2026-09-12 and applies to 0.3.0 on both backends. Its five items, in its
own order:

1. **A skill that fails to load must fail the eval.** The activation graders count `Skill`
   tool calls, and a call the permission mode denied counts as a firing. A run in which the
   skill never executed scores exactly like a run in which it did. The evidence is on disk in
   the kept trace: `{"type":"system","subtype":"permission_denied","tool_name":"Skill",
   "decision_reason_type":"mode"}`. The same check covers a run that hit its turn limit and
   produced nothing. Related and lower priority: a sweep the stop condition truncated still
   reads `7 cases, 7 passed`.
2. **Turn the baseline arm on.** `harness.py` pins `ABLATION = "none"` and `THRESHOLD = "0"`
   and exposes neither. Under `with-without` a `tool_used: Skill` grader stops being a score
   component and becomes an indicator, which is the other half of item 1. Needed: the option
   and the configuration key, a gate that reads both arms and decides on the delta, a
   threshold that means something, and the arm implemented on the CoWork backend, which runs
   no second arm at all.
3. **Checking the produced artifact needs no harness change.** 0.3.0 keeps each run's
   workspace on the host under `traces/<case>/run-N/workspace/`. Reading the file directly
   reproduces the graded verdict. A custom grader could not run in the container anyway. The
   checker is therefore a post-suite pass on the host, built outside this package. Two notes
   for whoever builds it: the kept workspace is sealed on purpose, and there is one directory
   per run. Deferred by the report's own recommendation: merging a verdict produced outside
   the harness into the result document so that it gates.
4. **Environment passthrough.** The container starts with exactly two variables, `HOME` and
   the enablement flag. A skill that needs credentials cannot be evaluated at all. Needed: a
   way to name variables in `cowork_evals.yaml` that are forwarded from the host, with values
   never written into logs or the result document.
5. **Skip a case without moving files.** `--case` takes a single glob and `--tag` filters
   inclusively, so the workaround is moving the case directory out of the tree. The report
   asked for a `skip:` field with a reason. That is refused. The request splits into two
   halves, and the decisions above answer each: a case that a backend cannot run declares it
   and is counted rather than failed, and a case a person wants out of one sweep is excluded
   by a glob on that invocation.

## What the conversation found that the report did not

The Docker backend's tool grant is not a measured mirror of CoWork. `docs/docker.md` and
`docs/runtime.md` claim fidelity of the image: the distribution, the interpreter and the wheel
set. The tool grant is a different thing, and it belongs to `claude plugin eval`, not to
CoWork. `docs/running_evals.md` justifies the `[Bash]` default as a judgement, not a
measurement, and the same file already records the consequence: an ungranted case loses the
tool rather than failing loudly. Meanwhile the CoWork backend reads `outputs/` for files a
session wrote, so a session plainly writes files while a Docker run under the default grant
has `Write` denied.

So there are two defects under item 1, not one. The grant is probably wrong, and a denial
scores green anyway. Fixing the grant does not make the second safe to ignore, and fixing the
second without the first turns a large number of currently green runs red for a reason that is
this repository's own configuration.

## Orientation

Where each thing is, for a context that starts here.

| Fact                                              | Where                                            |
| ------------------------------------------------- | -------------------------------------------------- |
| The pinned ablation and threshold                 | `src/cowork_evals/harness.py`, `ABLATION`, `THRESHOLD` |
| The gate, and the one arm it reads                | `src/cowork_evals/gate.py`, `ARM`                 |
| Trace collection, and the same single arm         | `src/cowork_evals/traces.py`, `ARM`, `collect`    |
| What a CoWork run cannot honour                   | `src/cowork_evals/cowork_backend.py`, `UNHONOURED_CASE_KEYS` |
| The container's two environment variables         | `src/cowork_evals/docker/__init__.py`, `run_preamble` |
| Case discovery, tags and the case glob            | `src/cowork_evals/cases.py`, `discover`           |
| The frontmatter key set the validator allows      | `src/cowork_evals/validate.py`, `PROMPT_KEYS`     |
| The tool grant, and why it is what it is          | `docs/running_evals.md`, the `--allow-tools` paragraph |
| What each backend honours                         | `docs/approaches.md`                              |
| The kept artefact layout                          | `docs/running_evals.md`                           |

## Phases

### Phase 1: measure, before anything is written

Each box is one or more `cowork_evals ask --cowork` submissions. Every box records its result
in the `docs/` file that owns the subject, dated, and called a snapshot. Ask the session to do
the thing and read what it did. What a session says about its own configuration is not
evidence.

- [x] What a live session does when asked to write a file, shell out, fetch a URL, and fire a
      skill. Plan 8 already paid for it and recorded it: section 5 of
      [`../docs/cowork_desktop.md`](../docs/cowork_desktop.md). Nothing was re-submitted
- [x] Whether a session asks for permission before using a tool, or acts. The same snapshot
      answers it: nothing was granted, nothing was asked, four tools were used and all four
      runs reached `completed`. A session acts
- [x] Whether a session can run with a named skill absent, and how that absence is arranged.
      One submission, recorded in section 5 of
      [`../docs/cowork_desktop.md`](../docs/cowork_desktop.md). A session's skill set is the
      profile's mounted, application-managed tree, so absence is arranged by using another
      profile and by nothing else. Not clean, so decision 3 splits the CoWork arm out
- [x] Whether `claude plugin eval` accepts an unknown `prompt.md` frontmatter key. It does
      not: the case is refused at load and the whole suite writes no result document. An
      unknown `case.yaml` key is ignored. Recorded in
      [`../docs/eval_format.md`](../docs/eval_format.md). The declaration is the reserved tag

If a measurement is inconclusive, the plan that depends on it is written to the conservative
option: the tag rather than the key, and the CoWork baseline arm split into its own plan
rather than folded in.

### Phase 2: settle what the measurements left

Every one of these follows from the principle above. None was put to the developer, and a
later plan does not reopen one.

- [x] The tool grant. Closed and implemented the same day rather than deferred into a plan:
      `eval.allow_tools` is the session mirror, stated in `docs/running_evals.md`
- [x] What makes a run invalid. A `mode` denial, whatever tool it names. A hook denial does
      not, because a hook-gate case is a case whose correct behaviour is a denied call
- [x] The baseline arm on CoWork. Not built, and no fifth plan. The row says why
- [x] Whether the baseline arm defaults on. Off
- [x] What the gate compares. Per case, against a threshold defaulting to 0
- [x] Every one of them written into the decisions table above, before the plan that
      depends on it is written

### Phase 3: write the four plans

Written in this order, and implemented in this order. Each is a separate file, a separate
branch and a separate merge. What each holds is its own file; nothing is restated here.

- [x] [`plan_run_validity.md`](plan_run_validity.md). A run that never got its tool fails
      instead of scoring, and the summary counts stop lying. The exclusion glob that was to
      ride with it is dropped, and that file says why: `--case` takes one glob with no
      negation, and on Docker the harness selects
- [x] [`plan_runnability.md`](plan_runnability.md). The `no-cowork` tag, enforced in both
      directions by the validator, read by the CoWork backend in place of its run-time case
      skip, and counted rather than failed
- [x] [`plan_env_passthrough.md`](plan_env_passthrough.md). Named host variables forwarded
      into the run container, with no value in any artefact
- [x] [`plan_ablation.md`](plan_ablation.md). The option, the setting, both arms collected,
      and a gate that decides on the per-case delta. Docker only. Last, because it rewrites
      the gate the first two change
- [x] A row for each in [`README.md`](README.md), and a paragraph where that file describes
      what a plan builds

### Phase 4: retire this file

Not yet, and the condition is not the one this phase was written with.

The four plans link to the decisions table above, which is the one place each of those
decisions is derived. A file in `done/` is frozen and is never read or cited, so retiring
this one while four live plans cite it would break that rule in four places at once.

- [ ] Each of plans 10 to 13 writes what it establishes into `docs/` as it is implemented,
      which is the rule in [`README.md`](README.md) and is what empties this file of anything
      durable
- [ ] When the last of the four is merged, nothing outside `done/` cites this file. Move it
      then, under the rule in [`README.md`](README.md). It is the record of what was measured
      and decided on 2026-09-12, which is the first thing anyone needs when one of these
      decisions is questioned later
