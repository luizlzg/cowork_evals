# ask: one prompt to a CoWork session, from the command line and from a skill

Branch: `feat/ask`.

## Scope

The driver submits one prompt, waits, and returns a session document. It has done so since
plan 1. Nothing reaches it except Python: there is no verb over it, and the one shipped skill
is about writing evals. This plan puts a verb on the driver and a skill on the verb, so a
question about what a real CoWork session does is answered by asking one.

It builds:

| Part                                            | Is                                                            |
| ----------------------------------------------- | ------------------------------------------------------------- |
| `cowork_evals ask --cowork <prompt>`            | One submission, one printed answer. No run directory, no gate |
| `cowork_evals ask --cowork --session <dir>`     | The same printed answer, read from a session already on disk  |
| The `cowork-ask` skill                          | Shipped package data, installed by `init` beside the eval skill |
| `scripts/dev_skills.sh`                         | The shipped skills, copied into this repository's `.claude/skills/` |
| One dated snapshot in `docs/cowork_desktop.md`  | What one session actually did when asked to write a file, shell out, fetch a URL and fire a skill |

It does not build:

| Not built                                | Why                                                                  |
| ---------------------------------------- | --------------------------------------------------------------------- |
| A session list or a session browser      | The run log and the printed session directory are enough to find one  |
| A second submission on the Docker backend | `ask` reaches a live session. The container has none                  |
| Any change to the driver                 | `CoWork.run` and `CoWork.collect` already do the whole of it          |
| A result document, a gate or a log directory | `ask` is not an eval. It answers a question and returns               |

## What this unblocks

Four facts are currently guessed at and are answerable by measurement once this exists.

| Question                                                        | Read by                        |
| ---------------------------------------------------------------- | ------------------------------ |
| Which tools a live session has, and whether it asks before using one | the Docker backend's `eval.allow_tools` default |
| Whether a session writes files without being granted anything    | the same                        |
| Which case keys a session genuinely cannot honour                | the runnability rule            |
| Whether a session can run with a skill absent                    | the baseline arm on CoWork      |

The measurements themselves are each plan's own work. This plan makes one of them, in phase 5,
because it is the one that proves the verb.

## The surface

```
cowork_evals ask --cowork <prompt> [--timeout-seconds N] [--json] [--dry-run]
cowork_evals ask --cowork --session <dir> [--json]
```

| Option               | Does                                                                |
| -------------------- | -------------------------------------------------------------------- |
| `<prompt>`           | The prompt. `-` reads it from standard input                        |
| `--session <dir>`    | Print a session already on disk. Submits nothing, costs nothing     |
| `--timeout-seconds`  | This run's timeout, replacing `cowork.run_timeout`                  |
| `--json`             | Print the session document instead of the text                      |
| `--dry-run`          | Print the deep link and the ceiling arithmetic. Submits nothing     |

`--cowork` is required and is the verb's only backend, exactly as `--docker` is required on
`test`. The surface rule is unchanged: a verb that reaches a backend names it.

`--json` here is this verb's output form. It is unrelated to the harness flag of the same name,
which `docs/plugin_eval.md` records as never emitted.

### What is printed, and where

| Form              | Standard output          | Standard error                                              |
| ----------------- | ------------------------ | ------------------------------------------------------------ |
| Default           | the final assistant text | session directory, assistant turn count, tool names, outputs, driver log |
| `--json`          | the session document     | nothing                                                      |
| `--dry-run`       | the deep link            | the ceiling arithmetic                                       |

The split is so that `cowork_evals ask --cowork "..." > answer.txt` holds the answer and
nothing else. A footer line whose value is empty is not printed.

### Usage errors

Each returns 2, from the verb rather than from `argparse`.

| Typed                              | Refused because                       |
| ---------------------------------- | -------------------------------------- |
| neither a prompt nor `--session`   | there is nothing to print              |
| a prompt and `--session` together  | the session is either new or on disk   |
| `--timeout-seconds` with `--session` | nothing waits                        |
| `--dry-run` with `--session`       | nothing would be submitted             |

### Exit codes

| Code | Means                                                                  |
| ---- | ----------------------------------------------------------------------- |
| 0    | A session document was printed                                          |
| 2    | A usage error above                                                     |
| 3    | The CoWork preflight is unmet, or the driver raised code 2              |
| 1    | Everything else the driver raised. No session document was printed      |
| 130  | Interrupted                                                             |

Driver code 2 is configuration or the rate ceiling, which is the preflight class, so it maps
to 3 and matches what `run --cowork` does with the same code. Code 7 is a run timeout and
carries a session directory: the verb collects that directory, prints what the session
produced, and still exits 1. That is what the CoWork backend already does with a timeout.

## Decisions

Every one of these is settled. None is left to the implementer.

| Decision                                                        | Reason                                                                     |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| The verb is `ask`                                               | It submits a prompt and prints the answer. It runs no eval                 |
| `--cowork` is required                                          | `test --docker` is the precedent for a single-member backend group          |
| `--session` skips the preflight entirely                        | It reads a directory. It needs no macOS, no profile and no Accessibility grant |
| The rate ceiling stays the driver's                             | `CoWork` already refuses over `max_runs` and writes the run log. A second ceiling in the verb would be a second source |
| `ask` writes nothing on the host                                | `test` is the precedent: no run directory, no `latest`, no `env.txt`, no pruning |
| The session document is printed, never saved by the verb        | The session directory in the profile is the permanent record, and nothing here writes under a profile |
| Two shipped skills, not one widened skill                       | They fire on different questions. The eval skill fires on a case tree and the command; the ask skill fires on what a live session does |
| `data/skill/` becomes `data/skills/<name>/SKILL.md`             | One directory per skill, and `init` installs every directory under it rather than a hard-coded pair |
| This repository's `.claude/skills/` is generated and git-ignored | The shipped copy is the one source. A committed second copy would be a duplicate with no rule |

## Phases

Work in order. Tick a box when it is verified, then commit. Do not batch ticks.

### Phase 1: the verb

- [x] `_ask_parser` in `src/cowork_evals/cli.py`: the positional prompt, `--session`,
      `--timeout-seconds`, `--json`, `--dry-run`, and `_backend_group(verb, COWORK)`
- [x] The four usage refusals, returning 2 with a message naming what was typed
- [x] `_ask(args, config)`: the CoWork preflight unless `--session`, then the driver call
- [x] `-` as the prompt reads standard input
- [x] `--dry-run` prints `CoWork.deep_link` and the ceiling arithmetic, and submits nothing
- [x] The two printed forms, on the two streams the table above names
- [x] The exit code mapping, including the code 7 collection
- [x] `ask` is dispatched from `_dispatch`

### Phase 2: the skills directory

- [x] Move `src/cowork_evals/data/skill/SKILL.md` to
      `src/cowork_evals/data/skills/cowork-evals/SKILL.md`
- [x] `resources.py`: `SKILLS` is the directory, and the install target of a skill is
      `.claude/skills/<directory name>/SKILL.md`
- [x] `_init` installs every skill directory, and still overwrites nothing
- [x] `scripts/build.sh` still produces a wheel carrying both skills, verified by unpacking it

### Phase 3: the ask skill

- [x] `src/cowork_evals/data/skills/cowork-ask/SKILL.md`, name `cowork-ask`
- [x] Its frontmatter triggers on a question about what a real CoWork session does, on a
      behaviour that has to be confirmed in the product, and on `cowork_evals ask` failing
- [x] It states no fact of its own. Every rule in it is in a document, and it names the
      document. That is the rule `docs/library.md` already holds the eval skill to
- [x] It carries the cost, in one line: a VM boot, the keyboard for the length of the run,
      and one submission against `cowork.max_runs`
- [x] It carries the one rule that makes a measurement worth anything: ask the session to do
      the thing, and read what it did. What a session says about its own configuration is not
      evidence
- [x] `scripts/dev_skills.sh` copies every shipped skill into `.claude/skills/`, and
      `--help` prints its own header, as every script here does
- [x] `.gitignore` ignores `.claude/skills/`

### Phase 4: tests

Activate the testing rules in `tests/README.md` first. No mock, no fake, no stub, no patch,
no skip.

- [x] Unit: `ask --cowork "hi"` parses, and `ask "hi"` without a backend exits 2
- [x] Unit: each of the four usage refusals exits 2
- [x] Unit: `--session <fixture>` over the session fixture under `tests/data/cowork/sessions`
      prints the final text on standard output and the footer on standard error, and exits 0
- [x] Unit: `--session <fixture> --json` prints a document that parses and whose `session_dir`
      is the fixture
- [x] Unit: `--dry-run` prints a deep link carrying the encoded prompt, and writes no run log
      entry
- [x] Unit: `--session` naming a directory that is not there exits 1 and says so
- [ ] Integration: one real `ask --cowork` against the configured profile exits 0, prints a
      non-empty answer, and names a session directory that exists

### Phase 5: documentation, and the first measurement

- [x] `docs/cli.md`: the synopsis line, an `## ask` section, the preflight paragraph for
      `--session`, and the exit code table
- [x] `docs/library.md`: the shipped file table gains the second skill, and the skill section
      states the rule that separates the two
- [x] `README.md`: the verb appears in the two command listings that name the verb set
- [x] `scripts/README.md`: the `dev_skills.sh` row
- [ ] Fire four asks against a real session: write a file, run a shell command, fetch a URL,
      and fire a skill the account has. Record what each did
- [ ] `docs/cowork_desktop.md`: one section holding those four results, dated, and called a
      snapshot
- [ ] `plans/README.md`: the row moves to `implemented` on the merge, and the file moves to
      `done/plan_ask.<YYYYMMDD>.md`

If the four asks in phase 5 show that a session refuses one of the four, that is the
measurement, and the snapshot records the refusal. Nothing in this plan changes shape on the
result: the verb and the skill are what it builds, and the snapshot is what they produce.

## Verification

- [x] `scripts/lint.sh`
- [x] `scripts/test.sh tests/unit`
- [x] `scripts/test.sh` with the default selection, green
- [ ] `scripts/test.sh -m integration -k ask`, on a machine with the profile and the grant
- [x] `cowork_evals ask --cowork --dry-run "hello"` prints a deep link and spends nothing
- [ ] `cowork_evals ask --cowork "Reply with the single word: ready"` prints `ready`
- [ ] `scripts/dev_skills.sh`, then a Claude Code session in this repository fires
      `cowork-ask` on the question "what tools does a CoWork session have"
