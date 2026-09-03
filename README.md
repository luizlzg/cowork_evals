# cowork_evals

Run evals for Claude CoWork skills and plugins.

CoWork exposes no scriptable entry point, so there is no single way to do this. This
repository holds three, from cheapest to most accurate, and says plainly what each one
proves and what it does not.

| Approach                   | Runs on                      | Proves                                     |
| -------------------------- | ---------------------------- | ------------------------------------------ |
| Claude Code, mirrored venv | Local `claude`, Python 3.10  | Skill logic, activation, hook gates        |
| Claude Code, Docker        | Local `claude`, Ubuntu 22.04 | The above plus rendering, OCR, fonts, CLIs |
| CoWork, driven directly    | The real CoWork VM           | The deployed stack, end to end             |

`docs/approaches.md` explains the trade-offs, and links each approach to its design.

## Setup

```bash
scripts/init.sh   # builds .venv (3.14, tooling) and .venv_cowork (3.10, CoWork mirror)
scripts/test.sh
scripts/lint.sh
```

`scripts/README.md` is the task index. Every script takes `--help`.

## Layout

| Path       | Holds                                                        |
| ---------- | ------------------------------------------------------------ |
| `docs/`    | Reference material. `docs/README.md` is the index            |
| `plans/`   | Work in progress. A plan is deleted once implemented         |
| `scripts/` | Every task. No build system                                  |
| `plugins/` | Plugins under test                                           |
| `tests/`   | Deterministic tests for this repository's own code           |
| `logs/`    | Eval run output. Git-ignored                                 |

## Public repository

Anyone can read this repository. Before committing any file, check that it carries no
username, email address, home directory path, host name, tenant identifier, employer name,
account identifier or session identifier. This covers test fixtures, log excerpts and
Dockerfiles, not only prose.

Record a measured local fact with a placeholder: a path as `<profile>` or `~/...`, and an
account as the environment variable that supplies it. A measured fact that cannot be
written without an identifier does not go in the repository.

## Contributing

`CLAUDE.md` holds the working rules and the writing rules. Each directory has a
`README.md` that indexes it and owns the rules for it.
