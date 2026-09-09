# Documentation

Reference material for running evals against Claude CoWork. Read the file that covers what
you are about to change, and link to it rather than restating it.

Evals are not written here. This repository is a library, installed by the repository that
owns the plugins under test. [`library.md`](library.md) is that boundary and
[`cli.md`](cli.md) is the command a consumer runs.

An eval is written once, in the format at [`eval_format.md`](eval_format.md), and runs on
any of the three backends. [`approaches.md`](approaches.md) says which backend honours which
part of it.

| File                                             | Covers                                                          |
| ------------------------------------------------ | --------------------------------------------------------------- |
| [`library.md`](library.md)                       | The boundary: what ships, how it installs, where state lives    |
| [`cli.md`](cli.md)                               | The `cowork_evals` command: verbs, backends, scope, exit codes  |
| [`approaches.md`](approaches.md)                 | The three backends, the one case format, and what each proves   |
| [`eval_format.md`](eval_format.md)               | What a case file contains: tree, frontmatter, graders, traps    |
| [`running_evals.md`](running_evals.md)           | The run: status, pinned flags, the gate, logs, cadence, cost    |
| [`docker.md`](docker.md)                         | The container that reproduces the CoWork image                  |
| [`cowork_driver.md`](cowork_driver.md)           | Driving CoWork from a script: API, sequence, session document   |
| [`runtime.md`](runtime.md)                       | What a CoWork session provides and what is on the image         |
| [`environments.md`](environments.md)             | The two Python environments and how to build them               |
| [`staged_runtime.md`](staged_runtime.md)         | The 3.10 runtime staged into a plugin so a sandboxed case reaches it, and the venv backend over it |
| [`plugin_eval.md`](plugin_eval.md)               | `claude plugin eval`: availability, flags, harness limits, cost |
| [`cowork_desktop.md`](cowork_desktop.md)         | Desktop application internals: deep links, session filesystem   |
| [`claude_code/`](claude_code/README.md)          | The vendored harness references, and the harness smoke plugin   |

A measured fact here carries its capture date and is called a snapshot. A snapshot is not a
contract, and it is re-probed when the thing it describes changes. `runtime.md` and
`cowork_desktop.md` are measurements throughout. Every other file carries a snapshot wherever
it cites a measured fact. The two requirements files are measurements too and are
not here: they are package data at
[`../src/cowork_evals/data/`](../src/cowork_evals/data/), and
[`environments.md`](environments.md) owns the split between them.

`eval_format.md` is the authoring contract a case is written to, and `plugin_eval.md`
describes a Claude Code command this repository does not own and carries the CLI version it
was written against.

Nothing here ever links to a plan. Anything durable a plan establishes is written into one
of these files while the work happens, so nothing here depends on a plan file.

## The run, and the mechanisms

[`running_evals.md`](running_evals.md) and the files that cover one backend or one mechanism
split like this.

`running_evals.md` holds the run: what the command does with a case tree whichever backend
it chose. The status of every piece, which case a backend must skip, the pinned harness
argument list, the gate, the log layout, the cadence and the cost ceilings.

A mechanism file holds how that one thing works and everything measured about it.
[`docker.md`](docker.md) is the container, [`staged_runtime.md`](staged_runtime.md) the
staged 3.10 runtime and the venv backend over it, [`cowork_driver.md`](cowork_driver.md) the
desktop driver, [`environments.md`](environments.md) the two Python environments. A fact
measured during a run belongs with the mechanism it binds and not with the run, so the host
that refuses a `Bash`-granting run is in `staged_runtime.md`.

Build status is the one fact that goes the other way. No file here carries a build status of
its own. Every piece has a row in `running_evals.md`'s status table whatever mechanism it
belongs to, and the files whose subjects have a row link there.

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
