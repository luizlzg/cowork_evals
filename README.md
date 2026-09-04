# cowork_evals

Run evals for Claude CoWork skills and plugins.

Evals are not written here. This is a library, installed by the repository that owns the
plugins under test. That repository writes the cases and points this one at them.

CoWork exposes no scriptable entry point, so there is no single way to run an eval against
it. This package holds three ways, from cheapest to most accurate, and says plainly what
each one proves and what it does not.

| Approach                   | Runs on                      | Proves                                     |
| -------------------------- | ---------------------------- | ------------------------------------------ |
| Claude Code, mirrored venv | Local `claude`, Python 3.10  | Skill logic, activation, hook gates        |
| Claude Code, Docker        | Local `claude`, Ubuntu 22.04 | The above plus rendering, OCR, fonts, CLIs |
| CoWork, driven directly    | The real CoWork VM           | The deployed stack, end to end             |

An eval is written once, in the `claude plugin eval` case format, and runs on any of the
three. The backend changes, the case does not. The CoWork backend honours a subset of the
format, because it drives a live session rather than the harness.

`docs/approaches.md` explains the trade-offs, says which subset, and links each approach to
its design.

## Using it

```bash
uv add --dev cowork-evals            # or: pip install cowork-evals

cowork_evals setup --venv            # build the 3.10 CoWork mirror
cowork_evals check --all             # what each backend still needs
cowork_evals run --venv path/to/plugin/evals
```

The command takes one path, and the path is the scope: a case, a skill, a plugin's suite, or
a directory of plugins. `docs/cli.md` is the whole surface. `docs/library.md` says what
ships, what it writes and where.

The caller is expected to have `claude`, and for the other two backends Docker or Rancher
Desktop, and the CoWork desktop application. `cowork_evals check` reports what is missing.

## Layout

| Path       | Holds                                                        |
| ---------- | ------------------------------------------------------------ |
| `docs/`    | Reference material. `docs/README.md` is the index            |
| `plans/`   | Work in progress. A plan is deleted once implemented         |
| `scripts/` | Development tasks for this repository. Never shipped         |
| `plugins/` | Fixture plugins for this repository's own tests              |
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

```bash
scripts/init.sh   # builds .venv (3.14, tooling) and the 3.10 CoWork mirror
scripts/test.sh
scripts/lint.sh
```

`scripts/README.md` is the task index. Every script takes `--help`. Those scripts are for
working on this repository and are not part of the distribution.

`CLAUDE.md` holds the working rules and the writing rules. Each directory has a
`README.md` that indexes it and owns the rules for it.
