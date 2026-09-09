# Library

## Summary

This repository is not where evals are written. It is a library, distributed as a Python
package. A separate repository owns the plugins and their eval cases, installs this one, and
points it at its own tree.

- **Two repositories.** This one owns the backends, the CLI, the gate, the validator, the
  pinned wheel set and the image. The consumer owns its plugins, its cases and its logs.
- **One configuration file.** `cowork_evals.yaml` in the working directory. Nothing is read
  from the process environment, and there is no `.env`.
- **Two roots.** The installed package holds the code and the pins. The consumer's working
  directory holds the plugins and the logs. Nothing resolves a path under test from the
  package root.
- **Two kinds of code.** This package runs on a laptop and is unconstrained. The code under
  test runs in the CoWork VM and is bound to 3.10 and the image wheel set.
- **Nothing writes into the installed package**, and the container holds none of it.

This file is the boundary. The command surface is [cli.md](cli.md). What of it is built is
the status table in [running_evals.md](running_evals.md).

## The two repositories

| Repository   | Owns                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------ |
| This one     | The backends, the CLI, the gate, the case validator, the pinned CoWork wheel set, the image      |
| The consumer | Its plugins, their `evals/` trees, its `logs/`, its `cowork_evals.yaml`, and the pinned version of this package |

The consumer never runs `claude plugin eval`. That command is an implementation detail of the
Docker backend, and [cli.md](cli.md) is the whole surface a consumer sees.

## Installing

The repository is the distribution. `pyproject.toml` sits at its root and the backend is
hatchling, so a git reference builds the same wheel `scripts/build.sh` builds. It is not on
a package index yet, so a consumer installs from the repository:

```sh
uv add --dev "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.1"
pip install "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.1"
uv tool install "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.1"
```

The reference after `@` is a tag, a branch or a commit, and it is the pin. Dropping it tracks
the default branch. The third line installs the command outside any project, which is how a
consumer that runs the command but does not import it holds the pin.
[../README.md](../README.md) carries the same three lines, and it is what a consumer reads.
Once the package is on an index they become the name alone:

```sh
uv add --dev cowork-evals
pip install cowork-evals
```

The distribution is `cowork-evals` and the command is `cowork_evals`. `scripts/build.sh`
builds both artefacts into `dist/` and proves the wheel carries the Dockerfiles and the
requirements files; `uv publish` is what sends them, and this repository runs no publishing
step of its own.

`[project.scripts]` provides the `cowork_evals` executable. It is the one entry point: there
is no second, and no per-backend executable. `cowork_evals --version` prints the installed
distribution version from package metadata, and every run records it in `env.txt`, so a log
says which version produced it.

The consumer pins the version in its own `pyproject.toml`. That is the pin. The wheel set and
the image inventory are measurements of a VM that moves, so a consumer on an old version
mirrors an old VM. See [runtime.md](runtime.md).

## What ships

| Path                                      | Ships | Holds                                                              |
| ----------------------------------------- | ----- | ------------------------------------------------------------------ |
| `src/cowork_evals/`                       | yes   | The CoWork driver, the CLI, the backends, the gate, the validator  |
| `src/cowork_evals/data/requirements*.txt` | yes   | The pins the mirror and the image are built from                   |
| `src/cowork_evals/config.py`              | yes   | `cowork_evals.yaml`, and the frozen `Config` below                 |
| `src/cowork_evals/harness.py`             | yes   | The `claude plugin eval` argument list                             |
| `src/cowork_evals/cowork.py`              | yes   | The CoWork driver: one prompt in, one session document out         |
| `src/cowork_evals/cases.py`               | yes   | The case reader, backend-neutral. `CaseError` lives here           |
| `src/cowork_evals/grader.py`              | yes   | The four structural graders over a session document                |
| `src/cowork_evals/judge.py`               | yes   | The `claude -p` judge behind `llm` and `baseline`                  |
| `src/cowork_evals/results.py`             | yes   | The v1 `aggregate-result.json` document                            |
| `src/cowork_evals/requirements.py`        | yes   | The pinned requirements reader, and PEP 503 name normalization     |
| `src/cowork_evals/cowork_backend.py`      | yes   | The CoWork backend: the skip rule, `plan` and `run`                |
| `src/cowork_evals/validate.py`            | yes   | The case validator, and the skill coverage report                  |
| `src/cowork_evals/logs.py`                | yes   | The run directory, `env.txt`, `latest`, pruning and the tee        |
| `src/cowork_evals/gate.py`                | yes   | The gate over `aggregate-result.json`                              |
| `src/cowork_evals/preflight.py`           | yes   | Each backend's unmet conditions, for `check` and for `run`         |
| `src/cowork_evals/cli.py`                 | yes   | The parser, the five verbs, the dispatch and the exit codes        |
| `src/cowork_evals/docker/`                | yes   | The container backend: the digest, the argument lists, build, check and run |
| `src/cowork_evals/docker/Dockerfile`      | yes   | What `setup --docker` builds                                       |
| `src/cowork_evals/docker/Dockerfile.pytest` | yes | One layer over it, carrying pytest                                 |
| `src/cowork_evals/docker/pytest_image.py` | yes   | `PytestImage`: the test image's digest, build, check and run       |
| `src/cowork_evals/docker/probe.py`        | yes   | The parity probe, the one file here that is 3.10                   |
| `src/cowork_evals/docker/parity.py`       | yes   | The comparison, run on the host                                    |
| `scripts/`                                | no    | Development tasks for this repository only                         |
| `tests/`, `plugins/`, `docs/`, `plans/`   | no    | Development and reference material                                 |

A consumer never sees `scripts/`. Those are the tasks that build this repository's own
environments, run its tests and lint it, and they are named nowhere in [cli.md](cli.md). See
[../scripts/README.md](../scripts/README.md).

The table is enforced by the sdist include list in `pyproject.toml`, which names the package,
`README.md` and `LICENSE` and nothing else. `scripts/build.sh` fails if a development
directory reaches the sdist, or if a Dockerfile or a requirements file is missing from the
wheel.

The requirements files are shipped data, not documentation, because `setup --docker` reads
them at run time on a machine that has no checkout of this repository. They are measured from
a CoWork VM and recorded once. What they hold, and how they differ, is
[environments.md](environments.md).

## Package constraints

| Constraint            | Value    | In `pyproject.toml` | Reason                                                        |
| --------------------- | -------- | ------------------- | -------------------------------------------------------------- |
| `requires-python`     | `>=3.14` | yes                 | This package runs on a developer's laptop, never in a session |
| `dependencies`        | any      | yes                 | Nothing about CoWork constrains what this package imports     |
| ruff `target-version` | `py314`  | yes                 | The same. It lints this package, not the code under test      |
| `[tool.uv] package`   | removed  | yes                 | Removing it makes uv build a distribution                     |
| `license`             | `MIT`    | yes                 | A public repository with no license grants nothing            |
| `readme`              | `README.md` | yes              | It is the description an index renders                        |

The runtime dependencies are `PyYAML`, which parses `cowork_evals.yaml` and `case.yaml`,
`python-frontmatter`, which splits a `prompt.md` or a grader file into its `---` block and its
body, and `packaging`. Nothing here writes a parser, a glob engine or an HTTP client.

`package = false` was removed in the commit that added `src/cowork_evals/`, and not before,
because `uv sync` fails against a package with no package tree. `[project.scripts]` came in a
later commit and is unrelated to it.

`requires-python` is a floor, so it also sets the interpreter a consumer's development
environment needs. Lower it when a consumer on an older one asks. Nothing about CoWork forces
a value here.

## Where the restrictions are

Two kinds of code, and one of them is unconstrained. This package runs on a laptop and
controls CoWork. The code under test runs inside the CoWork VM, on that VM's interpreter and
that VM's wheels. A rule for one is never applied to the other.

| Restriction                                  | Binds                              | Written in                         |
| -------------------------------------------- | ---------------------------------- | ---------------------------------- |
| Python 3.10 syntax and standard library      | The code under test                | [runtime.md](runtime.md)           |
| The CoWork wheel set, and nothing outside it | The code under test                | [runtime.md](runtime.md)           |
| Python 3.14, and any dependency it justifies | This package, `scripts/`, `tests/` | [environments.md](environments.md) |
| Python 3.10, and pytest beside the wheel set | A consumer's own `tests/`          | [cowork_test.md](cowork_test.md)   |

The code under test is every file under the path a consumer passes to `cowork_evals run`,
meaning each skill, command, agent and hook in the plugin. It runs on the session interpreter
and imports only what the image carries.

Nothing in this package runs in a session. It drives CoWork from outside, so no CoWork fact
reaches it: not the interpreter version, not the wheel set, not the image.

Enforcing the first two rows on the code under test is a separate check from running an eval.
Whether that check is designed or built is the status table in
[running_evals.md](running_evals.md).

## The two roots

| Root         | Is                               | Holds                                      |
| ------------ | -------------------------------- | ------------------------------------------ |
| Package root | the installed distribution       | the code, the pins, the Dockerfile         |
| Project root | the consumer's working directory | the plugins, their `evals/` trees, `logs/` |

Nothing resolves a path under test from the package root. Every such path comes from the
CLI's path argument, and logs come from the working directory.

## What the consumer provides

A tree the CLI can be pointed at, and nothing else. A plugin is discovered by a
`.claude-plugin/plugin.json` with a sibling `evals/` directory, not by a fixed `plugins/*`
glob, because marketplace repositories do not share one layout. The case tree inside `evals/`
is [eval_format.md](eval_format.md), unchanged by which repository holds it.

Options are flags, and their defaults are keys in `cowork_evals.yaml`, in the working
directory, the directory `logs/` is resolved from. That file is the only configuration route:
nothing is read from the process environment, and there is no `.env`.

| Layer                 | Beats           | Is for                         |
| --------------------- | --------------- | ------------------------------ |
| A command-line option | every row below | one run                        |
| `cowork_evals.yaml`   | the default     | a consumer's standing settings |
| The built-in default  | nothing         | a machine that sets nothing    |

The file holds three sections, and a section is named for the thing that reads it. A new
setting goes in the section of whatever reads it, which is the rule the file is kept to.

| Section   | Read by                                                                     | Its keys and defaults are in         |
| --------- | --------------------------------------------------------------------------- | ------------------------------------ |
| `cowork:` | The CoWork driver                                                           | [cowork_driver.md](cowork_driver.md) |
| `eval:`   | The `claude plugin eval` argument list, and the CoWork backend's judge model | [running_evals.md](running_evals.md) |
| `docker:` | The container backend                                                       | [docker.md](docker.md)               |

```yaml
cowork:
  profile: <the Application Support profile directory name>
eval:
  model: sonnet
docker:
  platform: linux/arm64
```

| Rule                                                                                                 |
| ------------------------------------------------------------------------------------------------------ |
| A missing file, a missing section and a missing key each fall back to the built-in default           |
| An unknown key inside a known section is an error, so a typo is never a silent default               |
| A value of the wrong type is an error, wherever the `Config` was built from                          |
| An unknown top level section is ignored, so a later backend adds its own without touching the loader |
| `~` in a path is expanded, and a relative path resolves against the working directory                |

`cowork_evals.yaml` names a profile, which is an identifier, so it is never committed. The
public repository rule in [../README.md](../README.md) applies to every value in it.
`../cowork_evals.example.yaml` is the committed template: every key, every default, and a
placeholder for the profile.

## Where state lives

| Thing           | Path                                      | Written by       |
| --------------- | ----------------------------------------- | ---------------- |
| Container image | tag `cowork-evals:<digest>`               | `setup --docker` |
| Test image      | tag `cowork-evals-test:<digest>`          | `setup --docker` |
| Container login | `docker.login_dir`                        | `setup --docker` |
| Run logs        | `./logs/evals/<yyyymmdd-hhmmss>-<scope>/` | `run`            |

Nothing writes into the installed package, and nothing writes a build product into the
consumer checkout. `test` is the one command whose container writes into the tree it is
pointed at, and what lands there is pytest's own: `.pytest_cache`, `__pycache__` and whatever
the suite writes. See [cowork_test.md](cowork_test.md). The consumer git-ignores `logs/`,
`cowork_evals.yaml` and those, and nothing else.

Each image digest covers every input that changes that image, so a changed input produces a
different tag rather than a stale hit. The first is defined in [docker.md](docker.md) and the
second in [cowork_test.md](cowork_test.md), which hashes the first. A digest that
does not match is a failed preflight, never a silent run against a stale artefact. See
[cli.md](cli.md).

Logs are resolved from the working directory, not from either root, and `--out` overrides
them. A consumer running the CLI from its checkout gets `logs/` in its checkout.

## The container holds none of this package

The image is an execution environment and nothing more: the OS, the interpreter, the wheels,
the document tooling, the fonts and the Claude Code CLI. The `cowork_evals` process stays on
the host, builds the `docker run` argument list, and reads the result document back out of the
mounted log directory. Run naming, pruning and the gate therefore happen in one place for both
backends, and the package is never installed into an image or mounted into a container. See
[docker.md](docker.md).
