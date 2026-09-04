# Running evals

The eval system behind the command: the mirror on `PATH`, the pinned harness flags, the
gate, the logs, the cadence and the cost. This page is the design. It is true whether or not
a given piece is built yet.

The command surface is [cli.md](cli.md) and the packaging boundary is
[library.md](library.md). A case is written once, in the format at
[eval_format.md](eval_format.md), and runs on any of the three backends. Which backend
honours which part of it is [approaches.md](approaches.md). The harness is
[plugin_eval.md](plugin_eval.md). Do not restate any of them here.

## Status

| Piece                                    | Built |
| ---------------------------------------- | ----- |
| The 3.10 mirror, as a development script | yes   |
| The `cowork_evals` package and CLI       | no    |
| The venv backend                         | no    |
| The gate                                 | no    |
| The case validator                       | no    |
| The container backend                    | no    |
| The CoWork driver and its backend        | no    |

## The cases it runs

The case tree, the frontmatter and the graders are [eval_format.md](eval_format.md). What a
given path selects is [cli.md](cli.md). The backends discover cases exactly as the harness
does, so nothing here configures discovery.

There is no marketplace-wide suite. The harness loads one plugin per run, so a cross-plugin
case is not expressible. A path holding several plugins means every plugin's suite in turn,
each its own harness invocation, gated once.

There is no sweep on CoWork. One case there costs a VM boot plus a full agentic run and
counts against `COWORK_MAX_RUNS`, so a sweep is a smoke set named case by case. Pointing
`--cowork` at a path holding several plugins is a usage error.

The CoWork backend does not call `claude plugin eval`. It reads the same case tree, submits
each case's prompt body through the driver, grades the driver's result document with the
CoWork grader, and writes the same `aggregate-result.json`. It pins one run per case, and
reports a case it cannot honour as skipped. Of the pinned flags below it uses only
`EVAL_JUDGE_MODEL`, for judged graders. The rest configure the CLI, and the CLI is not in
the path. See [cowork_driver.md](cowork_driver.md).

## The mirror on PATH

The venv backend puts the cached 3.10 mirror's `bin` first on `PATH` before calling the
harness, so a case that shells out to a bare `python3` gets 3.10 and the CoWork wheel set.
Where the mirror lives is [library.md](library.md), and
[environments.md](environments.md) says why prepending it reaches child processes.

It refuses to run when the resulting `python3 -V` is not 3.10. One rule covers both hosts:
on a laptop a missing or stale mirror fails preflight instead of running against the host
interpreter, and in the container there is no mirror to prepend because the system
interpreter is already 3.10. See [docker.md](docker.md).

Two conditions have to hold. Neither is verified against the harness yet.

| Condition                                      | Not met when                                       |
| ---------------------------------------------- | -------------------------------------------------- |
| The per-run sandbox inherits `PATH`            | It replaces the environment as it replaces `HOME`  |
| The mirror is readable from inside the sandbox | Granting `Bash` hides the rest of the home directory |

The OS sandbox that `Bash` turns on leaves readable the sandbox itself, the plugin
directory, the case's `context.add_dirs` entries, and the `PATH` directories inside those.
Everything else under the home directory is hidden. The mirror sits under
`~/.cache/cowork_evals` and not inside a plugin, and `add_dirs` refuses any entry outside
the case directory, so no case can expose it. Its `python3` is a symlink into the uv
interpreter store, which is under the home directory and is not itself on `PATH`, so the
base interpreter has to be reachable as well as the venv.

Until both conditions are measured, this approach is unproven and only the container
reproduces the interpreter. See [docker.md](docker.md).

## Pinned flags

Every flag below is pinned because its default would otherwise bite. What each flag does,
and the harness behaviour behind it, is in [plugin_eval.md](plugin_eval.md). Which of them a
command-line option overrides, and on which backend, is [cli.md](cli.md).

| Flag                                       | Pinned to                        |
| ------------------------------------------ | -------------------------------- |
| `--model`                                  | `${EVAL_MODEL:-sonnet}`          |
| `--judge-model`                            | `${EVAL_JUDGE_MODEL:-haiku}`     |
| `--ablation`                               | `none`                           |
| `--threshold`                              | `0`, so the local gate decides   |
| `--max-cost-usd`                           | `${EVAL_MAX_COST_USD:-5}`        |
| `--output-dir`                             | the run's log directory          |
| `--allow-tools`                            | `${EVAL_ALLOW_TOOLS:-Bash}`      |
| `--no-publish`, `--no-scaffold`, `--verbose` | always                         |

The target goes before every variadic flag: `--tag` and `--allow-tools` swallow a trailing
target.

`--allow-tools` is pinned because a case cannot grant itself `Bash`, `Write`, `Edit`,
`WebFetch` or an MCP tool. The operator grant is the only route, and an ungranted case loses
the tool rather than failing loudly. `Bash` is the default because a skill that shells out
needs it. Widen it through `EVAL_ALLOW_TOOLS` or `--allow-tools`, which replace the value
rather than adding to it, so the widened value has to name `Bash` again.

The two Claude Code backends export `CLAUDE_CODE_WALNUT_SPIRE`, the early-access enablement
variable, so no developer sets it by hand. See [plugin_eval.md](plugin_eval.md).

`--json` is never passed, for the reason in [plugin_eval.md](plugin_eval.md).

## The gate

The gate decides pass and fail, not the harness. It reads the result document, so one gate
covers all three backends, and it always runs in the `cowork_evals` process on the host.

| Condition                                                             | Result       |
| --------------------------------------------------------------------- | ------------ |
| Any `regex`, `tool_used`, `tool_order` or `file_exists` grader failed | exit 1       |
| Any case or grader reported skipped                                   | exit 1       |
| `partial: true`: cost ceiling, auth failure, or interrupted           | exit 1       |
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

An eval is not a commit-time check.

| Moment              | What runs                                            | Enforced by           |
| ------------------- | ---------------------------------------------------- | --------------------- |
| `git commit`        | nothing                                              | no hook, by design    |
| Writing a case      | `cowork_evals run --venv <case>`                     | the author            |
| Before opening a PR | `cowork_evals run --venv <plugin>/evals` per plugin  | the PR template       |
| Before a release    | `cowork_evals run --docker <root>`, then a CoWork smoke set | the release checklist |

This is the cadence for a consumer repository. Nothing here runs against this repository's
own fixtures except the smoke case that proves the backend reaches a running case.

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

[plugin_eval.md](plugin_eval.md) counts the model calls a suite makes. This page sets the
ceilings on what they may cost.

Ceilings: `EVAL_MAX_COST_USD` 5 per plugin, `EVAL_MAX_COST_TOTAL_USD` 25 per sweep. The
total binds first: five plugins at 5 USD each is 25. A sweep sums `costUsd` from each
plugin's result document and checks the total before every plugin, the first included, so a
ceiling of 0 stops it before it spends anything. A sweep that stops on the ceiling is a
failure, never a pass.

| Measurement                    | Wall clock       | costUsd          |
| ------------------------------ | ---------------- | ---------------- |
| Smoke case, `runs: 1`, local   | not yet measured | not yet measured |
| Smoke case, `runs: 1`, Docker  | not yet measured | not yet measured |
| Full sweep, local              | not yet measured | not yet measured |

A row reading `not yet measured` has not been run. The ceilings above were chosen, not
measured.
