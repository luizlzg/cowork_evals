# Environment passthrough: get a credential into the container

## The problem

A skill that needs a credential cannot be evaluated.

A skill calls an API and reads the key from an environment variable. The container an eval
runs in is given two environment variables, `HOME` and one internal flag, and there is no way
to add another. The skill fails in every eval, for a reason that has nothing to do with the
skill, and the person writing the case can do nothing about it.

## What this plan does

The config file lists which environment variables to pass from your machine into the
container. The backend passes them.

The values must not end up anywhere else: not in a log, not in the result file, not in a gate
line, not in the dry-run output. The names may, so you can see what was passed.

It changes a rule this repository states in two places: nothing is read from the process
environment. After this, one thing is, it is listed in the config file, and it is passed
straight through rather than read and used here.

Branch: `feat/env-passthrough`.

## Docker only

A case that needs an environment variable writes `env:`, and `env:` is exactly a key the
CoWork backend cannot honour: nothing sets a variable inside the VM, and a session decides
its own environment. So this is a Docker backend feature, and a case that depends on it is a
case [`plan_runnability.md`](plan_runnability.md) has already made declare itself.

That is the rule for the split, and it is not a build-order accident.

## What a value may never touch

| Artefact                          | Carries the name | Carries the value |
| --------------------------------- | ---------------- | ----------------- |
| `cowork_evals.yaml`               | yes              | no                |
| `env.txt`                         | yes              | no                |
| `run.log`                         | yes              | no                |
| `debug.txt`                       | yes              | no                |
| `aggregate-result.json`           | no               | no                |
| A gate line                       | no               | no                |
| `--dry-run` output                | yes              | no                |
| The container's environment       | yes              | yes               |

`run.log` is captured at the file descriptor level, so whatever the container prints reaches
it. That is the one artefact this plan cannot fully control, and phase 4 measures it rather
than asserting it.

## Two rules this plan settles

| Rule                                                                     | Why                                                     |
| -------------------------------------------------------------------------- | --------------------------------------------------------- |
| A named variable that is absent from the host refuses at the preflight    | A missing precondition fails. It never forwards an empty string, which would be a run that looks configured and is not |
| This is never a route for Claude's own credential                         | The container login is the one credential route, and `docs/docker.md` says so. The preflight refuses the names that would carry one |

The second is a refusal, so it is a restriction, and it is one
[`plan_believable_results.md`](plan_believable_results.md) already decided rather than one
invented here.

## What this plan does not do

| Not in scope                                             | Where it is instead                              |
| ----------------------------------------------------------- | -------------------------------------------------- |
| Anything on the CoWork backend                             | Nowhere. A session decides its own environment    |
| A `.env` file, or reading an unnamed variable              | Nowhere. One configuration file, and it names them |
| Forwarding into the test image                             | Nowhere. `cowork_evals test` runs pytest and takes a raw tail: [`../docs/cowork_test.md`](../docs/cowork_test.md) |

## Orientation

| Fact                                                 | Where                                                |
| ------------------------------------------------------- | ------------------------------------------------------ |
| The container's two variables                          | `src/cowork_evals/docker/__init__.py`, `run_preamble` |
| The enablement variable, a constant and not a setting  | `src/cowork_evals/harness.py`, `ENABLEMENT_ENV`       |
| `env.txt`, and what it records                         | `src/cowork_evals/logs.py`, `write_env`               |
| The configuration sections and the ladder over them    | `src/cowork_evals/config.py`                          |
| The preflight, one function per backend                | `src/cowork_evals/preflight.py`                       |
| The `EVAL_` prefix a case's own `env` keys carry       | `src/cowork_evals/validate.py`, `ENV_PREFIX`          |
| The rule this plan amends                              | [`../docs/library.md`](../docs/library.md), and `CLAUDE.md` |
| The one credential route                               | [`../docs/docker.md`](../docs/docker.md)              |

## Phases

### Phase 1: the setting

- [ ] `docker.env_passthrough`, a list of variable names, defaulting to empty. In the
      `docker:` section, because the container backend is what reads it
- [ ] A name that is not a plausible environment variable name is refused at load, with the
      message naming the line
- [ ] Empty by default, so a repository that names none behaves exactly as it does today

### Phase 2: the preflight

- [ ] A named variable absent from the process environment is an unmet condition, one line
      per name, and `run` exits 3
- [ ] A named variable present and empty is the same unmet condition. An empty string is not
      a value
- [ ] A name that would carry Claude's own credential is refused whatever its value, and the
      message names the container login as the route
- [ ] `check --docker` reports the same conditions, so a developer sees them without starting
      a run
- [ ] Every message names the variable and never its value

### Phase 3: the forwarding

- [ ] `run_preamble` forwards each named variable, beside `HOME` and the enablement flag
- [ ] The forwarded names are read once, where the preflight already read them, and are not
      read a second time at container start
- [ ] `env.txt` records the forwarded names on one line, and no value
- [ ] `--dry-run` prints the container argument list with each forwarded name and its value
      replaced, so a dry run is safe to paste into a message

### Phase 4: measure what leaks

Assertions, not arguments. Each box is a container run and a grep over what it produced.

- [ ] Forward one variable holding a known unique token, run `plugins/smoke/`, and grep
      `run.log`, `env.txt`, `debug.txt`, `report.html` and `aggregate-result.json` for the
      token. Record what was found and where, dated, in
      [`../docs/docker.md`](../docs/docker.md)
- [ ] Run the same case with `--dry-run` and grep the output for the token
- [ ] If `run.log` carries the token because the container printed it, write that down in
      that file as a limit rather than removing the feature. What the container prints is the
      container's

### Phase 5: tests

Unit tier, except phase 4's runs.

- [ ] A configured name absent from the environment yields the preflight condition
- [ ] A configured name present and empty yields the same condition
- [ ] A credential name yields the refusal, whatever its value
- [ ] `run_preamble` carries the forwarded name and value
- [ ] `write_env` carries the name and not the value
- [ ] The dry-run output carries the name and not the value
- [ ] An empty `env_passthrough` produces the argument list this package produces today, byte
      for byte

### Phase 6: documentation

- [ ] [`../docs/library.md`](../docs/library.md): the rule that nothing is read from the
      process environment is amended to the one exception, with the two rules above
- [ ] `CLAUDE.md`: the same amendment, in the one-config-file rule
- [ ] [`../docs/docker.md`](../docs/docker.md): the setting, the preflight, what is
      forwarded, the credential refusal, and phase 4's measurement
- [ ] [`../docs/cli.md`](../docs/cli.md): the preflight table gains the new conditions
- [ ] [`../docs/running_evals.md`](../docs/running_evals.md): `env.txt` gains its row
- [ ] `cowork_evals.example.yaml` carries the key, commented, with no value
- [ ] Nothing in `plans/done/` is read or corrected

### Phase 7: integration

- [ ] `plugins/smoke/` on the Docker backend with one variable forwarded, from the
      integration tier, green
- [ ] The same with the variable unset on the host, exit 3, naming the variable
- [ ] `scripts/test.sh` and `ruff` clean
