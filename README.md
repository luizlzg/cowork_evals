# CoWork Evals

Run evals for Claude CoWork skills and plugins, and run a plugin's own Python tests on the
CoWork runtime.

Neither is written here. This is a library, installed by the repository that owns the plugins
under test. That repository writes the cases and the tests, and points this one at them.

CoWork exposes no scriptable entry point, so there is no single way to run an eval against it.
This package holds two: Claude Code inside a container that reproduces the CoWork image, and
the real CoWork desktop application driven directly.

An eval is written once, in the `claude plugin eval` case format, and runs on either. The
backend changes, the case does not. The CoWork backend honours a subset of the format, because
it drives a live session rather than the harness.

## Install

Python 3.14 or later. The package is not on PyPI yet, so it installs from this repository.

```bash
uv add --dev "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.0"
```

```bash
pip install "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.0"
```

```bash
uv tool install "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.0"
```

The last line installs the command on its own, outside any project. The reference after `@` is
a tag, a branch or a commit, and it is the pin. Drop it to track the default branch.

The distribution is `cowork-evals`. The command it installs is `cowork_evals`.

## What you need

| To run                | You need                                                            |
| --------------------- | --------------------------------------------------------------------- |
| Anything              | `claude` on `PATH`, signed in                                       |
| The container backend | Docker or Rancher Desktop, running                                  |
| The CoWork backend    | macOS, the CoWork desktop application signed in, and a profile named in `cowork_evals.yaml` |

`cowork_evals check --all` reports what each backend is still missing, and names the command
that supplies it.

## Using it

```bash
cowork_evals setup --docker          # build the container images, and log in once
cowork_evals check --all             # what each backend still needs
cowork_evals run  --docker path/to/plugin          # an eval: a model, graders, a gate
cowork_evals test --docker path/to/plugin/tests    # pytest on the CoWork runtime, no model
cowork_evals prune --docker          # delete what setup built
```

The command takes one path, and the path is the scope: a case, a skill, a plugin's suite, or a
directory of plugins.

`run` grades what a model produced and exits non-zero when the gate fails. `test` runs no model,
runs your own pytest suite inside the CoWork runtime, and returns pytest's exit code unchanged.

Every option has a default in `cowork_evals.yaml`, in the working directory. That file is the
only configuration route: nothing is read from the process environment, and there is no `.env`.
Copy `cowork_evals.example.yaml`, which carries every key and every default. Runs write to
`logs/` under the working directory.

## Documentation

| File                                             | Covers                                             |
| ------------------------------------------------ | ---------------------------------------------------- |
| [`docs/cli.md`](docs/cli.md)                     | The whole command surface: verbs, options, exit codes |
| [`docs/eval_format.md`](docs/eval_format.md)     | How to write a case: tree, frontmatter, graders    |
| [`docs/approaches.md`](docs/approaches.md)       | The two backends, and what each one proves         |
| [`docs/running_evals.md`](docs/running_evals.md) | The run: what is built today, the gate, logs, cost |
| [`docs/cowork_test.md`](docs/cowork_test.md)     | `test`, and the runtime your suite gets            |
| [`docs/library.md`](docs/library.md)             | What ships, what it writes, and where              |
| [`docs/README.md`](docs/README.md)               | Everything else, in reading order                  |

## License

MIT. See [`LICENSE`](LICENSE).

## Public repository

Anyone can read this repository. Before committing any file, check that it carries no
username, email address, home directory path, host name, tenant identifier, employer name,
account identifier or session identifier. This covers test fixtures, log excerpts and
Dockerfiles, not only prose.

Record a measured local fact with a placeholder: a path as `<profile>` or `~/...`, and an
account as the environment variable that supplies it. A measured fact that cannot be written
without an identifier does not go in the repository.

## Contributing

[`scripts/README.md`](scripts/README.md) is the task index: the first clone, the tests, the
lint and the build. [`CLAUDE.md`](CLAUDE.md) holds the working rules and the writing rules.
Each directory has a `README.md` that indexes it and owns the rules for it.
