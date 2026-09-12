# scripts

Development tasks for this repository. They are not part of the distribution, and a
consumer never sees them. What ships is the `cowork_evals` package and its command; see
[`../docs/library.md`](../docs/library.md) and [`../docs/cli.md`](../docs/cli.md).

There is no build system and no Makefile for these. Each script takes `--help` and prints
its own header. `lib.sh` is sourced, never executed.

| Script           | Does                                                    |
| ---------------- | ------------------------------------------------------- |
| `init.sh`        | Build `.venv`. Run once after cloning                    |
| `venv.sh`        | Build or update `.venv`, the repository tooling env     |
| `cowork_venv.sh` | Build or verify the CoWork image mirror, on demand      |
| `cowork_run.sh`  | Run one command under the mirror                        |
| `image.sh`       | Build or verify the container image                     |
| `cowork_pytest.sh` | Build or verify the test image, and run a pytest suite in it |
| `login.sh`       | Log in once in a container, for the login this package owns |
| `parity.sh`      | Probe the image and compare it against the inventory    |
| `test.sh`        | Run the test suite under `.venv`                        |
| `lint.sh`        | Lint Python and shell. `--fix` applies                  |
| `build.sh`       | Build the distribution into `dist/`, and verify the wheel |
| `dev_skills.sh`  | Copy the shipped skills into this repository's `.claude/skills/` |
| `lib.sh`         | Shared `ROOT`, `VENV`, `COWORK`, `die`, `need`, `usage` |

`image.sh` and `parity.sh` are the image's half of what `cowork_venv.sh` is for the mirror.
Run `image.sh` and then `login.sh` before the integration tier: those tests need the image
and the login, and create neither. See [`../docs/docker.md`](../docs/docker.md).

`cowork_pytest.sh` is the test image's half of what `image.sh` is for the eval image, and
it also runs a suite in it. Run it before the integration tier for the same reason. It
carries the `cowork_` prefix the other two runtime scripts carry, so it is not read as a
sibling of `test.sh`, which runs this repository's own tests under `.venv`. See
[`../docs/cowork_test.md`](../docs/cowork_test.md).

`dev_skills.sh` is how this repository gets the skills a consumer gets from
`cowork_evals init`. This repository is not a consumer, so `.claude/skills/` here is
generated and git-ignored, and the shipped copy under `src/cowork_evals/data/skills/` is the
one source. See [`../docs/library.md`](../docs/library.md).

The three eval backends, the verdict and the case validator are not here. They are library
code, they are reached through the `cowork_evals` command, and a row is never added below
for one of them.

## Conventions

- `#!/usr/bin/env bash` and `set -euo pipefail`.
- Source `lib.sh` on the second line. It sets `ROOT` from `BASH_SOURCE`, so a script works
  from any working directory.
- The header comment block is the help text. `usage` prints it, so help cannot drift from
  the file.
- Exit non-zero with a one-line reason through `die`. Never print a stack of advice.
- Verify a precondition before acting. `cowork_run.sh` refuses `uv`, and
  `cowork_venv.sh --check` refuses to write.
