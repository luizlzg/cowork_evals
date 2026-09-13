# Eval case format

## Summary

What a case is made of: the tree, the file names, the frontmatter, the graders and the
authoring traps. This is the authoring contract for every eval in this repository, on both
backends.

- **A case is a directory**: a `prompt.md` with frontmatter and a prompt body, a `graders/`
  directory, an optional `case.yaml`, and an optional `checks/` directory.
- **Two addressability keys are required**, `tags` and `plugins`, and both are checked.
- **Graders come in two classes.** Structural graders are deterministic and carry the verdict;
  judged graders call a model and are printed. Prefer a structural one.
- **A `checks/` directory holds assertions written as Python**, run on the host after the run
  is graded. It is added to a case, never in place of its graders.
- **Only two grader types choose what they look at, and they use different keys.** `regex`
  uses `target`, `llm` uses `focus`.
- **A case a CoWork session cannot run says so, with the `no-cowork` tag.** The validator
  checks it in both directions.
- **Every trap in the last section has a silent failure mode.** Read it before writing a case.

The format is `claude plugin eval`'s own, so a case needs no adapter to run under that
harness. What the CLI does with a case is [plugin_eval.md](plugin_eval.md). How this
repository invokes it is [running_evals.md](running_evals.md). Which backend honours which
field is [approaches.md](approaches.md). The full field-by-field reference is vendored at
[claude_code/plugin_eval_reference.md](claude_code/plugin_eval_reference.md), and it is the
authority where this file is silent.

Four rules here are this repository's own and not the harness's: the `<skill>` layer under
`evals/`, the two addressability keys below, the reserved tag, and the `checks/` directory,
which the harness neither reads nor knows is there. Everything else is the harness.
`docs/claude_code/eval_smoke/` is deliberately outside all of it; see
[claude_code/eval_smoke/README.md](claude_code/eval_smoke/README.md).

## The tree

One eval directory per skill, inside the plugin, in the repository that owns the plugin.

```
<plugin>/.claude-plugin/plugin.json               # what makes <plugin> a plugin root
<plugin>/evals/<skill>/<case>/prompt.md
<plugin>/evals/<skill>/<case>/graders/<name>.md
<plugin>/evals/<skill>/<case>/checks/<name>.py    # optional, this package's own
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
the case directory, and any entry inside its `checks/`.

## Addressability

Two frontmatter keys make a case addressable, and both are checked:

- `tags: [<skill>]`, matching the case's own directory. `--tag` is the only reliable
  per-skill selector; `--case` globs the case **name**, which defaults to the directory name
  and differs from it whenever the case writes a `name`.
- `plugins: ["../../.."]`, the plugin root, counted from the case directory. That is three
  levels up from a case under `evals/<skill>/<case>/`.

## The reserved tag

`no-cowork` is the one reserved tag value, and there is no other. A case carrying it declares
that a live CoWork session cannot run it. It lives in `tags:`, beside the `<skill>` tag the
case already carries, so `--tag <skill>` still selects it.

Three things make a case unrunnable there, and a case carrying any of them carries the tag.

| Source                                               | Written in                       | Why a session cannot honour it        |
| ---------------------------------------------------- | -------------------------------- | ------------------------------------- |
| `max_turns`, `model`, `allowed_tools`, `append_system_prompt` or `env` | `prompt.md` frontmatter | [approaches.md](approaches.md), key by key |
| Any `context.*` key                                  | `case.yaml`                      | Nothing stages files into the VM      |
| A `mocks/` directory on the case's layer chain       | `evals/mocks/`, or beside the case | The MCP servers here are the real ones |

The third is a directory and not a key, and the case that inherits it can be several
directories below. It is declared at each case and not at the directory, so a plugin whose
`evals/mocks/` covers every case tags every case.

The validator checks both directions, and each costs exit 3 inside `run`'s preflight.

| The case                                                  | Rule                 |
| --------------------------------------------------------- | -------------------- |
| Carries a source above and no `no-cowork`                 | `no-cowork-missing`  |
| Carries `no-cowork` and no source above                   | `no-cowork-unneeded` |

The second direction is what keeps the tag from becoming a way to switch a case off. There is
no `skip:` field in a case tree.

On the Docker backend the tag is a tag, and the harness filters on the tags it is given. On
the CoWork backend the case is not submitted, and is counted rather than failed. There is no
`no-docker` counterpart, because nothing names a case key that backend cannot honour. See
[running_evals.md](running_evals.md).

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

Writing out a key the CoWork backend cannot honour is what makes the reserved tag above
required. Leaving it out does not, because a default is not a request. See
[running_evals.md](running_evals.md).

### What an unknown key does, in each of the two files

On CLI 2.1.265, through the container backend, over one fixture case carrying
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

On Node 25.9.0, over the pattern `^\s*(?:blocker|major|minor)\s*$`:

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
under `--ablation with-without`, which is off by default and is the container backend's
alone, so a case that never asks for the baseline arm sets it only to stay portable. See
[running_evals.md](running_evals.md).

Prefer a deterministic grader over a judged one for anything long. Judges are noisy on long
inputs.

The skill-fired idiom:

```yaml
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?<skill>"'
```

## checks/

Optional. One file per assertion an author writes as Python, run on the host after the run is
graded, on either backend. It is [checks.md](checks.md), and this section is the part of it
that binds a case file.

```python
from cowork_evals.checks import Result, Run, check


@check
def totals_add_up(run: Run) -> None:
    book = openpyxl.load_workbook(run.file("totals.xlsx"))
    assert book.active["D10"].value == 4200
```

| Fact                                                             | Is                                                   |
| ------------------------------------------------------------------ | ---------------------------------------------------- |
| A check's name                                                   | `<file stem>.<function name>`                        |
| A check's weight                                                 | 1, always. `@check` takes no arguments               |
| The result                                                       | a grader result of `type: check`, in the same document |
| A failed check                                                   | fails the run, as a failed structural grader does    |
| A file under `checks/` carrying no `@check`                      | a helper, and no violation                           |
| A `checks/` directory carrying no `@check` at all                | a violation                                          |

**A check file is host code and is not bound by the image wheel set.** It sits under the path
passed to `cowork_evals run`, and everything else under that path is code under test, which
imports only what the CoWork image carries. A check is not: the run is over and graded before
a check starts, and a check reads what that run left on the host. Its own imports are the
consumer's own dependency. See [runtime.md](runtime.md) and [library.md](library.md).

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
| Every file under `checks/` imports                                          |
| A `checks/` directory carries at least one function decorated with `@check` |
| No two checks of one case share a name                                      |
| No `context.add_dirs` entry resolves under the case's own `checks/`         |
| A case a CoWork session cannot run carries `no-cowork`                      |
| A case carrying `no-cowork` is one a CoWork session cannot run              |

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
  sibling case, the plugin root or the case's own `graders/` refuses the run. That list is
  exhaustive: every other directory inside the case is a fixture directory to the harness and
  is granted, so a directory holding anything the agent under test must not read is this
  repository's to refuse.
- **A `target` on an `llm` grader is ignored.** That key is `focus`, and the grader judges
  `last_message` while looking as if it judges a file.
- **A case carrying `checks/` and no grader does not load.** The harness refuses a case with
  no grader at all, so `checks/` is added to a case and never replaces its `graders/`.
- **A check reads a collected run, so `--no-keep-traces` gives up every check.** With nothing
  collected each check is a skip, and a skip fails the run.
- **A `checks/` file with no decorated function asserts nothing.** A helper is a file like any
  other, so only a `checks/` directory with no check anywhere in it is reported.
- **Each run of a case runs every check again.** A case at `runs: 3` carrying one judged check
  costs three of every judge call it makes.

The traps that a case cannot fix, because they are the harness rather than the file, are in
[plugin_eval.md](plugin_eval.md).
