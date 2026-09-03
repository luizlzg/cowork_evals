# scripts

Every task in this repository is a shell script. There is no build system: nothing here has
file dependencies or incremental rebuild, so make would be a task runner in disguise and a
second layer over these scripts.

Each script takes `--help` and prints its own header. `lib.sh` is sourced, never executed.

| Script           | Does                                                    |
| ---------------- | ------------------------------------------------------- |
| `init.sh`        | Build both environments. Run once after cloning         |
| `venv.sh`        | Build or update `.venv`, the repository tooling env     |
| `cowork_venv.sh` | Build or verify `.venv_cowork`, the CoWork image mirror |
| `cowork_run.sh`  | Run one command under the mirror                        |
| `test.sh`        | Run the test suite under `.venv`                        |
| `lint.sh`        | Lint Python and shell. `--fix` applies                  |
| `lib.sh`         | Shared `ROOT`, `VENV`, `COWORK`, `die`, `need`, `usage` |

## Conventions

- `#!/usr/bin/env bash` and `set -euo pipefail`.
- Source `lib.sh` on the second line. It sets `ROOT` from `BASH_SOURCE`, so a script works
  from any working directory.
- The header comment block is the help text. `usage` prints it, so help cannot drift from
  the file.
- Exit non-zero with a one-line reason through `die`. Never print a stack of advice.
- Verify a precondition before acting. `cowork_run.sh` refuses `uv`, and
  `cowork_venv.sh --check` refuses to write.
- Every eval runner exports `CLAUDE_CODE_WALNUT_SPIRE`, so no developer sets it by hand.
  See [`../docs/plugin_eval.md`](../docs/plugin_eval.md).

The eval runner scripts are specified in
[`../docs/running_evals.md`](../docs/running_evals.md). Rows are added here as each is
built.
