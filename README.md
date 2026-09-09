# CoWork Evals

Run evals for Claude CoWork skills and plugins.

Evals are not written here. This is a library, installed by the repository that owns the
plugins under test. That repository writes the cases and points this one at them.

CoWork exposes no scriptable entry point, so there is no single way to run an eval against
it. This package holds three, from cheapest to most accurate: Claude Code against a 3.10
runtime mirrored from the image, Claude Code inside a container that reproduces the image,
and the real CoWork desktop application driven directly.

An eval is written once, in the `claude plugin eval` case format, and runs on any of the
three. The backend changes, the case does not. The CoWork backend honours a subset of the
format, because it drives a live session rather than the harness.

[`docs/approaches.md`](docs/approaches.md) says what each one proves and what it does
not, which subset, and links each to its design.
[`docs/running_evals.md`](docs/running_evals.md) carries the status table, which says what is
built today.

The code under test is bound to Python 3.10 and the CoWork wheel set. Nothing in this
package is; it runs on a laptop. See [`docs/runtime.md`](docs/runtime.md).

## Using it

```bash
uv add --dev cowork-evals            # or: pip install cowork-evals

cowork_evals setup --docker          # build the container image, and log in once
cowork_evals check --all             # what each backend still needs
cowork_evals run --docker path/to/plugin/evals
```

The command takes one path, and the path is the scope: a case, a skill, a plugin's suite, or
a directory of plugins. [`docs/cli.md`](docs/cli.md) is the whole surface.
[`docs/library.md`](docs/library.md) says what ships, what it writes and where.

The caller is expected to have `claude`, and for the other two backends Docker or Rancher
Desktop, and the CoWork desktop application. `cowork_evals check` reports what is missing.

## Layout

| Path                            | Holds                                                               |
| ------------------------------- | ------------------------------------------------------------------- |
| `src/cowork_evals/`             | The package. What ships, and the only thing that does               |
| [`docs/`](docs/README.md)       | Reference material. [`docs/README.md`](docs/README.md) is the index |
| [`plans/`](plans/README.md)     | Work in progress. A plan stays after it is implemented              |
| [`scripts/`](scripts/README.md) | Development tasks for this repository. Never shipped                |
| [`plugins/`](plugins/README.md) | Fixture plugins for this repository's own tests                     |
| [`tests/`](tests/README.md)     | Deterministic tests for this repository's own code                  |
| `logs/`                         | Eval run output. Git-ignored, and absent until a run creates it     |
| `cowork_evals.yaml`             | Every setting, in three sections. Git-ignored: it names a profile   |

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
scripts/init.sh                 # builds .venv (3.14, tooling) and the 3.10 CoWork mirror
scripts/test.sh                 # the unit tests
scripts/image.sh                # builds the container image the integration tier needs
scripts/parity.sh               # probes that image against the CoWork inventory
scripts/test.sh -m integration  # the real-system tests. Boots a CoWork VM, and spends on two eval runs
scripts/lint.sh
```

[`scripts/README.md`](scripts/README.md) is the task index. Every script takes `--help`.
Those scripts are for working on this repository and are not part of the distribution.

[`CLAUDE.md`](CLAUDE.md) holds the working rules and the writing rules. Each directory has a
`README.md` that indexes it and owns the rules for it.
