# Library

This repository is not where evals are written. It is a library, distributed as a Python
package. A separate repository owns the plugins and their eval cases, installs this one, and
points it at its own tree.

This page is the boundary. The command surface is [cli.md](cli.md).

Design. Nothing here is built. What is built is the status table in
[running_evals.md](running_evals.md).

## The two repositories

| Repository   | Owns                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------- |
| This one     | The three backends, the CLI, the gate, the case validator, the pinned CoWork wheel set, the image |
| The consumer | Its plugins, their `evals/` trees, its `logs/`, its `.env`, and the pinned version of this package |

The consumer never runs `claude plugin eval`. That command is an implementation detail of
two of the three backends, and [cli.md](cli.md) is the whole surface a consumer sees.

## Installing

```sh
uv add --dev cowork-evals
pip install cowork-evals
```

`[project.scripts]` provides the `cowork_evals` executable. `cowork_evals --version` prints
the installed distribution version from package metadata, and every run records it in
`env.txt`, so a log says which version produced it.

The consumer pins the version in its own `pyproject.toml`. That is the pin. The wheel set
and the image inventory are measurements of a VM that moves, so a consumer on an old version
mirrors an old VM. See [runtime.md](runtime.md).

## What ships

| Path                                       | Ships | Holds                                              |
| ------------------------------------------ | ----- | -------------------------------------------------- |
| `src/cowork_evals/`                        | yes   | The CLI, the three backends, the gate, the validator |
| `src/cowork_evals/data/requirements*.txt`  | yes   | The pins the mirror and the image are built from   |
| `src/cowork_evals/docker/Dockerfile`       | yes   | What `setup --docker` builds                       |
| `scripts/`                                 | no    | Development tasks for this repository only         |
| `tests/`, `plugins/`, `docs/`, `plans/`    | no    | Development and reference material                 |

A consumer never sees `scripts/`. Those are the tasks that build this repository's own
environments, run its tests and lint it, and they are named nowhere in
[cli.md](cli.md). See [../scripts/README.md](../scripts/README.md).

The two requirements files are shipped data, not documentation, because `setup --venv` and
`setup --docker` read them at run time on a machine that has no checkout of this repository.
They are measured from a CoWork VM and recorded once. What they hold, and how they differ,
is [environments.md](environments.md).

## Package constraints

| Constraint            | Value    | In `pyproject.toml` | Reason                                                        |
| --------------------- | -------- | ------------------- | -------------------------------------------------------------- |
| `requires-python`     | `>=3.14` | yes                 | This package runs on a developer's laptop, never in a session |
| `dependencies`        | few      | empty today         | Nothing about CoWork constrains what this package imports     |
| ruff `target-version` | `py314`  | yes                 | The same. It lints this package, not the code under test      |
| `[tool.uv] package`   | removed  | **no**              | Removing it makes uv build a distribution, and `src/cowork_evals/` does not exist yet |

`package = false` is the one row `pyproject.toml` does not yet carry. It is removed in the
same commit that adds `src/cowork_evals/` and `[project.scripts]`, and not before, because
`uv sync` fails against a package with no package tree.

`requires-python` is a floor, so it also sets the interpreter a consumer's development
environment needs. Lower it when a consumer on an older one asks. Nothing about CoWork
forces a value here.

A dependency is allowed. This package is a consumer's development dependency, so the list is
kept short and every entry is named below with what needs it, but there is no rule against
one. `dependencies` is empty today because nothing has needed one yet.

| Dependency | Needed by | Added when |
| ---------- | --------- | ---------- |
| none yet   |           |            |

## Where the restrictions are

Two kinds of code, and one of them is unconstrained. This package runs on a laptop and
controls CoWork. The code under test runs inside the CoWork VM, on that VM's interpreter and
that VM's wheels. A rule for one is never applied to the other.

| Restriction                                  | Binds                                  | Written in                         |
| -------------------------------------------- | --------------------------------------- | ---------------------------------- |
| Python 3.10 syntax and standard library      | The code under test                     | [runtime.md](runtime.md)           |
| The CoWork wheel set, and nothing outside it | The code under test                     | [runtime.md](runtime.md)           |
| Python 3.14, and any dependency it justifies | This package, `scripts/`, `tests/`      | [environments.md](environments.md) |

The code under test is every file under the path a consumer passes to `cowork_evals run`,
meaning each skill, command, agent and hook in the plugin. It runs on the session
interpreter and imports only what the image carries.

Nothing in this package runs in a session. It drives CoWork from outside, so no CoWork fact
reaches it: not the interpreter version, not the wheel set, not the image.

Enforcing the first two rows on the code under test is a separate check from running an
eval. It is not designed and not built; see the status table in
[running_evals.md](running_evals.md).

## The two roots

| Root         | Is                                | Holds                                        |
| ------------ | --------------------------------- | -------------------------------------------- |
| Package root | the installed distribution        | the code, the pins, the Dockerfile           |
| Project root | the consumer's working directory  | the plugins, their `evals/` trees, `logs/`   |

Nothing resolves a path under test from the package root. Every such path comes from the
CLI's path argument, and logs come from the working directory.

## What the consumer provides

A tree the CLI can be pointed at, and nothing else. A plugin is discovered by a
`.claude-plugin/plugin.json` with a sibling `evals/` directory, not by a fixed `plugins/*`
glob, because marketplace repositories do not share one layout. The case tree inside
`evals/` is [eval_format.md](eval_format.md), unchanged by which repository holds it.

Options are flags, and their defaults are environment variables. Those variables are written
in a `.env` file in the working directory, the directory `logs/` is resolved from. A shell or
a CI job may set a variable directly instead, and wins when it does.

| Layer                           | Beats           | Is for                                  |
| ------------------------------- | --------------- | --------------------------------------- |
| A command-line option           | every row below | one run                                 |
| The process environment         | `.env`          | CI, and a one-off `EVAL_MODEL=opus ...` |
| `.env` in the working directory | the default     | a consumer's standing settings          |
| The built-in default            | nothing         | a machine that sets nothing             |

`.env` holds `KEY=value` lines, `#` comments and blank lines. No `export`, no shell
expansion, and no quoting beyond a matched pair of quotes around a value. A key the CLI does
not recognise is ignored, because a consumer's `.env` serves more than this command.

`.env` is never committed. It carries `ANTHROPIC_API_KEY`, and the public repository rule in
[../README.md](../README.md) applies to every other value in it as well.

| Variables                                                | Named in                             |
| ---------------------------------------------------------- | ------------------------------------ |
| `EVAL_MODEL`, `EVAL_JUDGE_MODEL`, `EVAL_ALLOW_TOOLS`, `EVAL_MAX_COST_USD`, `EVAL_MAX_COST_TOTAL_USD` | [running_evals.md](running_evals.md) |
| `EVAL_PLATFORM`                                          | [docker.md](docker.md)               |
| `COWORK_*`                                               | [cowork_driver.md](cowork_driver.md) |
| `ANTHROPIC_API_KEY`                                      | [docker.md](docker.md)               |
| `CLAUDE_CODE_WALNUT_SPIRE`                               | [plugin_eval.md](plugin_eval.md)     |

## Where state lives

| Thing            | Path                                             | Written by       |
| ---------------- | ------------------------------------------------ | ---------------- |
| CoWork mirror    | `~/.cache/cowork_evals/venv-<digest>/`           | `setup --venv`   |
| Container image  | tag `cowork-evals:<digest>`                      | `setup --docker` |
| Run logs         | `./logs/evals/<yyyymmdd-hhmmss>-<scope>/`        | `run`            |
| Staged runtime   | `<plugin>/.cowork-runtime/`, for the length of a run | `run --venv` |

Nothing writes into the installed package. One thing writes a build product into the
consumer checkout: the venv backend stages a runtime inside the plugin under test for the
length of a run, and removes it when the run ends. See
[staged_runtime.md](staged_runtime.md). The consumer git-ignores `logs/`,
`.cowork-runtime/` and `.env`, and nothing else.

Both digests cover every input that changes the artefact, so a changed input produces a
different path or tag rather than a stale hit. The mirror digest is the sha256 of
`requirements_installable.txt` and the interpreter version. The image digest is defined in
[docker.md](docker.md).

A digest that does not match is a failed preflight, never a silent run against a stale
artefact. See [cli.md](cli.md).

Logs are resolved from the working directory, not from either root, and `--out` overrides
them. A consumer running the CLI from its checkout gets `logs/` in its checkout.

## The container holds none of this package

The image is an execution environment and nothing more: the OS, the interpreter, the wheels,
the document tooling, the fonts and the Claude Code CLI. The `cowork_evals` process stays on
the host, builds the `docker run` argument list, and reads the result document back out of
the mounted log directory. Run naming, pruning and the gate therefore happen in one place
for all three backends, and the package is never installed into an image or mounted into a
container. See [docker.md](docker.md).
