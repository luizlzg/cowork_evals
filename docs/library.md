# Library

This repository is not where evals are written. It is a library, distributed as a Python
package. A separate repository owns the plugins and their eval cases, installs this one, and
points it at its own tree.

This page is the boundary. The command surface is [cli.md](cli.md).

## Status

Not built. The design below is settled.

## The two repositories

| Repository   | Owns                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------- |
| This one     | The three backends, the CLI, the gate, the case validator, the pinned CoWork wheel set, the image |
| The consumer | Its plugins, their `evals/` trees, its `logs/`, and the pinned version of this package            |

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
They are measured from a CoWork VM and recorded once. They sit at [data/](data/) today and
move into the package when it is built, keeping one copy either way.

## Package constraints

| Constraint             | Value    | Reason                                                            |
| ---------------------- | -------- | ----------------------------------------------------------------- |
| `requires-python`      | `>=3.10` | It is a development dependency of somebody else's project         |
| `dependencies`         | empty    | The same. Standard library only                                   |
| ruff `target-version`  | `py310`  | Shipped code is written under 3.14 and must not use newer syntax  |
| `[tool.uv] package`    | removed  | The repository currently declares itself not a package            |

The repository's own `.venv` stays at 3.14 for tooling and tests. See
[environments.md](environments.md).

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

There is no configuration file. Options are flags, and their defaults are the `EVAL_*` and
`COWORK_*` environment variables named in [running_evals.md](running_evals.md) and
[cowork_driver.md](cowork_driver.md). A consumer sets them in its own shell or CI. A third
precedence layer between flag and environment would buy nothing.

## Where state lives

| Thing            | Path                                             | Written by       |
| ---------------- | ------------------------------------------------ | ---------------- |
| CoWork mirror    | `~/.cache/cowork_evals/venv-<digest>/`           | `setup --venv`   |
| Container image  | tag `cowork-evals:<digest>`                      | `setup --docker` |
| Run logs         | `./logs/evals/<yyyymmdd-hhmmss>-<scope>/`        | `run`            |

Nothing writes into the installed package. Nothing writes a build product into the consumer
checkout. The consumer git-ignores `logs/` and nothing else.

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
