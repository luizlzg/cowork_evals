# Eval case format

## Summary

What a case is made of: the tree, the file names, the frontmatter, the graders and the
authoring traps. This is the authoring contract for every eval in this repository, on both
backends.

- **A case is a directory**: a `prompt.md` with frontmatter and a prompt body, a `graders/`
  directory, and an optional `case.yaml`.
- **Two addressability keys are required**, `tags` and `plugins`, and both are checked.
- **Graders come in two classes.** Structural graders are deterministic and carry the verdict;
  judged graders call a model and are printed. Prefer a structural one.
- **Only two grader types choose what they look at, and they use different keys.** `regex`
  uses `target`, `llm` uses `focus`.
- **Writing out a key a backend cannot honour skips the case there.** Leaving it out does not.
- **Every trap in the last section has a silent failure mode.** Read it before writing a case.

The format is `claude plugin eval`'s own, so a case needs no adapter to run under that
harness. What the CLI does with a case is [plugin_eval.md](plugin_eval.md). How this
repository invokes it is [running_evals.md](running_evals.md). Which backend honours which
field is [approaches.md](approaches.md). The full field-by-field reference is vendored at
[claude_code/plugin_eval_reference.md](claude_code/plugin_eval_reference.md), and it is the
authority where this file is silent.

Two rules here are this repository's own and not the harness's: the `<skill>` layer under
`evals/`, and the two addressability keys below. Everything else is the harness.
`docs/claude_code/eval_smoke/` is deliberately outside all of it; see
[claude_code/eval_smoke/README.md](claude_code/eval_smoke/README.md).

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
The case validator enforces that in both directions. That layer is this repository's
convention: the harness puts a case directly under `evals/` and recurses through anything
that is not a case, so the layer costs nothing and one directory per skill is what makes
`--tag` selection match the tree.

Fixtures live inside the case that uses them. `context.add_dirs` refuses any entry outside
the case directory.

## Addressability

Two frontmatter keys make a case addressable, and both are checked:

- `tags: [<skill>]`, matching the case's own directory. `--tag` is the only reliable
  per-skill selector; `--case` globs the case **name**, which defaults to the directory name
  and differs from it whenever the case writes a `name`.
- `plugins: ["../../.."]`, the plugin root, counted from the case directory. That is three
  levels up from a case under `evals/<skill>/<case>/`.

## prompt.md

Frontmatter, then the prompt body.

| Key                                                        | Is                                                      |
| ------------------------------------------------------------ | ------------------------------------------------------- |
| `name`                                                     | Required                                                |
| `description`                                              | For humans. Not read at run time and not in the results |
| `tags`, `plugins`                                          | Addressability, above. Both required here               |
| `runs`, `max_turns`, `timeout_seconds`                     | Defaults 3, 10, 300. Caps 50, 200, 3600                 |
| `model`, `allowed_tools`, `append_system_prompt`, `env`    | Execution. `env` keys must start with `EVAL_`           |
| `schema_version`, `expected_outcome`                       | Accepted by the harness. Not used here                  |

Any other key is an error. `context.*` cannot be set from `prompt.md`.

Writing out a key a backend cannot honour skips the case on that backend. Leaving it out
does not, because a default is not a request. See [running_evals.md](running_evals.md).

### What an unknown key does, in each of the two files

Snapshot, 2026-09-12, CLI 2.1.265, through the container backend. One fixture case carried
`backends: [docker]`, first in `prompt.md` and then in `case.yaml`.

| Where the key was       | The harness                                                          |
| ----------------------- | ---------------------------------------------------------------------- |
| `prompt.md` frontmatter | Refused the case at load, named the allowed set, ran nothing and wrote no `aggregate-result.json`. The command exited 1 |
| `case.yaml`             | Loaded the case and ran it                                            |

The refusal is at case load and before the credential is read, so it costs no model call, and
a whole suite produces no result document for one malformed case. A fact this repository has
to read off a case therefore cannot ride in `prompt.md` frontmatter.

The allowed set the harness named carries two keys the table above does not:
`artifact_publish` and `growthbook_overrides`. The case validator's key set is that table, so
a case writing either is refused by the preflight although the harness accepts it.

## case.yaml

Optional. It carries only what `prompt.md` cannot: `context.scaffold_script`,
`context.history_file`, `context.add_dirs`. It needs `schema_version: "1.1"` and `name`.
An unknown top-level key there is ignored, as the snapshot above records, and this repository
writes none.

## Graders

One grader per file under `graders/`, frontmatter then the rubric or pattern.

| Type          | Asserts                                                          | Class      |
| ------------- | ---------------------------------------------------------------- | ---------- |
| `regex`       | `pattern`, `flags`, `match: contains \| not_contains \| count:N`, `target` | structural |
| `tool_used`   | `tool`, `input_match`, `min` (default 1), `max` (default unlimited) | structural |
| `tool_order`  | `before`, `after`                                                | structural |
| `file_exists` | `path`, a glob over files the agent created, `exists` (default true) | structural |
| `llm`         | `criteria`, `focus`. A judge model votes 2 of 3                  | judged     |
| `baseline`    | `baseline_file`, `criteria`                                      | judged     |

The class column is what the verdict reads. See [running_evals.md](running_evals.md).

Every grader also takes `name`, which defaults to the filename without `.md`, and `weight`,
which is greater than 0 and defaults to 1. The verdict reads pass and fail, not the score, so
`weight` changes the harness summary and changes nothing here. There is no `weight: 0`:
delete the grader, or use `arm`.

**Only two graders choose what they look at, and they use different keys.** `regex` uses
`target`, `llm` uses `focus`. `tool_used` and `tool_order` always read the trace,
`file_exists` always reads the created file list, and `baseline` always compares against
`baseline_file`. Setting `target` on an `llm` grader is silently ignored and it judges
`last_message`.

Values for `target` and `focus`: `last_message` (default), `trace`, `files` (created paths,
not contents), `{source: file, path}` (a produced file's contents), `mock_calls`.

### A regex anchor is string-anchored

A `regex` grader's `pattern` is JavaScript RegExp source, and `flags` carries the flags. `^`
and `$` therefore match the start and the end of the whole target, not of a line, unless
`flags` carries `m`. This differs from Python, where `$` also matches before a trailing
newline, and it is what a grader asserting that an answer is exactly one thing rests on.

Snapshot, 2026-09-09, Node 25.9.0, over the pattern `^\s*(?:blocker|major|minor)\s*$`:

| Target                      | no flags | `m`   |
| --------------------------- | -------- | ----- |
| `blocker`                   | pass     | pass  |
| `blocker\n`                 | pass     | pass  |
| `  minor  `                 | pass     | pass  |
| `minor.`                    | fail     | fail  |
| `The severity is blocker`   | fail     | fail  |
| `blocker\nmajor`            | fail     | pass  |
| `line one\nblocker`         | fail     | pass  |

A trailing newline passes because `\s*` consumes it, not because `$` matches before it. A
pattern with no `\s*` and a target ending in a newline fails.

`arm` selects which ablation arm scores a grader: `with-only`, or `both`. It matters only
under `--ablation with-without`, which this repository never runs, so a case here sets it
only to stay portable. See [running_evals.md](running_evals.md).

Prefer a deterministic grader over a judged one for anything long. Judges are noisy on long
inputs.

The skill-fired idiom:

```yaml
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?<skill>"'
```

## What the validator enforces

`cowork_evals run` validates every selected plugin root before it runs anything, and a
violation exits 3. It validates the whole root and not only the target, so a malformed
sibling case blocks a single-case run. There is no option to skip it. See
[cli.md](cli.md).

| Rule                                                                        |
| ------------------------------------------------------------------------------ |
| A directory directly under `evals/` is `plugin`, `mocks`, or a directory under `<plugin>/skills/` |
| `name`, `tags` and `plugins` are present in `prompt.md`                     |
| `tags` names the case's own `<skill>` directory                             |
| `plugins` resolves, from the case directory, to the plugin root             |
| Every `prompt.md` frontmatter key is in the table above, `context.*` included |
| `runs` is at most 50, `max_turns` at most 200, `timeout_seconds` at most 3600 |
| Every `env` key starts with `EVAL_`                                         |
| `case.yaml` carries `schema_version: "1.1"` and `name`, and no key outside the three above |
| Every `context.add_dirs` entry resolves inside its own case directory       |
| Every grader has a `type` the table above lists, and a `weight` above 0     |
| Every file under `graders/` carries a `---` block                           |

A skill under `<plugin>/skills/` with no directory of that name under `evals/` is reported and
is not a violation. Coverage is not a rule of this format, so it fails nothing on its own.
`cowork_evals run --require-coverage` is what turns a report into a preflight failure.

## Authoring traps

Each of these has a silent failure mode, and each is fixed by editing the case.

- **A grader file needs `---` frontmatter delimiters.** Without them it is a note and is
  ignored, so the case runs with fewer graders than it appears to have.
- **`min: 0, max: 0` is how a must-not-call assertion is written.** `max: 0` alone can never
  pass, because `min` stays 1.
- **`file_exists` only sees files created during the run.** Not scaffold output, and not
  files merely modified.
- **`llm` graders refuse binaries.** A `.pptx` is a ZIP. Render to an image, or write text.
  An image file is shown to the judge as an image, except on the CoWork backend, where an
  image focus is a grader skip. See [cowork_backend.md](cowork_backend.md).
- **Scaffolds run in an empty working directory** with a minimal environment, no
  credentials, and a 2-minute cap. Reference resources as `$(dirname "$0")/...`.
- **`context.add_dirs` must stay inside the case directory.** Naming the eval directory, a
  sibling case, the plugin root or the case's own `graders/` refuses the run.
- **A `target` on an `llm` grader is ignored.** That key is `focus`, and the grader judges
  `last_message` while looking as if it judges a file.

The traps that a case cannot fix, because they are the harness rather than the file, are in
[plugin_eval.md](plugin_eval.md).
