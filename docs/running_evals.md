# Running evals

The eval system behind the command: the mirror on `PATH`, the pinned harness flags, the
gate, the logs, the cadence and the cost. This file is the design. It is true whether or not
a given piece is built yet.

The command surface is [cli.md](cli.md) and the packaging boundary is
[library.md](library.md). A case is written once, in the format at
[eval_format.md](eval_format.md), and runs on any of the three backends. Which backend
honours which part of it is [approaches.md](approaches.md). The harness is
[plugin_eval.md](plugin_eval.md). Do not restate any of them here.

## Status

This table is the build status of the whole system. Nothing else carries one; they link
here.

| Piece                                     | Built | Designed in                                |
| ----------------------------------------- | ----- | ------------------------------------------- |
| The 3.10 mirror, as a development script  | yes   | [environments.md](environments.md)          |
| The `cowork_evals` package, as a distribution | yes | [library.md](library.md)                 |
| The `cowork_evals` executable and its verbs | no  | [cli.md](cli.md)                           |
| `cowork_evals.yaml` and the `Config` over it | yes | [library.md](library.md)                    |
| The pinned harness argument list          | yes   | this file                                   |
| The venv backend                          | no    | this file                                   |
| The staged runtime                        | no    | [staged_runtime.md](staged_runtime.md)      |
| The gate                                  | no    | this file                                   |
| The case validator                        | no    | [eval_format.md](eval_format.md)            |
| The 3.10 and import check over code under test | no | nowhere yet                                 |
| The container backend and its Dockerfile  | yes   | [docker.md](docker.md)                      |
| `scripts/parity.sh` and `tests/unit/test_parity.py` | yes | [docker.md](docker.md)                     |
| The CoWork driver                         | yes   | [cowork_driver.md](cowork_driver.md)        |
| The CoWork backend over it                | no    | [cowork_driver.md](cowork_driver.md)        |
| `plugins/smoke/`, the fixture both Claude Code backends fire | yes | [../plugins/README.md](../plugins/README.md) |

## The cases it runs

The case tree, the frontmatter and the graders are [eval_format.md](eval_format.md). What a
given path selects is [cli.md](cli.md). The backends discover cases exactly as the harness
does, so nothing here configures discovery.

There is no marketplace-wide suite. The harness loads one plugin per run, so a cross-plugin
case is not expressible. A path holding several plugins means every plugin's suite in turn,
each its own harness invocation, gated once.

There is no sweep on CoWork. One case there costs a VM boot plus a full agentic run and
counts against the driver's `max_runs` ceiling, so a sweep is a smoke set named case by
case. That is why [cli.md](cli.md) makes a multi-plugin path a usage error on `--cowork`.

The CoWork backend does not call `claude plugin eval`. It reads the same case tree, submits
each case's prompt body through the driver, grades the session document with the CoWork
grader, and writes the same `aggregate-result.json`. It pins one run per case. Of the
pinned flags below it uses only `eval.judge_model`, for judged graders. The rest configure
the CLI, and the CLI is not in the path. See [cowork_driver.md](cowork_driver.md).

### What counts as a case the backend cannot honour

A backend reads the keys the case file writes, never the merged defaults. `runs: 3` is the
default for every case, so treating a default as a request would skip every case on CoWork
and leave the gate permanently red.

| In the case file                                  | On CoWork          |
| -------------------------------------------------- | ------------------ |
| No `runs` key                                      | Runs once          |
| `runs: 1`                                          | Runs once          |
| `runs: 3`, written out                             | Skipped            |
| `max_turns` or `timeout_seconds`, written out      | Skipped            |
| `model`, `allowed_tools`, `append_system_prompt`, `env` | Skipped       |
| `context.*`, or a `mocks/` directory the case uses | Skipped            |

The rule is the same for every backend: an explicit key is honoured when the backend's fixed
behaviour already satisfies it, and skipped otherwise. Which key each backend can honour is
[approaches.md](approaches.md). A skip is written into the result document with its reason
and fails the gate, so a backend cannot go green by honouring nothing.

## The staged runtime on PATH

The venv backend stages a relocatable 3.10 interpreter carrying the CoWork wheels inside the
plugin directory under test, then puts its `bin` first on `PATH` before calling the harness.
A case that shells out to a bare `python3` gets 3.10 and the CoWork wheel set. What is
staged, how, and what has been measured about it is
[staged_runtime.md](staged_runtime.md).

The mirror itself is never staged. It is a virtual environment, so its interpreter and
standard library stay under the home directory, which the OS sandbox cannot read. That is
the whole reason the runtime is staged rather than put on `PATH` where it is built.

It refuses to run when the resulting `python3 -V` is not 3.10. One rule covers both hosts:
on a laptop a missing or stale mirror fails preflight instead of running against the host
interpreter, and in the container there is nothing to stage because the system interpreter
is already 3.10. See [docker.md](docker.md).

### Why the plugin directory is the only place it can go

Granting `Bash` in any form turns on Claude Code's OS-level Bash sandbox, whose readable set
is in [staged_runtime.md](staged_runtime.md). Every candidate below is decided by it.

`--allow-tools` is pinned to `Bash` because a skill that shells out needs it, so every run
is subject to this.

| Candidate location                          | Usable                                                             |
| ------------------------------------------- | ------------------------------------------------------------------ |
| The plugin directory under test             | Yes. Readable, and `PATH` directories inside it stay readable      |
| `~/.cache/cowork_evals/`, where it is built | No. Under the home directory                                       |
| A `context.add_dirs` entry                  | No. [eval_format.md](eval_format.md) refuses an entry outside the case directory, and the reference refuses one naming anything but a fixture directory |
| An operator `--allow-tools` read grant      | No. Grants a read path, not an exec path into the sandbox          |

Staging into the plugin directory writes a build product into the consumer checkout. It is
the one exception to the rule in [library.md](library.md), the backend removes it when the
run ends, and the consumer git-ignores it.


### A Bash-granting run is refused on a host that runs a credential process

Snapshot, 2026-09-03, CLI 2.1.260, macOS. A case granted `Bash` fails before the child
starts, so no case body runs and the run costs nothing:

```
a credentials file in this environment (the AWS config / shared credentials file, the GCP
application-default credentials, a kubeconfig, or an Anthropic profile config) could not be
followed (an AWS credential_process / credential_source cannot be excluded from the shell),
so the Bash sandbox cannot exclude the files it points at - a Bash-granting evaluation
cannot run here
```

The harness excludes credential files from the OS sandbox before it grants `Bash`. A
`credential_process` or `credential_source` entry names a command, not a file, so there is
nothing to exclude, and the harness refuses the run rather than leave that entry reachable
from the shell.

Three runs of one throwaway case separate the cause:

| Run                                            | Result                    |
| ---------------------------------------------- | ------------------------- |
| `--allow-tools Bash`, mirror first on `PATH`   | refused, no child started |
| `--allow-tools Bash`, host `PATH`              | refused, no child started |
| No `--allow-tools`, otherwise identical        | ran, 12 s, 0.06 USD       |

The `Bash` grant alone causes it. Neither the mirror nor `scripts/cowork_run.sh` is
involved.

Re-measured 2026-09-04, same CLI. Nothing lifts it on that host:

| Attempt                                                     | Result                              |
| ------------------------------------------------------------ | ------------------------------------- |
| `AWS_CONFIG_FILE` and `AWS_SHARED_CREDENTIALS_FILE` at empty files | still refused                   |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`                        | still refused                        |
| Every `CLAUDE_CODE_*` and `CLAUDECODE` variable unset       | still refused, so nesting inside a session is not the cause |
| `HOME` at an empty directory                                | refusal gone, run fails `Not logged in`. Plain `claude -p` fails the same way |

The last row is why the host cannot be worked around. The configuration the sandbox cannot
exclude is also the one that authenticates Claude Code there.

It binds the venv backend, which pins `--allow-tools Bash` and runs the harness on the
developer's host. It does not bind the container backend, which runs the harness inside the
image, where no such configuration exists. Nothing in this repository lifts it: the host's
AWS configuration belongs to the developer.

## Pinned flags

Every flag below is pinned because its default would otherwise bite. What each flag does,
and the harness behaviour behind it, is in [plugin_eval.md](plugin_eval.md). Which of them a
command-line option overrides, and on which backend, is [cli.md](cli.md).

| Flag                                       | Pinned to                        | Configuration key, and its default |
| ------------------------------------------ | -------------------------------- | ---------------------------------- |
| `--model`                                  | the configured model             | `eval.model`, `sonnet`             |
| `--judge-model`                            | the configured judge             | `eval.judge_model`, `haiku`        |
| `--ablation`                               | `none`                           | none                               |
| `--threshold`                              | `0`, so the local gate decides   | none                               |
| `--max-cost-usd`                           | the configured ceiling           | `eval.max_cost_usd`, 5             |
| `--output-dir`                             | the run's log directory          | none                               |
| `--allow-tools`                            | the configured grant             | `eval.allow_tools`, `[Bash]`       |
| `--no-publish`, `--no-scaffold`, `--verbose` | always                         | none                               |

The target goes before every variadic flag: `--tag` and `--allow-tools` swallow a trailing
target.

`--ablation` and `--threshold` have no command-line option and cannot be overridden.
`--threshold 0` is what hands pass and fail to the gate below.

### The baseline arm, and `arm:` on a grader

`--ablation with-without` runs every case twice. The with-arm loads the plugin under test.
The without-arm loads no plugin. The score delta between them is the evidence that the
plugin changed behaviour, rather than the model answering well on its own.

A `tool_used: Skill` grader cannot pass in the without-arm, because no plugin is loaded and
no skill can fire. The harness therefore drops such a grader from the score in both arms, so
the two arms are compared on the same graders. It still reports it, as an indicator carrying
`withOnly: true` and `scored: false`.

`arm:` on a grader is the case author's control over that.

| Value               | Scores in                                       |
| ------------------- | ----------------------------------------------- |
| `with-only`         | The with-arm only                               |
| `both`              | Every arm that runs                             |
| Absent, on a `tool_used: Skill` grader | The with-arm only. That is the harness default for this one grader shape |
| Absent, on anything else | Every arm that runs                        |

A case whose graders are all with-only is the exception. There is nothing left to compare,
so the harness scores them normally in both arms.

`--ablation none` runs one arm, and that arm is the with-arm. Nothing is dropped from the
score, so a `tool_used: Skill` grader is scored and the gate reads it. That is why it is
pinned. `arm:` then satisfies itself whichever value it carries, and a case sets it only to
stay portable to a suite that does run the baseline arm.

A baseline arm is an investigation, run by calling the harness by hand, and it is not a run
of this command. It doubles the agent runs, and the table in
[plugin_eval.md](plugin_eval.md) counts them.

`--allow-tools` is pinned because a case cannot grant itself `Bash`, `Write`, `Edit`,
`WebFetch` or an MCP tool. The operator grant is the only route, and an ungranted case loses
the tool rather than failing loudly. `Bash` is the default because a skill that shells out
needs it. Widen it through `eval.allow_tools` or `--allow-tools`, which replace the value
rather than adding to it, so the widened value has to name `Bash` again.

The two Claude Code backends export `CLAUDE_CODE_WALNUT_SPIRE`, the early-access enablement
variable, so no developer sets it by hand. It is a constant in `harness.py` and not a
configuration key. See [plugin_eval.md](plugin_eval.md).

`--json` is never passed, for the reason in [plugin_eval.md](plugin_eval.md).

## The gate

The gate decides pass and fail, not the harness. It reads the result document, so one gate
covers all three backends, and it always runs in the `cowork_evals` process on the host.

| Condition                                                             | Result       |
| --------------------------------------------------------------------- | ------------ |
| Any `regex`, `tool_used`, `tool_order` or `file_exists` grader failed | exit 1       |
| Any case or grader reported skipped                                   | exit 1       |
| `partial: true`: `partialReason` `cost_ceiling` or `auth_failed`      | exit 1       |
| A CoWork case that the driver could not run or collect                | exit 1       |
| A results document is missing or unparsable                           | exit 1       |
| Any `llm` or `baseline` grader failed                                 | printed only |
| Otherwise                                                             | exit 0       |

Structural graders gate because a judged grader over a non-deterministic agent is a flaky
gate. A skip gates so that a backend cannot go green by honouring nothing.

The gate reads every `<plugin>/aggregate-result.json` under the run directory and decides
once for the whole invocation, so a sweep gates once and not once per plugin.

It reads the `with` arm only. A run's grader results carry `name`, `passed` and `scored`,
never `type`, so the gate joins each result to that case's grader definition by name to
learn which of the two classes it is in.

The gate reads `schemaVersion: 1` documents and tolerates unknown fields. The contract is
additive-only.

## Logs

Every invocation keeps everything it printed, in one directory per invocation. Not one file
per plugin: runs are non-deterministic, and a per-plugin file overwrites the previous run.

```
logs/evals/<yyyymmdd-hhmmss>-<scope>/
  run.log                        # stdout and stderr of the whole invocation, tee'd live
  gate.txt                       # the gate's output
  env.txt                        # cowork_evals --version, claude --version, python3 -V
  <plugin>/aggregate-result.json # the v1 result document
  <plugin>/report.html           # the self-contained HTML report
  <plugin>/debug.txt             # claude --debug-file output
logs/evals/latest                # symlink to the newest directory
```

The log root is the working directory unless `--out` overrides it, and `<scope>` is named
from the path argument. Both are [cli.md](cli.md). Run directories older than 30 days are
deleted at the start of every run.

The debug log exists only when the run is given one:
`claude --debug-file <path> plugin eval ... --verbose`. The flag goes before `plugin`, and
it must be `--debug-file`: a bare `--debug` there swallows the subcommand name as its
filter. `--verbose` writes to that file only and never to the terminal.

## Cadence

An eval is not a commit-time check. `git commit` runs nothing, and there is no hook.

Which command runs at which moment is the table in
[approaches.md](approaches.md). Who enforces it is the consumer repository: the author while
writing a case, the PR template before a PR, the release checklist before a release.

That cadence is for a consumer repository. Nothing here runs against this repository's own
fixtures except the smoke case that proves the backend reaches a running case.

## Nothing here runs on CI

No hook, no PR job, no workflow shipped by this package. A person runs the sweep and reads
the summary. The reason is not cost: a red gate over cases nobody trusts gets routed around
rather than fixed.

A consumer automates it when all four of these hold, and not before:

| Condition                                                              | Read from         |
| ---------------------------------------------------------------------- | ----------------- |
| Every skill under test has at least one case                           | the `evals/` tree |
| Structural graders carry the gate, with a measured flake rate          | `logs/evals/*/`   |
| The cost and wall-clock time of a full sweep are measured and accepted | the table below   |
| A credential and a pinned CLI on a runner have an owner                | a decision        |

## Cost

[plugin_eval.md](plugin_eval.md) counts the model calls a suite makes. This file sets the
ceilings on what they may cost.

| Ceiling                      | Default | Binds                | Reached through        |
| ---------------------------- | ------- | -------------------- | ---------------------- |
| `eval.max_cost_usd`          | 5       | one plugin's suite   | `--max-cost-usd`       |
| `eval.max_cost_total_usd`    | 25      | the whole invocation | the key only, no flag  |

The total binds first: five plugins at 5 USD each is 25. A sweep sums `costUsd` from each
plugin's result document and checks the total before every plugin, the first included, so a
ceiling of 0 stops it before it spends anything. A sweep that stops on the ceiling is a
failure, never a pass.

The total has no command-line option because it governs an invocation rather than a run, and
[cli.md](cli.md) lists only the options a run takes.

| Measurement                    | Wall clock       | costUsd          |
| ------------------------------ | ---------------- | ---------------- |
| Smoke case, `runs: 1`, local   | not yet measured | not yet measured |
| Smoke case, `runs: 1`, Docker  | 3 s              | 0.057            |
| Full sweep, local              | not yet measured | not yet measured |

A row reading `not yet measured` has not been run. The ceilings above were chosen, not
measured.

The Docker row is a snapshot, 2026-09-08. It is `durationSeconds` and `costUsd` read from
the `aggregate-result.json` of the passing container run [docker.md](docker.md) records, on
CLI 2.1.265, `sonnet` and the `haiku` judge. The wall clock is the harness's own, so it
excludes the image build and the container start.
