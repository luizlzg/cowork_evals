# Documentation

## Summary

Reference material for running evals against Claude CoWork. Read the file that covers what
you are about to change, and link to it rather than restating it.

- Evals are not written here. This repository is a library, installed by the repository that
  owns the plugins under test.
- It runs two things: an eval, and a consumer's pytest suite on the CoWork runtime. Only the
  first needs a model.
- An eval is written once, in one case format, and runs on either backend. The backend
  changes, the case does not.
- Every file states what is true of this repository now. A measured fact carries its capture
  date and is called a snapshot.
- No file here carries a build status of its own, and no file here links to a plan.

The table below is in reading order. The first six files are the system; the next four are
the mechanisms under it; the next two are measurements of things this repository does not
build; the last three are external material and one deferred design.

| File                                       | Covers                                                          |
| ------------------------------------------ | ---------------------------------------------------------------- |
| [`library.md`](library.md)                 | The boundary: what ships, how it installs, where state lives    |
| [`cli.md`](cli.md)                         | The `cowork_evals` command: verbs, backends, scope, exit codes  |
| [`approaches.md`](approaches.md)           | The two backends, the one case format, and what each proves     |
| [`eval_format.md`](eval_format.md)         | What a case file contains: tree, frontmatter, graders, traps    |
| [`running_evals.md`](running_evals.md)     | The run: status, pinned flags, the gate, logs, cadence, cost    |
| [`cowork_test.md`](cowork_test.md)         | The other thing this repository runs: a consumer's pytest suite, on the CoWork runtime |
| [`docker.md`](docker.md)                   | The container that reproduces the CoWork image                  |
| [`cowork_driver.md`](cowork_driver.md)     | Driving CoWork from a script: API, sequence, session document   |
| [`cowork_backend.md`](cowork_backend.md)   | The layer over it: grading a session document, the judge, the result document |
| [`environments.md`](environments.md)       | The two Python environments and how to build them               |
| [`runtime.md`](runtime.md)                 | What a CoWork session provides and what is on the image         |
| [`cowork_desktop.md`](cowork_desktop.md)   | Desktop application internals: deep links, session filesystem   |
| [`plugin_eval.md`](plugin_eval.md)         | `claude plugin eval`: availability, flags, harness limits, cost |
| [`claude_code/`](claude_code/README.md)    | The vendored harness references, and the harness smoke plugin   |
| [`staged_runtime.md`](staged_runtime.md)   | Designed, not implemented: the staged 3.10 runtime and the venv backend over it |

## How the files divide

`running_evals.md` holds the run: what the command does with a case tree whichever backend
it chose. The status of every piece, which case a backend must skip, the pinned harness
argument list, the gate, the log layout, the cadence and the cost ceilings.

[`cowork_test.md`](cowork_test.md) holds the other thing the command runs. It is a mechanism
file, not a backend: it returns pytest's exit code and produces no result document, so nothing
in `running_evals.md` covers it.

A mechanism file holds how one thing works and everything measured about it.
[`docker.md`](docker.md) is the container, [`cowork_driver.md`](cowork_driver.md) the desktop
driver, [`environments.md`](environments.md) the two Python environments. A fact measured
during a run belongs with the mechanism it binds and not with the run.

[`cowork_backend.md`](cowork_backend.md) is the layer over the driver, and the two files split
on one question: does the statement need to know what a case is? Yes, and it is in the
backend. No, and it is in the driver.

[`runtime.md`](runtime.md) and [`cowork_desktop.md`](cowork_desktop.md) measure what this
repository does not build, the session image and the desktop application. A mechanism file
cites a value from either and never restates it, so `cowork_driver.md` states the driver's
design and links the application shape it reads.

Build status is the one fact that goes the other way. Every piece has a row in
`running_evals.md`'s status table whatever mechanism it belongs to, and the files whose
subjects have a row link there.

`eval_format.md` is the authoring contract a case is written to. `plugin_eval.md` describes a
Claude Code command this repository does not own and carries the CLI version it was written
against. The three requirements files are measurements too and are not here: they are package
data at [`../src/cowork_evals/data/`](../src/cowork_evals/data/), and
[`environments.md`](environments.md) owns the split between them.

## Provenance

Adapted from an internal marketplace repository, which is not public. Absolute paths are
redacted, because this repository is public.

| Source document             | Adapted into                                             |
| --------------------------- | -------------------------------------------------------- |
| `dev/environment.md`        | [`environments.md`](environments.md)                     |
| `dev/runtime.md`            | [`runtime.md`](runtime.md)                               |
| `dev/data/requirements*`    | [`../src/cowork_evals/data/`](../src/cowork_evals/data/) |
| `plan_evals_claude_code.md` | [`plugin_eval.md`](plugin_eval.md)                       |
| `plan_run_cowork.md`        | [`cowork_desktop.md`](cowork_desktop.md)                 |

Writing rules are in [`../CLAUDE.md`](../CLAUDE.md). The public repository rule is in
[`../README.md`](../README.md), and it applies to every file here.
