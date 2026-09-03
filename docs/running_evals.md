# Running evals

The eval system: the case layout, the run scopes, the pinned flags, the gate, the logs and
the cadence. This page is the design. It is true whether or not a given piece is built yet.

The harness itself is [plugin_eval.md](plugin_eval.md). Do not restate it here.

## Status

| Piece                                     | Built |
| ----------------------------------------- | ----- |
| `.venv_cowork` mirror and `cowork_run.sh` | yes   |
| `scripts/eval.sh`, `eval_all.sh`          | no    |
| `scripts/eval_gate.py`                    | no    |
| `scripts/validate_cases.py`               | no    |
| The container runner                      | no    |
| The CoWork driver                         | no    |

## Case layout

One eval directory per skill.

```
plugins/<plugin>/evals/<skill>/<case>/prompt.md
plugins/<plugin>/evals/<skill>/<case>/graders/<name>.md
plugins/<plugin>/evals/<skill>/<case>/case.yaml      # optional, context.* only
plugins/<plugin>/evals/plugin/<case>/                # cross-skill composition
plugins/<plugin>/evals/mocks/<server>/<tool>.md      # shared MCP stand-ins
```

Discovery is recursive, so a grouping directory that is not itself a case is searched
through. `evals/` is the harness default, so nothing is configured.

A directory directly under `evals/` is a skill name, `plugin`, or `mocks`. Nothing else.
`scripts/validate_cases.py` enforces that in both directions.

Two frontmatter keys make a case addressable, and both are checked:

- `tags: [<skill>]`, matching the case's own directory. `--tag` is the only reliable
  per-skill selector.
- `plugins: ["../../.."]`, the plugin root from a case three levels down.

Fixtures live inside the case that uses them. `context.add_dirs` refuses any entry outside
the case directory.

There is no marketplace-wide suite. The harness loads one plugin per run, so a cross-plugin
case is not expressible. Marketplace scope means every plugin's suite in turn.

## The three scopes

| Scope  | Command                   | Runs                                                 |
| ------ | ------------------------- | ---------------------------------------------------- |
| Skill  | `scripts/eval.sh <p>/<s>` | that skill's cases, `--runs 1`                       |
| Plugin | `scripts/eval.sh <p>`     | every case under that plugin, each case's own `runs` |
| All    | `scripts/eval_all.sh`     | every plugin that has an `evals/` tree               |

Skill scope pins `--runs 1` because it is the iteration loop. The other two use the case's
own `runs`.

The container equivalents are `scripts/eval_docker.sh` and `scripts/eval_docker_all.sh`.
They take the same arguments and produce the same logs. See [docker.md](docker.md).

## Pinned flags

Every flag below is pinned because its default would otherwise bite. What each flag does,
and the harness behaviour behind it, is in [plugin_eval.md](plugin_eval.md).

| Flag                                       | Pinned to                        |
| ------------------------------------------ | -------------------------------- |
| `--model`                                  | `${EVAL_MODEL:-sonnet}`          |
| `--judge-model`                            | `${EVAL_JUDGE_MODEL:-haiku}`     |
| `--ablation`                               | `none`                           |
| `--threshold`                              | `0`, so the local gate decides   |
| `--max-cost-usd`                           | `${EVAL_MAX_COST_USD:-5}`        |
| `--output-dir`                             | the run's log directory          |
| `--no-publish`, `--no-scaffold`, `--verbose` | always                         |

The target goes before every variadic flag: `--tag` and `--allow-tools` swallow a trailing
target.

Every runner exports `CLAUDE_CODE_WALNUT_SPIRE`, the early-access enablement variable, so no
developer sets it by hand. See [plugin_eval.md](plugin_eval.md).

`--json` is never passed. It silences progress, per-case grader lines, notices and the
summary table, and an errored run's sandbox is not kept. `--output-dir` gives the same
document with none of that loss.

## The gate

`scripts/eval_gate.py` decides pass and fail, not the CLI.

| Condition                                                             | Result       |
| --------------------------------------------------------------------- | ------------ |
| Any `regex`, `tool_used`, `tool_order` or `file_exists` grader failed | exit 1       |
| `partial: true`: cost ceiling, auth failure, or interrupted           | exit 1       |
| A results document is missing or unparsable                           | exit 1       |
| Any `llm` or `baseline` grader failed                                 | printed only |
| Otherwise                                                             | exit 0       |

Structural graders gate. Judged graders report. A judged suite at `runs: 3` over a
non-deterministic agent is a flaky gate, and a flaky gate gets ignored.

The gate reads `schemaVersion: 1` documents and tolerates unknown fields. The contract is
additive-only.

## Logs

Evals are slow and cost money, so every invocation keeps everything it printed. One
directory per invocation, not one file per plugin: runs are non-deterministic, so the thing
you need while debugging is the previous run, and a per-plugin file overwrites exactly that.

```
logs/evals/<yyyymmdd-hhmmss>-<scope>/
  run.log                        # stdout and stderr of the whole invocation, tee'd live
  gate.txt                       # the gate's output
  env.txt                        # claude --version, python3 -V, git rev-parse HEAD
  <plugin>/aggregate-result.json # the v1 result document
  <plugin>/report.html           # the self-contained HTML report
  <plugin>/debug.txt             # claude --debug-file output
logs/evals/latest                # symlink to the newest directory
```

`<scope>` is `all`, `<plugin>`, or `<plugin>-<skill>`. `logs/` is git-ignored whole. Run
directories older than 30 days are deleted by the runner.

The debug log exists only when the run is given one:
`claude --debug-file <path> plugin eval ... --verbose`. The flag goes before `plugin`, and
it must be `--debug-file`: a bare `--debug` there swallows the subcommand name as its
filter. `--verbose` writes to that file only and never to the terminal.

## Cadence

Evals cost money and take minutes. They are not a commit-time check.

| Moment              | What runs                                     | Enforced by           |
| ------------------- | --------------------------------------------- | --------------------- |
| `git commit`        | nothing                                       | no hook, by design    |
| Writing a case      | `scripts/eval.sh <p>/<s>`                     | the author            |
| Before opening a PR | `scripts/eval.sh <p>` for each touched plugin | the PR template       |
| Before a release    | `scripts/eval_docker_all.sh`, then a CoWork smoke set | the release checklist |

## Nothing here runs on CI

No hook, no PR job, no workflow. A person runs the sweep and reads the summary.

The reason is not cost. A gate is only worth automating over a suite the team trusts, and a
red gate over cases nobody trusts gets routed around rather than fixed. Case quality first,
automation second.

Automate it when all four of these hold, and not before:

| Condition                                                              | Read from         |
| ---------------------------------------------------------------------- | ----------------- |
| Every skill under test has at least one case                           | the `evals/` tree |
| Structural graders carry the gate, with a measured flake rate          | `logs/evals/*/`   |
| The cost and wall-clock time of a full sweep are measured and accepted | the table below   |
| A credential and a pinned CLI on a runner have an owner                | a decision        |

## Cost

Agent runs are `cases x runs x arms`. Each `llm` or `baseline` grader adds three judge
calls. Structural graders are free.

Ceilings: `EVAL_MAX_COST_USD` 5 per plugin, `EVAL_MAX_COST_TOTAL_USD` 25 per sweep. The
total binds first: five plugins at 5 USD each is 25. A sweep that stops on the ceiling is a
failure, never a pass.

| Measurement                    | Wall clock       | costUsd          |
| ------------------------------ | ---------------- | ---------------- |
| Smoke case, `runs: 1`, local   | not yet measured | not yet measured |
| Smoke case, `runs: 1`, Docker  | not yet measured | not yet measured |
| Full sweep, local              | not yet measured | not yet measured |

A row reading `not yet measured` has not been run. The ceilings above are arithmetic, not
measurements.
