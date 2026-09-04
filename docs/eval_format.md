# Eval case format

What a case is made of: the tree, the file names, the frontmatter, the graders and the
authoring traps. This is the authoring contract for every eval in this repository, on every
backend.

The format is `claude plugin eval`'s own, so a case needs no adapter to run under that
harness. What the CLI does with a case is [plugin_eval.md](plugin_eval.md). How this
repository invokes it is [running_evals.md](running_evals.md). Which backend honours which
field is [approaches.md](approaches.md).

## The tree

One eval directory per skill, inside the plugin, in the repository that owns the plugin.

```
<plugin>/.claude-plugin/plugin.json               # what makes <plugin> a plugin root
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md
<plugin>/evals/<skill>/<case>/case.yaml           # optional, context.* only
<plugin>/evals/plugin/<case>/                     # cross-skill composition
<plugin>/evals/mocks/<server>/<tool>.md           # shared MCP stand-ins
```

`<plugin>` is any directory holding `.claude-plugin/plugin.json`. Where it sits in the
consumer repository is that repository's choice, and nothing here assumes a `plugins/`
parent. See [library.md](library.md).

Discovery is recursive, so a grouping directory that is not itself a case is searched
through rather than run. `evals/` is the harness default, so nothing is configured.

A directory directly under `evals/` is a skill name, `plugin`, or `mocks`. Nothing else.
The case validator enforces that in both directions.

Fixtures live inside the case that uses them. `context.add_dirs` refuses any entry outside
the case directory.

## Addressability

Two frontmatter keys make a case addressable, and both are checked:

- `tags: [<skill>]`, matching the case's own directory. `--tag` is the only reliable
  per-skill selector; `--case` globs the case directory name.
- `plugins: ["../../.."]`, the plugin root, counted from the case directory. That is three
  levels up from a case under `evals/<skill>/<case>/`.

## prompt.md

Frontmatter, then the prompt body.

Keys: `name`, `tags`, `plugins`, `runs`, `max_turns`, `timeout_seconds`, `allowed_tools`,
`model`, `append_system_prompt`, `env`. Defaults are `runs: 3`, `max_turns: 10`,
`timeout_seconds: 300`. Case `env` keys must start with `EVAL_`.

## case.yaml

Optional. It carries only what `prompt.md` cannot: `context.scaffold_script`,
`context.history_file`, `context.add_dirs`. It needs `schema_version: "1.1"` and `name`.

## Graders

One grader per file under `graders/`, frontmatter then the rubric or pattern.

| Type          | Asserts                                                          | Class      |
| ------------- | ---------------------------------------------------------------- | ---------- |
| `regex`       | `pattern`, `flags`, `match: contains \| not_contains \| count:N` | structural |
| `tool_used`   | `tool`, `input_match`, `min` (default 1), `max`                  | structural |
| `tool_order`  | `before`, `after`                                                | structural |
| `file_exists` | `path`, a glob over files the agent created                      | structural |
| `llm`         | `criteria`, `focus`. A judge model votes 2 of 3                  | judged     |
| `baseline`    | `baseline_file`, `criteria`                                      | judged     |

The class column is what the gate reads. See [running_evals.md](running_evals.md).

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

## Authoring traps

Each of these has a silent failure mode, and each is fixed by editing the case.

- **A grader file needs `---` frontmatter delimiters.** Without them it is a note and is
  ignored, so the case runs with fewer graders than it appears to have.
- **`min: 0, max: 0` is how a must-not-call assertion is written.** `max: 0` alone can never
  pass, because `min` stays 1.
- **`file_exists` only sees files created during the run.** Not scaffold output, and not
  files merely modified.
- **`llm` graders refuse binaries.** A `.pptx` is a ZIP. Render to an image, or write text.
  An image file is shown to the judge as an image.
- **Scaffolds run in an empty working directory** with a minimal environment, no
  credentials, and a 2-minute cap. Reference resources as `$(dirname "$0")/...`.
- **`context.add_dirs` must stay inside the case directory.** Naming the eval directory, a
  sibling case, the plugin root or the case's own `graders/` refuses the run.

The traps that a case cannot fix, because they are the harness rather than the file, are in
[plugin_eval.md](plugin_eval.md).
