# Approaches

Three ways to run an eval against a CoWork skill. They answer different questions. None
replaces another.

Which of the three is built is the status table in
[running_evals.md](running_evals.md).

| Approach                   | Runs on                      | Proves                                     | Design                               |
| -------------------------- | ---------------------------- | ------------------------------------------ | ------------------------------------- |
| Claude Code, mirrored venv | Local `claude`, Python 3.10  | Skill logic, activation, hook gates        | [running_evals.md](running_evals.md) |
| Claude Code, Docker        | Local `claude`, Ubuntu 22.04 | The above plus rendering, OCR, fonts, CLIs | [docker.md](docker.md)               |
| CoWork, driven directly    | The real CoWork VM           | The deployed stack, end to end             | [cowork_driver.md](cowork_driver.md) |

This is the one copy of that table. [`../README.md`](../README.md) introduces the same three
approaches in prose and links here.

## One case format, three backends

An eval is written once, in the `claude plugin eval` case format: a `prompt.md` carrying
frontmatter and the prompt body, a `graders/` directory, and an optional `case.yaml`. It is
the only eval format in this repository, and [eval_format.md](eval_format.md) is what
owns it.

The same case tree runs on all three approaches. Only the backend changes.

| Approach      | Command                            | Executes a case                        | Grades with        |
| ------------- | ---------------------------------- | -------------------------------------- | ------------------ |
| Mirrored venv | `cowork_evals run --venv <path>`   | `claude plugin eval`                   | the harness        |
| Docker        | `cowork_evals run --docker <path>` | `claude plugin eval`, in the container | the harness        |
| CoWork        | `cowork_evals run --cowork <path>` | the desktop driver                     | the CoWork grader  |

One executable, one path argument, one backend flag. The full surface is
[cli.md](cli.md).

Every backend writes the same `aggregate-result.json` v1 document into the same log
directory, so one gate decides pass and fail identically for all three.

## What each backend honours

The first two backends run the same harness and differ only in the host, so a case behaves
the same on both. The CoWork backend submits a prompt to a live session and reads what the
session wrote, so it honours a subset of the format.

| Case feature                                            | Claude Code backends | CoWork backend                          |
| ------------------------------------------------------- | -------------------- | --------------------------------------- |
| `prompt.md` body                                        | yes                  | yes                                     |
| `regex`, `tool_used`, `tool_order` graders              | yes                  | yes                                     |
| `file_exists` grader                                    | any created file     | files under `outputs/` only             |
| `llm` and `baseline` graders                            | yes                  | yes, judged by a separate call          |
| `runs`, `max_turns`, `timeout_seconds`                  | yes                  | no, one run per case, one timeout       |
| `model`, `allowed_tools`, `append_system_prompt`, `env` | yes                  | no, the session decides                 |
| `context.add_dirs`, `context.scaffold_script`           | yes                  | no, nothing stages files into the VM    |
| `mocks/`                                                | yes                  | no, the MCP servers are the real ones   |
| `arm:` on a grader                                      | read, but inert      | no                                      |

`arm:` is read on the Claude Code backends and changes nothing, because `--ablation` is
pinned to `none` and no baseline arm runs. There is no baseline arm on any backend, so
`--ablation with-without` is not reachable through this command at all. See
[running_evals.md](running_evals.md).

A case that writes out a key the CoWork backend cannot honour is reported by that backend as
skipped, never as passed. A default is not a request, so a case that writes no `runs` key
runs once rather than skipping; the exact rule is in
[running_evals.md](running_evals.md). A command-line option a backend cannot honour is a
usage error instead, and the difference is stated in [cli.md](cli.md).

## Claude Code as a proxy for CoWork

`claude plugin eval` loads one plugin into a fresh isolated session, runs each case, and
scores it with graders. It is the only harness that knows how to load a plugin, so it is the
harness two of these backends use. See [plugin_eval.md](plugin_eval.md). It is not part of
the command surface: a consumer never invokes it.

What it gets right: the skill files under test are the ones that ship, activation is decided
by the real model, and hook gates fire.

What it gets wrong: it is not CoWork. Different model routing, no admin-applied enterprise
prompt, no CoWork MCP servers, and the host is a development laptop rather than an Ubuntu
22.04 aarch64 VM. See [runtime.md](runtime.md) for the size of that gap.

Two ways to narrow the host half of the gap:

**The mirrored virtual environment.** A cached virtual environment pins Python 3.10 and the
wheel set a session provides, and nothing else. It catches an import that does not exist on
the image and an API that changed between versions. Cheap and fast. What it leaves diverging
is in [environments.md](environments.md).

The mirror is not put on `PATH` as it is built. Granting `Bash` turns on an OS sandbox whose
readable set leaves out a virtual environment's interpreter and standard library. The backend
copies a relocatable interpreter and the mirror's `site-packages` into the plugin under test
and puts that on `PATH`. That set, and the copy, are
[staged_runtime.md](staged_runtime.md).

**Docker.** A container from `ubuntu:22.04` with the same interpreter, wheels, document
tooling and fonts, and on an ARM Mac the same architecture. It costs an image build and a
slower run, so it is the pre-release gate rather than the iteration loop. See
[docker.md](docker.md).

## CoWork, driven directly

The most accurate result, because it is the deployed stack. CoWork exposes no scriptable
entry point, so the only route is to drive the desktop application: submit a prompt through
its `claude://` URL scheme, press Return with a synthetic keystroke, and read the
transcript, audit log and outputs the session writes to the host filesystem. See
[cowork_desktop.md](cowork_desktop.md).

The costs. None is reduced by better engineering.

| Cost                                                        | Detail                                    |
| ----------------------------------------------------------- | ----------------------------------------- |
| Couples to application internals no release promises to keep | [cowork_desktop.md](cowork_desktop.md)    |
| Needs a macOS Accessibility grant, so no headless and no CI  | [cowork_desktop.md](cowork_desktop.md)    |
| Drives a live account, so a case can reach real mail         | [cowork_driver.md](cowork_driver.md)      |
| Leaves a permanent session in that account's history         | [cowork_driver.md](cowork_driver.md)      |
| Costs a VM boot plus a full agentic run, so minutes per case | [cowork_desktop.md](cowork_desktop.md)    |

It is the pre-release confirmation, run by a person on purpose. It is never a commit gate.

## Which to use when

This is the cadence a consumer repository follows. It is the one copy;
[running_evals.md](running_evals.md) links here rather than repeating it.

| Moment              | Command                                                    | Enforced by           |
| ------------------- | ----------------------------------------------------------- | --------------------- |
| `git commit`        | nothing                                                    | no hook, by design    |
| Writing a case      | `cowork_evals run --venv <plugin>/evals/<skill>/<case>`    | the author            |
| Before opening a PR | `cowork_evals run --venv <plugin>/evals`, per plugin       | the PR template       |
| Before a release    | `cowork_evals run --docker <root>`, then a CoWork smoke set | the release checklist |

Which of these commands is built is the status table in
[running_evals.md](running_evals.md), and [docker.md](docker.md) says what reaches the
container until the `--docker` one is.
