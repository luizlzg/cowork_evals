# Plan: the CoWork session environment in Docker runs

Branch `feat/session-env`, cut from `main` after the npm-tree and session-variable changes to
`docs/runtime.md`, `docs/docker.md`, the `Dockerfile`, `probe.py`, `parity.py` and their tests
are committed there. Work the phases in order. Tick a box only when it is verified, then
commit. `plans/README.md` holds the execution rules.

## Summary

A skill's `Bash` call in a CoWork session sees the 16 variables listed in `docs/runtime.md`,
under "What the host provides". In `cowork_evals run --docker`, the same call runs under
Claude Code inside the container. It also sees what Claude Code, the `claude plugin eval`
harness and `docker run` add: `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`,
`CLAUDE_CODE_SESSION_ID`, `CLAUDE_CONFIG_DIR`, `EXTRA_CA_FILE` and others. A skill that reads
one of them passes in Docker and fails in CoWork, and no run reports it. After this plan,
every `Bash` call in a Docker run sees only the variable names `cowork_evals.yaml` lists. A
skill that reads anything else gets the empty string, the same as in CoWork, and its case
fails in Docker.

## Design

Claude Code runs every shell command through the program named by
`CLAUDE_CODE_SHELL_PREFIX`. The name is present in the 2.1.265 CLI binary in the image. The
image sets that variable in the `env` block of `/etc/claude-code/managed-settings.json`,
pointing at the script `/usr/local/bin/cowork-env`. It goes in managed settings rather than
`docker run --env`, because the harness removes session-scoped variables from the Claude Code
process it starts, while managed settings still apply inside a run
(`docs/claude_code/plugin_eval_reference.md`, "Nothing personal or project-level leaks in").

The script sits only between Claude Code and the `Bash` subprocess. Claude Code, its login and
the harness keep their own environment, so authentication needs no exception. The login is a
mounted credentials file (`docs/docker.md`).

The kept names are configuration, not code. They are three lists under `docker:` in
`cowork_evals.yaml`, with defaults in `DockerSection` in `src/cowork_evals/config.py`. Each
name belongs in exactly one list, by this rule:

| Key               | A name goes here when                                     | Default                                                        |
| ----------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| `session_env`     | a CoWork session shell has it                             | the 16 names in `docs/runtime.md`                              |
| `env_passthrough` | the developer forwards it from the host. It exists today, and a forwarded name is now also kept in `Bash` | empty |
| `keep_env`        | it is already in the container, and a Docker run fails without it | `NODE_EXTRA_CA_CERTS`, the three hook names and the eight HTTP proxy names phase 1 found. Without the CA, Node in a skill cannot reach the network on a host whose proxy inspects TLS |

How the names reach the script. Phase 1 replaced the environment variable route this plan
first named: the harness strips `COWORK_EVALS_KEEP` from the CLI it starts, and a sandboxed
`Bash` call cannot see the log mount.

1. `cowork_evals` reads the three lists, in the order `session_env`, `env_passthrough`,
   `keep_env`.
2. `Docker.run` writes them to `keep_env.txt` in the run's log directory, one name per line.
   `run_argv` mounts that file read-only at `/etc/cowork_evals/keep_env.txt`.
   `run_preamble` adds `--env TZ=<zone>`. The zone is the `/etc/localtime` symlink target
   after `zoneinfo/`, and `TZ` is omitted when `/etc/localtime` is not a symlink. This reads a
   file, not the process environment, so the one-config-file rule in `CLAUDE.md` holds.
3. The harness starts Claude Code, and Claude Code runs `cowork-env '<command>'` for each
   `Bash` call and each hook command.
4. The script reads the keep file. For each name with a value, it adds `NAME=value` to an
   argument list. It then runs `env -i <list> /bin/bash -c "$1"`. Only the listed names exist
   in the result.

The names are read on every run, so changing a list needs no image rebuild. The script names
no variable except five derived ones. Their CoWork values are
functions of another variable, so the script sets them when they are listed: `USER` and
`LOGNAME` to `basename "$HOME"`, `CLAUDE_TMPDIR` and `CLAUDE_CODE_TMPDIR` to `$TMPDIR`, and
`SHELL` to `/bin/sh`. `PATH`, `NODE_PATH` and `LANG` already hold the CoWork values through the
image's `ENV` lines. A listed name with no value stays unset. That is why the three systemd
names are absent in Docker: the container has no systemd. This is a recorded Docker delta.

The names reach `eval` in the script, so each one must be a valid shell name. `_env_names` in
`config.py` already enforces that for `env_passthrough`, and it is used for the new keys too.
The script also skips a line that is not a shell name.

Out of scope:
- A static scan of plugin source. It misses names built at run time, and it flags names that
  only appear in strings. The runtime check catches exactly the reads that execute.
- `cowork_evals test --docker`. pytest runs directly in the container, and no Claude Code
  process adds variables there.
- The CoWork backend. The session already has the CoWork environment.

## Phase 1: measure

These facts are in no file. Write a first `cowork_env.sh` that only appends its argv and
`env | sort` to `$TMPDIR/prefix.log` and then execs the command, and make the `Dockerfile`
changes from phase 2. Build with `scripts/image.sh`. Run a throwaway case outside the
repository that asks for `env | sort`, with `cowork_evals run --docker --keep-traces`, so the
sandbox and the log stay in the run directory (`docs/docker.md`). Record each answer in
`docs/docker.md`, in the new section. Phase 2 then replaces the logging script with the real
one.

- [x] Does the prefix fire in a harness run? If not, the managed settings carry a
      `PreToolUse` hook on `Bash` instead. It rewrites `tool_input.command` to
      `cowork-env /bin/bash -c '<command>'`. Everything else is unchanged.
      Result: yes. No hook is needed.
- [x] Does the command arrive as one string or as an argv? For one string, the script
      execs `env -i <pairs> /bin/bash -c "$1"`, where `/bin/bash` matches the CoWork Bash
      tool (bash 5.1.16). For an argv, it execs `env -i <pairs> "$@"`. Either way the pairs
      are built before the exec, from `COWORK_EVALS_KEEP`.
      Result: one string, for a Bash call and for a hook. The script runs `/bin/bash -c "$1"`.
- [x] Does `COWORK_EVALS_KEEP` reach the script? If not, `run_preamble` writes the names to
      `keep_env.txt` in the log mount, and the script reads that file.
      Result: no, and the log mount is not visible to a sandboxed call either. The names go in `keep_env.txt` in the run's log directory, mounted read-only at `/etc/cowork_evals/keep_env.txt`. The prefix setting cannot carry an argument, so the path is fixed in the script.
- [x] Does the prefix wrap plugin hooks? Add a `SessionStart` hook to the throwaway plugin to
      find out. If it does, add `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA` and
      `CLAUDE_PROJECT_DIR` to the `keep_env` default, because hooks rely on them.
      Result: yes. The three names are in the `keep_env` default.
- [x] Which incoming names does a sandboxed call need? Remove each name the log shows, then run
      `curl -sI https://example.com` with that domain granted, and `python3 -c 'import tempfile;
      tempfile.mkdtemp()'`. A name whose removal breaks either goes in the `keep_env` default.
      Result: the HTTP proxy the sandbox sets. Without it curl exits 6. `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY` and the lower-case forms are in the `keep_env` default. `tempfile.mkdtemp()` needs only `TMPDIR`.
- [x] Does the command string Claude Code passes export any variable itself, for example from
      its shell snapshot? A name it exports that is outside the lists reaches the command after
      `env -i`, and the script cannot remove it. If one appears, record it as a Docker delta
      in `docs/docker.md`, and allow it in the fixture check by name.
      Result: no. A Bash call sees the listed names, `PWD`, `SHLVL` and `_`.
- [x] Does `TZ` reach the script? If not, drop it from `run_preamble`, and record its absence
      as a Docker delta.
      Result: yes. It stays in `run_preamble`.

## Phase 2: build

- [x] `src/cowork_evals/data/cowork_env.sh`: POSIX sh, as designed above. The directory is the
      Docker build context. It reads `/etc/cowork_evals/keep_env.txt`.
- [x] `Dockerfile`: `COPY cowork_env.sh /usr/local/bin/cowork-env`, `chmod 0755`, and a `RUN`
      step that writes `/etc/claude-code/managed-settings.json`.
- [x] `Docker.digest` in `src/cowork_evals/docker/__init__.py`: hash `cowork_env.sh` beside
      `DOCKERFILE`, `REQUIREMENTS` and `INSTALLABLE`. Without this a changed script reuses a
      stale tag.
- [x] `DockerSection`: add `session_env` and `keep_env` as `tuple[str, ...]` with the
      defaults above, validated by `_env_names`. Refuse, at load, a name that is in two lists,
      and name the name and both keys.
- [x] `run_preamble`: add `TZ`, after `ENABLEMENT_ENV`. `run_argv`: mount the run's
      `keep_env.txt` read-only at `/etc/cowork_evals/keep_env.txt`. `Docker.run` writes that
      file before the container starts, and `--dry-run` writes nothing. Neither value is
      secret, so `--dry-run` prints both unredacted.
- [x] `write_env` in `src/cowork_evals/logs.py`: record `session_env` and `keep_env` beside
      `env_passthrough`, so a result says which list it ran under. Pass them from the caller in
      `cli.py` that already passes `env_passthrough`.
- [x] Fixture case `plugins/smoke/evals/plugin/session-env/`, modelled on `checked-file`:
      - `prompt.md` asks the model to run `env | cut -d= -f1 | sort > env.txt` and reply
        `DONE`. Names only: a model declined to write a full environment dump to disk.
      - `graders/writes-env-txt.md` is a `file_exists` grader on `env.txt`.
      - `checks/assertions.py` reads `env.txt` through `run.file` (`docs/checks.md`). It fails
        on any name outside `DockerSection().session_env`, `DockerSection().keep_env` and `_`,
        which `env` sets on itself. It uses the defaults, not a loaded config, because this
        repository sets none of the three keys. It also fails when `HOME`, `PATH` or `TMPDIR` is missing.
        The same case passes on the CoWork backend, because a session has only
        `session_env` names.
      Result: passes under `run --docker`. With `CLAUDECODE` added to `keep_env` it fails on `assertions.only_kept_names`.

## Phase 3: test

Match the existing tests: pytest, unit tests under `tests/unit/`, container and model tests
under `tests/integration/`, marked `integration`. Never mock and never skip (`CLAUDE.md`). The
script reads a fixed container path, so its tests run the real script in the image, over a keep
file mounted where a run mounts it and an environment set with `--env`.

- [x] `tests/integration/test_docker.py`, no model: `CLAUDECODE`, `CLAUDE_CODE_SESSION_ID`
      and an unlisted name are dropped, and a listed name is kept.
- [x] Same file: a listed name with no incoming value stays unset.
- [x] Same file: the five derived values, with `HOME=/x/abc` giving `USER=abc`.
- [x] `tests/unit/test_config.py`: the defaults load, a name in two lists is refused, and an
      invalid name is refused.
- [x] `tests/unit/test_docker.py`: `run_preamble` and its redacted form carry `TZ`, and
      `run_argv` mounts the keep file. A `keep_env` addition changes the keep file and not
      `digest`. `cowork_env.sh` is hashed into `digest`. The script reads the path the file
      is mounted at.
- [x] `tests/unit/test_logs.py`: `env.txt` carries both new rows.
- [x] `tests/integration/test_docker.py`, no model: the image names `cowork-env` in its managed
      settings, and a line in the keep file that is not a shell name is skipped.
- [x] `tests/integration/test_docker.py`, credentialled: the `session-env` case passes through
      the Docker backend, beside `test_the_smoke_case_passes_through_the_backend`.

## Phase 4: documentation

- [ ] `docs/docker.md`: a new section, "The session environment". It covers the mechanism,
      the three lists and their rule, the derived names, the phase 1 results, and the Docker
      deltas: the systemd names, and `TZ` if phase 1 dropped it. Add two rows for
      `session_env` and `keep_env` to the configuration table near the top.
- [ ] `docs/runtime.md`: one sentence after the variable table saying that a Docker run
      enforces this set and that `docker.session_env` holds it, with a link to `docker.md`.
- [ ] `docs/library.md`: `session_env` and `keep_env` hold names and never values, the same
      as `env_passthrough`.
- [ ] `src/cowork_evals/data/cowork_evals.example.yaml`: both keys, commented, with their
      defaults and the one-line rule for each.
- [ ] `docs/running_evals.md`: one sentence saying that a skill reading a variable outside the
      lists fails in Docker.
- [ ] `plugins/README.md`: the `session-env` row, and "four cases" changed to five.
- [ ] `src/cowork_evals/data/skills/cowork-evals/SKILL.md`: code in a session reads only the
      variables in `docs/runtime.md`, and never a `CLAUDE_CODE_*` variable.
- [ ] `plans/README.md`: the status of this plan.

## Phase 5: verify

- [ ] `scripts/lint.sh`.
- [ ] `scripts/test.sh`.
- [ ] `scripts/image.sh`, then `scripts/parity.sh`, with 0 failures.
- [ ] `scripts/test.sh -m integration -k docker`.
- [ ] `cowork_evals run --cowork plugins/smoke --case session-env` passes, which shows one
      case serves both backends.
- [ ] Manual: a one-case plugin whose skill runs `test -n "$CLAUDE_CODE_SESSION_ID"` and
      reports the exit status. It fails under `run --docker`, and it fails under `run --cowork`.
