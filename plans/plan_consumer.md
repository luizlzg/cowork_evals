# plan_consumer

Make the installed package teach itself. Today a consumer installs the wheel and gets code,
two Dockerfiles and three requirements files. Every file that says how to write a case, how
to configure the command, or what the runtime provides stays in the checkout. This plan ships
`docs/`, removes the references that break on the way, and adds the two verbs and the one
skill that put them in front of a Claude Code session in the consumer's repository.

Branch: `feat/consumer`. Design: [`../docs/library.md`](../docs/library.md) owns the
boundary and the two reference rules below. [`../docs/cli.md`](../docs/cli.md) owns the two
new verbs.

## What was measured

Captured 2026-09-09, against `dist/cowork_evals-0.1.1-py3-none-any.whl` installed into a
clean 3.14 venv and a consumer repository holding one plugin.

| Fact                                                                   | Value                       |
| ---------------------------------------------------------------------- | --------------------------- |
| Files in the wheel                                                     | 29, no `.md` but `LICENSE`  |
| Consumer-facing files named by README's Documentation table that ship  | 0 of 6                      |
| `docs/*.md` references inside shipped `.py` files                      | 134, of which 26 are links  |
| Links inside `docs/` that escape `docs/`                               | 16, of which 11 leave the shipped tree |
| `cowork_evals.example.yaml` in the wheel or sdist                      | no, and README says to copy it |
| `check --all` on a clean repository                                    | exit 3, one unlabelled line about the CoWork profile |
| `check --docker` on the same machine                                   | `ready`, exit 0             |
| Backends `check --all` actually probes                                 | both. `preflight.checks_all` iterates them, and Docker contributed no line because it was ready |
| README quickstart followed verbatim in a clean repository              | `run --docker --dry-run` exit 0 |

The last row is why this plan changes no case format and no grader: what is written works.
What is missing is every route to knowing it.

## Decisions

Both were the developer's, taken 2026-09-09.

| Question                                    | Decision                                                        |
| ------------------------------------------- | ----------------------------------------------------------------- |
| Which of `docs/` ships                      | All of it, `docs/claude_code/` included                          |
| How a cold Claude Code session finds it     | A skill and a `CLAUDE.md` block, both written by `cowork_evals init` |

Shipping `docs/` whole is the rule: there is no ship list to curate and no per-file decision
when a document is added. The first assessment proposed six files and had already missed
[`../docs/runtime.md`](../docs/runtime.md), which is what a plugin author reads to know the
wheel set the code under test may import.

## The two reference rules

`docs/` ships and the tree around it does not, so a reference that crosses that edge cannot
be a link: its target sits at a different path in the checkout and in the install, and one of
the two is always wrong. Both rules are written into
[`../docs/library.md`](../docs/library.md) in phase 1 and enforced by a test in phase 8.

| Rule | Where                | Says                                                                     |
| ---- | -------------------- | -------------------------------------------------------------------------- |
| R1   | Any file under `src/` | Names a document by its `docs/` path. Never links to one                  |
| R2   | Any file under `docs/` | Links to a target inside `docs/`. Names a target outside it as plain text |

R1 covers 26 links. R2 covers 11: the 5 links to `../plugin_eval.md` and `../../eval_format.md`
stay links, because they stay inside `docs/`.

## The layout

`docs/` stays at the repository root. Hatchling `force-include` places it at
`cowork_evals/docs/` in the wheel, and the sdist include list carries `/docs`. Verified
2026-09-09: 32 files in both artifacts. Nothing moves in the checkout, so no reference from
`README.md`, `CLAUDE.md`, `plans/`, `scripts/` or `tests/` changes.

`cowork_evals.example.yaml` moves from the repository root to
`src/cowork_evals/data/cowork_evals.example.yaml`. It becomes shipped data for the same
reason the requirements files are: `init` reads it at run time on a machine with no checkout.

## Phases

### Phase 1: ship docs/

- [x] `pyproject.toml`: `force-include = { "docs" = "cowork_evals/docs" }` on the wheel target, `/docs` in the sdist include list, and the stale comment above the sdist block rewritten
- [x] `scripts/build.sh`: drop `docs` from the loop that refuses a development directory in the sdist, and assert `cowork_evals/docs/eval_format.md` and `cowork_evals/docs/claude_code/plugin_eval_reference.md` are in the wheel
- [x] `docs/library.md`: the "What ships" table carries `docs/` as `yes`, the `tests/`, `plugins/`, `plans/` row loses it, and the paragraph under the table states why documentation is shipped data
- [x] `docs/library.md`: R1 and R2 written, with the reason
- [x] `scripts/build.sh` passes

### Phase 2: fix the references

- [x] R1 applied: the 26 markdown links under `src/cowork_evals/` become plain-text names
- [x] R2 applied: the 11 escaping links under `docs/` become plain-text paths
- [x] `src/cowork_evals/__init__.py`: the docstring describes the package, not the driver alone
- [x] `scripts/lint.sh` passes

### Phase 3: the docs verb

- [x] `cowork_evals docs` with no argument lists every shipped document name and prints the directory holding them
- [x] `cowork_evals docs <name>` prints the absolute path of one document, and exits 2 with the list when the name is unknown
- [x] `docs/cli.md`: the verb, its two forms and its exit codes

### Phase 4: the example file and the init verb

- [x] `cowork_evals.example.yaml` moves to `src/cowork_evals/data/`, and `docs/library.md` records it as shipped data
- [x] `cowork_evals init` writes `cowork_evals.yaml`, `.claude/skills/cowork-evals/SKILL.md` and a pointer block in `CLAUDE.md`, into the working directory
- [x] `init` writes only what is absent, leaves what exists untouched, and prints one line per target saying which of the two it did
- [x] `docs/cli.md`: the verb, what it writes, and its exit codes

### Phase 5: the skill

- [x] `src/cowork_evals/data/skill/SKILL.md`: the case tree, the two addressability keys, the four structural grader types, the two judged ones, the traps, and `cowork_evals docs` as the route to the rest
- [x] The `CLAUDE.md` block `init` appends: the command, the two new verbs, and the runtime constraint on the code under test
- [x] `docs/cli.md` links neither. The skill is named in `docs/library.md` as shipped data

### Phase 6: check --all

`--all` probes both backends already. What it does not do is say so: a ready backend
contributes no line, so its output is indistinguishable from a backend that was never
reached, and no line says which backend it belongs to. `README.md` claims a per-backend
report, and this is the phase that makes the claim true.

- [x] `check --all` prints one section per backend, each naming the backend and then `ready` or its unmet lines
- [x] `check --docker` and `check --cowork` keep the output they have, which is `ready` or the lines alone
- [x] The exit code is unchanged: 0 when nothing is unmet, 3 otherwise
- [x] `docs/cli.md`: the per-backend report, and that a ready backend is stated rather than silent

### Phase 7: the documentation sweep

- [x] `README.md`: `init` in the quickstart, the two new verbs in "The command", and the Documentation table saying the files ship
- [x] `docs/README.md`: the reading order carries no change of content, and the summary states that this tree ships
- [x] `docs/cli.md`: the verb table carries seven verbs
- [x] No file outside `plans/` links to this plan

### Phase 8: tests

- [x] `docs` verb: every name it lists resolves to a file that exists
- [x] `init`: writes three targets into an empty directory, and a second run changes none of them
- [x] `init`: the `cowork_evals.yaml` it writes loads through `Config`
- [x] R1 enforced: no markdown link under `src/cowork_evals/` targets a path outside the package
- [x] R2 enforced: no markdown link under `docs/` targets a path outside `docs/`
- [x] `check --all` reports both backends when one is unconfigured
- [x] Every document named in `README.md`'s Documentation table exists
- [x] `scripts/test.sh` passes

### Phase 9: the install test

- [ ] `scripts/build.sh` passes, wheel and sdist both carrying `docs/`
- [ ] The wheel installs into a clean 3.14 venv, and `docs`, `docs eval_format` and `init` all work out of it
- [ ] In a repository holding one plugin and nothing else, `init` then a case written from the shipped skill reaches `run --docker --dry-run` exit 0
- [ ] `scripts/test.sh -m integration` passes
