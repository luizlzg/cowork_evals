# Environment passthrough: get a credential into the container

## The problem

A skill that needs a credential cannot be evaluated.

A skill calls an API and reads the key from an environment variable. Every variable the
container gets is written in `run_preamble` and `run_argv`, and all of them are this
package's own: `HOME`, the enablement flag, `TMPDIR` when the run keeps its traces, and
`NODE_EXTRA_CA_CERTS` when a certificate file is configured. None is a route a case can use.

That is not an omission. This repository has one configuration route and reads nothing from
the process environment, which is why a run is reproducible from `cowork_evals.yaml` alone
and why no `.env` can change what a suite did. The rule is in `CLAUDE.md` and in
[`../docs/library.md`](../docs/library.md).

The rule is too strict in exactly one way. A skill whose whole job is calling an API cannot
be evaluated at all: it fails in every eval for a reason that has nothing to do with the
skill, and the person writing the case can do nothing about it. This plan cuts the one hole
the rule needs and keeps everything else about it.

## What this plan does

The config file lists which environment variables to pass from your machine into the
container. The backend passes them.

The values must not end up anywhere else: not in a log, not in the result file, not in a failure
line, not in the dry-run output. The names may, so you can see what was passed.

It changes a rule this repository states in two places: nothing is read from the process
environment. After this, one thing is, it is listed in the config file, and it is passed
straight through rather than read and used here.

Branch: `feat/env-passthrough`.

## Docker only

The setting is in the `docker:` section because only that backend starts a process whose
environment this package writes. Nothing here reaches inside the VM, and a session decides
its own environment, which is why `env:` is already a key the CoWork backend cannot honour.
That is the rule for the split, and it is not a build-order accident.

Two kinds of case depend on a forwarded variable, and they land differently. A case that
writes `env:` carries the `no-cowork` tag, which
[`../docs/eval_format.md`](../docs/eval_format.md) defines and the validator enforces, so it
never reaches a CoWork run. A case whose skill simply reads a variable writes
nothing, carries no tag, and fails on CoWork for a missing credential. That is left as it is:
it is the skill failing the way it would fail in a session that never had the credential,
which is a true result and not a defect in this package.

## What a value may never touch

| Artefact                    | Carries the name | Carries the value |
| --------------------------- | ---------------- | ----------------- |
| `cowork_evals.yaml`         | yes              | no                |
| `env.txt`                   | yes              | no                |
| `run.log`                   | yes              | no                |
| `debug.txt`                 | yes              | no                |
| `aggregate-result.json`     | no               | no                |
| A failure line              | no               | no                |
| `--dry-run` output          | yes              | no                |
| The container's environment | yes              | yes               |

`run.log` is captured at the file descriptor level, so whatever the container prints reaches
it. That is the one artefact this plan cannot fully control, and phase 4 measures it rather
than asserting it.

## Two rules this plan settles

| Rule                                                                   | Why                                                                                                                                 |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| A named variable that is absent from the host refuses at the preflight | A missing precondition fails. It never forwards an empty string, which would be a run that looks configured and is not              |
| This is never a route for Claude's own credential                      | The container login is the one credential route, and `docs/docker.md` says so. The preflight refuses the names that would carry one |

The second is a refusal, so it is a restriction, and the developer asked for it rather than
this plan inventing it. The container login is the one credential route, and this never
becomes a second one.

## What this plan does not do

| Not in scope                                  | Where it is instead                                                                                               |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Anything on the CoWork backend                | Nowhere. A session decides its own environment                                                                    |
| A `.env` file, or reading an unnamed variable | Nowhere. One configuration file, and it names them                                                                |
| Forwarding into the test image                | Nowhere. `cowork_evals test` runs pytest and takes a raw tail: [`../docs/cowork_test.md`](../docs/cowork_test.md) |

## Orientation

| Fact                                                         | Where                                                                                  |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Every variable the container gets today                      | `src/cowork_evals/docker/__init__.py`, `run_preamble`, `run_argv`, `extra_ca_env_argv` |
| The enablement variable, a constant and not a setting        | `src/cowork_evals/harness.py`, `ENABLEMENT_ENV`                                        |
| `env.txt`, and what it records                               | `src/cowork_evals/logs.py`, `write_env`                                                |
| The configuration sections and the ladder over them          | `src/cowork_evals/config.py`                                                           |
| The preflight dispatch                                       | `src/cowork_evals/preflight.py`, `checks`                                              |
| The Docker backend's own conditions, which is where these go | `src/cowork_evals/docker/__init__.py`, `Docker.check`                                  |
| The `EVAL_` prefix a case's own `env` keys carry             | `src/cowork_evals/validate.py`, `ENV_PREFIX`                                           |
| The rule this plan amends                                    | [`../docs/library.md`](../docs/library.md), and `CLAUDE.md`                            |
| The one credential route                                     | [`../docs/docker.md`](../docs/docker.md)                                               |

## Phases

### Phase 1: the setting

- [x] `docker.env_passthrough`, a list of variable names, defaulting to empty. In the
      `docker:` section, because the container backend is what reads it
- [x] A name that is not a plausible environment variable name is refused at load, with the
      message naming the line
- [x] Empty by default, so a repository that names none behaves exactly as it does today

### Phase 2: the preflight

- [x] A named variable absent from the process environment is an unmet condition, one line
      per name, and `run` exits 3
- [x] A named variable present and empty is the same unmet condition. An empty string is not
      a value
- [x] A name that would carry Claude's own credential is refused whatever its value, and the
      message names the container login as the route
- [x] `check --docker` reports the same conditions, so a developer sees them without starting
      a run
- [x] Every message names the variable and never its value

### Phase 3: the forwarding

- [x] `run_preamble` forwards each named variable, beside the variables it already writes
- [x] The forwarded names are read once, where the preflight already read them, and are not
      read a second time at container start
- [x] `env.txt` records the forwarded names on one line, and no value
- [x] `--dry-run` prints the container argument list with each forwarded name and its value
      replaced, so a dry run is safe to paste into a message
- [x] A dry run reads no value at all, and so prints the list with every configured name
      whether or not the host has it set. `cli._run` skips the preflight on `--dry-run`, so
      the refusal in phase 2 has not run, and a dry run reaching nothing behind the preflight
      is the rule that verb already holds

### Phase 4: measure what leaks

Assertions, not arguments. Each box is a container run and a grep over what it produced.

- [x] Forward one variable holding a known unique token, run `plugins/smoke/`, and grep
      `run.log`, `env.txt`, `debug.txt`, `report.html` and `aggregate-result.json` for the
      token. Record what was found and where, dated, in
      [`../docs/docker.md`](../docs/docker.md)
- [x] Run the same case with `--dry-run` and grep the output for the token
- [x] If `run.log` carries the token because the container printed it, write that down in
      that file as a limit rather than removing the feature. What the container prints is the
      container's

### Phase 5: tests

Unit tier, except phase 4's runs.

- [x] A configured name absent from the environment yields the preflight condition
- [x] A configured name present and empty yields the same condition
- [x] A credential name yields the refusal, whatever its value
- [x] `run_preamble` carries the forwarded name and value
- [x] `write_env` carries the name and not the value
- [x] The dry-run output carries the name and not the value
- [x] The dry-run output carries a configured name that is unset on the host, and the command
      exits 0
- [x] An empty `env_passthrough` produces the argument list this package produces today, byte
      for byte

### Phase 6: documentation

- [x] [`../docs/library.md`](../docs/library.md): the rule that nothing is read from the
      process environment is amended to the one exception, with the two rules above
- [x] `CLAUDE.md`: the same amendment, in the one-config-file rule
- [x] [`../docs/docker.md`](../docs/docker.md): the setting, the preflight, what is
      forwarded, the credential refusal, and phase 4's measurement
- [x] [`../docs/cli.md`](../docs/cli.md): the preflight table gains the new conditions
- [x] [`../docs/running_evals.md`](../docs/running_evals.md): `env.txt` gains its row
- [x] `src/cowork_evals/data/cowork_evals.example.yaml` carries the key, commented, with no
      value. That file is what `init` writes, so a consumer sees the key without reading a
      document
- [x] Nothing in `plans/done/` is read or corrected

### Phase 7: integration

- [ ] `plugins/smoke/` on the Docker backend with one variable forwarded, from the
      integration tier, green
- [ ] The same with the variable unset on the host, exit 3, naming the variable
- [ ] `scripts/test.sh` and `ruff` clean
