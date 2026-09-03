# claude plugin eval

Claude Code's own eval harness. It loads one plugin into a fresh isolated `claude -p`
session, runs each case several times, and scores the result with graders.

Written against CLI 2.1.259. The command is in early access and has no public documentation
page, so `claude plugin eval --help` in your own build is the authority when this page and
the CLI disagree.

This page is a summary. Anthropic's own full reference is vendored at
[`claude_code/`](claude_code/), together with `eval_smoke/`, a runnable plugin that proves
the harness works.

## Availability

Enabled per organization. When it is not enabled, the command prints that it is in early
access and exits 1. The command exists either way; a gated build is not a missing feature.

Enablement is the `tengu_walnut_spire` per-organization rollout flag. Enabled first-party
clients pick it up after `claude update` and a fresh session.

**Clients that cannot fetch server-side flags must set `CLAUDE_CODE_WALNUT_SPIRE=1`.** That
covers Bedrock, Vertex, Foundry, any client with a custom `ANTHROPIC_BASE_URL`, and any
client with `DISABLE_TELEMETRY`, `DO_NOT_TRACK`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
or `DISABLE_GROWTHBOOK` set. It needs CLI 2.1.207 or later.

Every runner script in this repository exports it, so no developer sets anything by hand:

```sh
export CLAUDE_CODE_WALNUT_SPIRE="${CLAUDE_CODE_WALNUT_SPIRE:-1}"
```

It cannot be committed to a repository's `.claude/settings.json` `env`: only allowlisted
variables apply from project settings, this one is not allowlisted, and `claude plugin ...`
run from a shell or CI does not pass trust anyway. Set it in the shell, in CI, in
`~/.claude/settings.json` under `env`, or in managed settings.

Self-test from an empty directory:

| Output                | Means            |
| --------------------- | ---------------- |
| `early access`        | Not enabled here |
| `No eval cases found` | Enabled          |

## Case layout

Cases live under the plugin's eval directory, `evals/` by default.

```
<plugin>/evals/<case>/prompt.md          # frontmatter + the prompt body
<plugin>/evals/<case>/graders/<name>.md  # frontmatter + the rubric or pattern
<plugin>/evals/<case>/case.yaml          # optional, context.* only
<plugin>/evals/mocks/<server>/<tool>.md  # MCP stand-ins
<plugin>/evals/results/                  # written by the CLI
```

Discovery is recursive, so a grouping directory that is not itself a case is searched
through rather than run. That is how one directory per skill works.

`prompt.md` frontmatter: `name`, `tags`, `plugins`, `runs`, `max_turns`, `timeout_seconds`,
`allowed_tools`, `model`, `append_system_prompt`, `env`. Defaults are `runs: 3`,
`max_turns: 10`, `timeout_seconds: 300`. Case `env` keys must start with `EVAL_`.

`case.yaml` carries only what `prompt.md` cannot: `context.scaffold_script`,
`context.history_file`, `context.add_dirs`. It needs `schema_version: "1.1"` and `name`.

Two frontmatter keys make a case addressable:

- `tags: [<skill>]` matching its directory. `--tag` is the only reliable per-skill selector;
  `--case` globs the case directory name.
- `plugins: ["../../.."]`, the plugin root, counted from the case directory.

## Graders

| Type          | Asserts                                                          |
| ------------- | ---------------------------------------------------------------- |
| `regex`       | `pattern`, `flags`, `match: contains \| not_contains \| count:N` |
| `tool_used`   | `tool`, `input_match`, `min` (default 1), `max`                  |
| `tool_order`  | `before`, `after`                                                |
| `file_exists` | `path`, a glob over files the agent created                      |
| `llm`         | `criteria`, `focus`. A judge model votes 2 of 3                  |
| `baseline`    | `baseline_file`, `criteria`                                      |

Grader targets: `last_message` (default), `trace`, `files` (created paths, not contents),
`{source: file, path}` (a produced file's contents), `mock_calls`.

Prefer a deterministic grader over a judged one for anything long. Judges are noisy on long
inputs.

The skill-fired idiom:

```yaml
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?<skill>"'
```

## Running

```
claude plugin eval [target] [--case glob] [--tag t...] [--runs n] [--model m]
                   [--judge-model m] [--max-cost-usd usd] [--eval-dir dir]
                   [--output-dir dir] [--json [file]] [--threshold 0..1]
                   [--allow-tools t...] [--scaffold|--no-scaffold]
                   [--ablation none|with-without] [--mocks record|off]
                   [--keep-temp] [--verbose] [--report path] [--no-publish]
```

The target is a path, an installed plugin name, or `name@marketplace`. Put it before
`--tag`, `--allow-tools` and `--json`: those are variadic and will swallow a trailing
target.

Exit codes: 0 every case at or above the threshold (default 1.0); 1 below threshold, load
error, no cases, bad options; 2 partial, meaning the cost ceiling was hit or the credential
was rejected; 130 interrupted; 143 terminated.

## Flags worth pinning

| Flag              | Why                                                                                                                                                  |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--model`         | `ANTHROPIC_MODEL` is not inherited by the agent under test. Unpinned, a model rollout reads as a regression                                          |
| `--judge-model`   | Same, for the graders                                                                                                                                |
| `--ablation none` | The default runs a no-plugin baseline arm whenever the plugin resolves, doubling cost and demoting `tool_used: Skill` graders to unscored indicators |
| `--threshold 0`   | Let a local gate decide pass and fail, so structural and judged graders can be separated                                                             |
| `--max-cost-usd`  | Spend backstop. Hitting it exits 2 with partial results                                                                                              |
| `--output-dir`    | Puts `aggregate-result.json` and `report.html` in a log directory rather than under the plugin                                                       |
| `--no-publish`    | The HTML report is otherwise published to claude.ai                                                                                                  |
| `--no-scaffold`   | `context.scaffold_script` runs author-supplied shell as the invoking user                                                                            |

Do not pass `--json`. It silences progress lines, per-case grader lines, notices and the
summary table, and an errored run's sandbox is not kept. `--output-dir` gives the same
document with none of that loss.

## Limits a case author has to know

Each of these has a silent failure mode.

- **Only the plugin under test loads.** No user or project settings, no `CLAUDE.md`, no
  other plugins, no personal MCP servers.
- **Tools are gated.** Effective tools are the case's `allowed_tools` intersected with the
  read-only set, unioned with the operator's `--allow-tools`. `Bash`, `Write`, `Edit`,
  `WebFetch`, `WebSearch` and `mcp__*` need an explicit grant. A plugin's own MCP tools are
  named `mcp__plugin_<plugin>_<server>__<tool>`.
- **A grader file needs `---` frontmatter delimiters.** Without them it is a note and is
  ignored, so the case runs with fewer graders than it appears to have.
- **`min: 0, max: 0` is how a must-not-call assertion is written.** `max: 0` alone can never
  pass, because `min` stays 1.
- **Granting `Bash` turns on the OS sandbox.** On a machine with no sandbox backend the run
  is refused rather than run unconfined.
- **`file_exists` only sees files created during the run.** Not scaffold output, and not
  files merely modified.
- **The Artifact tool is unavailable in a run.** A skill that ends by publishing cannot be
  exercised past that point.
- **`llm` graders refuse binaries.** A `.pptx` is a ZIP. Render to an image, or write text.
  An image file is shown to the judge as an image.
- **Scaffolds run in an empty working directory** with a minimal environment, no
  credentials, and a 2-minute cap. Reference resources as `$(dirname "$0")/...`.
- **`context.add_dirs` must stay inside the case directory.** Naming the eval directory, a
  sibling case, the plugin root or the case's own `graders/` refuses the run.
- **Enterprise managed policy still applies inside a run.** Results on a managed machine
  differ from an unmanaged one by exactly that policy.
- **The network is not blocked.** The per-run sandbox is a fresh workspace, `HOME` and
  `CLAUDE_CONFIG_DIR`, not an OS-level network jail.

## Proving the harness works

`docs/claude_code/eval_smoke/run.sh` is a throwaway plugin with two skills, three cases and
four grader types. It calls `claude plugin eval` directly, with no wrapper from this
repository, so it separates a harness problem from a runner problem.

## Cost

Agent runs are `cases x runs x arms`. Each `llm` or `baseline` grader adds three judge
calls. Structural graders are free.

A 10-case suite at `runs: 3` with the baseline arm on is 60 agent runs before a single judge
call. That is why `--ablation none` is the default in this repository and `with-without` is
a manual investigation tool.
