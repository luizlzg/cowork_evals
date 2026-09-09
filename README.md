# CoWork Evals

Run evals for Claude CoWork skills and plugins, and run a plugin's own Python tests on the
CoWork runtime.

## Summary

Four problems stand between a CoWork skill and a test suite. This is what this package does
about each.

| Problem                                                                                   | How this solves it                                                                        |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| CoWork has no scriptable entry point, so a skill can only be exercised by a person clicking | Two backends execute a case from the command line: Claude Code inside a container that reproduces the CoWork image, and the real desktop application driven directly |
| A container is not the product, and the product cannot be run on every commit             | Both. Docker is the iteration loop and the pre-release gate. CoWork is the confirmation on the real stack, run by a person on purpose, and never a commit gate |
| Two backends would mean two eval formats and two sets of results                          | One format, `claude plugin eval`'s own. The same case tree runs on both, both write the same result document, and one gate reads it |
| A CoWork session is Python 3.10 with a fixed wheel set, so a plugin's tests passing on a laptop prove nothing about the session | `cowork_evals test` runs the plugin's own pytest suite inside that runtime, with no model in the loop |

A case asserts what a unit test cannot reach: the answer text, which tools ran and in what
order, which files the agent created, and a rubric a judge model votes on. The four structural
graders are deterministic and carry the gate. The two judged ones are printed.

The CoWork backend honours a subset of the format, because it drives a live session rather
than the harness. [`docs/approaches.md`](docs/approaches.md) says which subset, and what each
backend proves.

Evals are not written here. This is a library, installed by the repository that owns the
plugins under test. That repository writes the cases and the tests, and points this one at
them.

## Install

Python 3.14 or later. The package is not on PyPI yet, so it installs from this repository.

```bash
uv add --dev "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.1"
```

```bash
pip install "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.1"
```

```bash
uv tool install "cowork-evals @ git+https://github.com/pcingola/cowork_evals@v0.1.1"
```

The last line installs the command on its own, outside any project. The reference after `@` is
a tag, a branch or a commit, and it is the pin. Drop it to track the default branch.

The distribution is `cowork-evals`. The command it installs is `cowork_evals`.

## What you need

| Backend                    | You need                                                       |
| -------------------------- | ---------------------------------------------------------------- |
| The container, `--docker`  | Docker or Rancher Desktop running, the images, and the one-time login. `setup --docker` makes all three |
| CoWork, `--cowork`         | macOS, `claude` on `PATH`, CoWork signed in, the profile named in `cowork_evals.yaml`, and the macOS Accessibility grant |

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
