# Documentation

Reference material for running evals against Claude CoWork. Read the page that covers what
you are about to change, and link to it rather than restating it.

Evals are not written here. This repository is a library, installed by the repository that
owns the plugins under test. [`library.md`](library.md) is that boundary and
[`cli.md`](cli.md) is the command a consumer runs.

An eval is written once, in the format at [`eval_format.md`](eval_format.md), and runs on
any of the three backends. [`approaches.md`](approaches.md) says which backend honours which
part of it.

| Page                                             | Covers                                                          |
| ------------------------------------------------ | --------------------------------------------------------------- |
| [`library.md`](library.md)                       | The boundary: what ships, how it installs, where state lives    |
| [`cli.md`](cli.md)                               | The `cowork_evals` command: verbs, backends, scope, exit codes  |
| [`approaches.md`](approaches.md)                 | The three backends, the one case format, and what each proves   |
| [`eval_format.md`](eval_format.md)               | What a case file contains: tree, frontmatter, graders, traps    |
| [`running_evals.md`](running_evals.md)           | The eval system: mirror, pinned flags, gate, logs, cadence      |
| [`docker.md`](docker.md)                         | The container that reproduces the CoWork image                  |
| [`cowork_driver.md`](cowork_driver.md)           | Driving CoWork from a script: API, sequence, result document    |
| [`runtime.md`](runtime.md)                       | What a CoWork session provides and what is on the image         |
| [`environments.md`](environments.md)             | The two Python environments and how to build them               |
| [`staged_runtime.md`](staged_runtime.md)         | The 3.10 runtime staged into a plugin so a sandboxed case reaches it |
| [`plugin_eval.md`](plugin_eval.md)               | `claude plugin eval`: availability, flags, harness limits, cost |
| [`cowork_desktop.md`](cowork_desktop.md)         | Desktop application internals: deep links, session filesystem   |
| [`data/requirements.txt`](data/requirements.txt) | `pip freeze` from a CoWork VM, 136 pins, verbatim               |
| [`data/requirements_installable.txt`](data/requirements_installable.txt) | The same minus the 9 pins that cannot install off the VM |

Three pages are measurements: `runtime.md`, `cowork_desktop.md` and `data/`. Each carries
its capture date, is a snapshot rather than a contract, and is re-probed when the thing it
describes changes. `staged_runtime.md` is design carrying a dated snapshot, and says so.

Three pages are neither. `eval_format.md` is the authoring contract a case is written to,
`plugin_eval.md` describes a Claude Code command this repository does not own and carries
the CLI version it was written against, and `environments.md` marks which of its routes are
built and which are design. Every other page is design and says so at the top.

`data/` is shipped data rather than reference material. It moves into the package when the
package is built, and [`library.md`](library.md) says so.

A page here never links to a plan. Anything durable a plan establishes is written into one
of these pages while the work happens, so no page here depends on a plan file.

## Provenance

Adapted from an internal marketplace repository, which is not public. Absolute paths are
redacted, because this repository is public.

| Source document             | Adapted into                             |
| --------------------------- | ---------------------------------------- |
| `dev/environment.md`        | [`environments.md`](environments.md)     |
| `dev/runtime.md`            | [`runtime.md`](runtime.md)               |
| `dev/data/requirements*`    | [`data/`](data/)                         |
| `plan_evals_claude_code.md` | [`plugin_eval.md`](plugin_eval.md)       |
| `plan_run_cowork.md`        | [`cowork_desktop.md`](cowork_desktop.md) |

Writing rules are in [`../CLAUDE.md`](../CLAUDE.md). The public repository rule is in
[`../README.md`](../README.md), and it applies to every page here.
