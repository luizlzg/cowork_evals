# Plan: the container backend

Branch `feat/docker`, cut from `main`. Ten phases, one commit each.

## Scope

The container that reproduces the CoWork image, and the library that builds it, checks it
and runs the harness inside it. The design is [`../docs/docker.md`](../docs/docker.md) and
the inventory it matches is [`../docs/runtime.md`](../docs/runtime.md). What a backend plan
builds, and the one fixture firing at the end of it, are in [`README.md`](README.md).

| Builds                                     | Is                                                        |
| ------------------------------------------ | ----------------------------------------------------------- |
| `src/cowork_evals/data/`                   | The two requirements files, as package data               |
| `src/cowork_evals/env.py`                  | `.env`, and the `EVAL_*` settings over it                 |
| `src/cowork_evals/harness.py`              | The `claude plugin eval` argument list. The venv backend reuses it unchanged |
| `src/cowork_evals/docker/__init__.py`      | The digest, the argument lists, build, check and run      |
| `src/cowork_evals/docker/Dockerfile`       | What the build builds                                     |
| `src/cowork_evals/docker/probe.py`         | The parity probe, run inside the container                |
| `src/cowork_evals/docker/parity.py`        | The comparison, run on the host                           |
| `scripts/parity.sh`                        | The development task over those two                       |
| `plugins/smoke/`                           | The fixture the integration tier fires                    |
| `tests/unit/test_env.py`, `tests/unit/test_harness.py`, `tests/unit/test_docker.py`, `tests/unit/test_parity.py`, `tests/integration/test_docker.py` | [`../tests/README.md`](../tests/README.md) |

## Out of scope

| Not built                                                       | Belongs to              |
| ----------------------------------------------------------------- | ------------------------ |
| The `cowork_evals` command, `[project.scripts]`, option parsing  | `plan_cli.md`           |
| The run directory, `env.txt`, the `latest` symlink, pruning      | `plan_cli.md`           |
| The gate, and the case validator                                 | `plan_cli.md`           |
| The staged runtime and the venv backend                          | `plan_venv.md`          |
| Any eval over a shipped plugin, any suite, any cadence           | the consumer repository |

## Where this plan overrides the documents

[`../docs/docker.md`](../docs/docker.md) is the contract this plan builds to. On these four
points it is superseded, this plan wins, and phase 10 rewrites the page.

| That page says                                                    | Build this instead                                        |
| ------------------------------------------------------------------ | ---------------------------------------------------------- |
| The container authenticates with `ANTHROPIC_API_KEY`, and an unset key is a failed preflight | A logged-in Claude Code in a host directory this package owns, bind-mounted. No API key anywhere |
| The digest covers the Dockerfile, both requirements files and `CLAUDE_CODE_VERSION` | The platform is in it too. Without that an `arm64` and an `amd64` image share one tag |
| `pip install -r docs/data/requirements_installable.txt`           | The package data directory, from phase 1                   |
| Three measurement rows that need a graded suite                   | `Bash sandbox option needed` stays, filled by phase 9. The two smoke-case rows go: the wall clock and cost of a suite are measured when a suite is first run |

Why the credential is not an API key, since a later reader will ask:

| Route                          | Outcome                                                                  |
| ------------------------------- | -------------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY` in `.env`  | Rejected. A second credential to hold on a machine that has a logged-in Claude Code |
| Mounting the host `~/.claude`  | Rejected. On macOS the token is in the login Keychain, so that directory holds no credential to mount. Verified on the development host, 2026-09-08 |
| A directory this package owns  | Chosen. One explicit login, and a per-run container that keeps nothing     |

## Constraints

- Python 3.14 and ruff `target-version = "py314"`, with one exception: `docker/probe.py`
  runs on the container's 3.10 interpreter, imports the standard library only, and imports
  nothing from this package. [`../docs/library.md`](../docs/library.md).
- No dependency is added. The standard library and the `docker` CLI through `subprocess`.
- No credential is written into an image layer, printed, or logged.
- A function that builds an argument list is covered by asserting over the list. A function
  that starts a container is covered in the integration tier, against a real daemon.

## Phase 1: The requirements files become package data

A build reads them on a machine with no checkout, so they cannot stay under `docs/`.

- [ ] `git mv docs/data src/cowork_evals/data`.
- [ ] Point `scripts/cowork_venv.sh` at the new path, header comment included.
- [ ] Point `tests/unit/test_environments.py` at the new path.
- [ ] Add a test that both files resolve through `importlib.resources.files("cowork_evals")`,
      which is how a build reaches them from an installed wheel.
- [ ] Correct `docs/environments.md`, `docs/runtime.md`, `docs/docker.md`, and
      `docs/README.md`, which links both files, names `data/` among the three measured
      pages, and points its provenance table at `docs/data/`.
- [ ] Confirm the wheel carries them: `uv build`, then list the wheel.

## Phase 2: `.env` and the settings over it

`src/cowork_evals/env.py`. It reads one file and the process environment. The format and the
precedence are [`../docs/library.md`](../docs/library.md).

- [ ] Parse `.env`: `KEY=value`, `#` comments, blank lines, one matched pair of quotes
      around a value. No `export`, no expansion, no interpolation.
- [ ] Keep an unrecognised key.
- [ ] `setting(name, default)`: the process environment beats `.env` beats the default. A
      missing `.env` is not an error.
- [ ] Resolve `.env` from the working directory, and accept an explicit path.
- [ ] Read `EVAL_PLATFORM`, default `linux/arm64`, and the `EVAL_*` names in
      [`../docs/running_evals.md`](../docs/running_evals.md).
- [ ] Never log a value and never put one in an exception message.

## Phase 3: The Dockerfile

`src/cowork_evals/docker/Dockerfile`. Every version it installs is a row in
[`../docs/runtime.md`](../docs/runtime.md) or in the four-source table in
[`../docs/docker.md`](../docs/docker.md).

- [ ] `FROM ubuntu:22.04`, with `ARG CLAUDE_CODE_VERSION` and `ARG TARGETARCH`.
- [ ] One apt layer: the document, image, media and CLI tooling, the nine dist-packages
      suppliers, the Ubuntu font stack, and `bubblewrap`.
- [ ] `pip install --upgrade pip==25.3`, then `pip install -r requirements_installable.txt`
      from the build context.
- [ ] LibreOffice 26.2.5.2 from the upstream deb set, mapping `TARGETARCH` to the kernel
      architecture the tarball is named by: `arm64` to `aarch64`, `amd64` to `x86-64`.
- [ ] Put the LibreOffice `program` directory on `PYTHONPATH`, so `import uno` resolves.
- [ ] Node.js from NodeSource `node_22.x`, pinned to `22.23.2-1nodesource1`.
- [ ] `@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}` as the one added npm global.
- [ ] uv 0.12.3 from the Astral installer.
- [ ] Create the container home and `/work` world-writable, for a uid with no passwd entry.
- [ ] Copy no source tree, install no credential, and add no `.dockerignore`.

## Phase 4: The digest, the build and the check

`src/cowork_evals/docker/__init__.py`. A `Docker` object holding frozen configuration and
doing no work at construction, so `Docker().digest` works on a machine with no daemon.

- [ ] `Docker(*, platform=None, claude_code_version=None, home=None)`, each resolved from
      `env.py` and falling back to the documented default.
- [ ] `digest`: the first 12 characters of the sha256 over the Dockerfile, both requirements
      files, the resolved `CLAUDE_CODE_VERSION` and the resolved platform.
- [ ] `tag`, `cowork-evals:<digest>`. A build also tags `cowork-evals:latest`.
- [ ] `DockerError`, carrying a code. Nothing returns an error code or calls `sys.exit`.
- [ ] `build_argv()`: `-f` at the Dockerfile, the context at the package data directory,
      `--platform`, both tags and the build argument.
- [ ] `build()`: run it, stream the output, raise on a non-zero exit.
- [ ] `check()`: the unmet conditions in order, each with the command that fixes it. The
      daemon reachable, the image present at the current digest, a credential file present.
      An empty list means ready. It writes nothing and builds nothing.
- [ ] `login_argv()`: the interactive container a developer logs in through once.

## Phase 5: The harness argument list

`src/cowork_evals/harness.py`. One place builds the `claude plugin eval` command line for
both Claude Code backends. The pinned flags are
[`../docs/running_evals.md`](../docs/running_evals.md).

- [ ] A frozen `RunOptions`, loaded from the `EVAL_*` settings, an explicit value beating
      the setting.
- [ ] `eval_argv(target, output_dir, options)`: every pinned flag, and nothing that is
      neither pinned nor optioned.
- [ ] Put the target ahead of `--tag` and `--allow-tools`, which are variadic and swallow a
      trailing target.
- [ ] Never emit `--json`. Always emit `--no-publish`, `--no-scaffold`, `--verbose`,
      `--threshold 0` and `--ablation none`, with no way to override the last two.
- [ ] Put `--debug-file` before `plugin`, and never a bare `--debug`, which swallows the
      subcommand name as its filter.

## Phase 6: The run argument list, and the backend function

Still `src/cowork_evals/docker/__init__.py`. It wraps phase 5's list in a container.

- [ ] `run_argv(plugin_root, log_dir, options)`: `docker run --rm`, the platform, the host
      uid and gid, `HOME`, `--security-opt seccomp=unconfined`, and phase 5's list as the
      command.
- [ ] The plugin root read-only, the run's log directory read-write, `--output-dir` at the
      log mount, and the configuration directory and the state file beside it from the host
      directory this package owns. Nothing else from the host.
- [ ] Pass `CLAUDE_CODE_WALNUT_SPIRE` with `--env`: the process in the container is the
      harness itself, with no wrapper to export it.
- [ ] `run(case_path, output_dir)`: run the container and return the path to the
      `aggregate-result.json` it left behind. Raise when it produced none.
- [ ] Name no run directory, write no `latest` symlink, prune nothing, decide nothing.

## Phase 7: The probe, the comparison and `scripts/parity.sh`

Only two things are compared mechanically, because the delta table in
[`../docs/docker.md`](../docs/docker.md) fails on only two: the pins, against
`data/requirements.txt`, and the five tools recorded as absent. Everything else the probe
reports is printed for a reader. No page under `docs/` is parsed.

- [ ] `docker/probe.py`: one JSON document on stdout holding the OS release, the
      architecture, the version of each tool in [`../docs/runtime.md`](../docs/runtime.md),
      `import uno`, `unoserver --version`, the font family count and the full `pip freeze`.
      3.10 syntax, standard library only.
- [ ] `docker/parity.py`: apply the delta table exactly. Exit 1 on a missing or moved pin,
      on one of the five absent tools being present, and on `import uno` failing. Print an
      extra package or a differing tool version without failing.
- [ ] Report the platform the probe actually ran on, so an x86 run is never read as aarch64.
- [ ] `scripts/parity.sh`: run the probe in the container with the probe bind-mounted
      read-only, then the comparison on the host. It installs nothing into the image.
- [ ] `tests/unit/test_parity.py`: recorded probe documents under `tests/data/`, one per row
      of the delta table. No container starts.

## Phase 8: The fixture

`plugins/smoke/`, per [`../plugins/README.md`](../plugins/README.md). The standard layout,
so it exercises discovery.

- [ ] One skill that shells out to `python3 -V` and reports what it got.
- [ ] One case in the format at [`../docs/eval_format.md`](../docs/eval_format.md), graded
      structurally: the skill fired, and the reported version is 3.10.
- [ ] `runs: 1` written out.

## Phase 9: The integration tier, and the measurements

`tests/integration/test_docker.py`. It needs a running daemon and a logged-in configuration
directory. A missing precondition fails the test and never skips it.

- [ ] Build the image, with a timeout that fits a cold build. The 300 second default in
      `pyproject.toml` does not.
- [ ] Assert the digest tag exists and a second build is a no-op.
- [ ] Run the probe and assert the comparison passes.
- [ ] Assert the plugin mount refuses a write, the log mount accepts one, and a file written
      into the log mount is owned by the host uid and gid.
- [ ] Fire `plugins/smoke/` through `run()` and assert the result document says the case
      passed.
- [ ] Record in `docs/docker.md`: the platform, the image size, the cold and warm build
      times, the pin mismatches, the extra packages, the non-Python deltas, the font family
      count, `import uno`, the uid mapping option needed, the Bash sandbox option needed,
      and the installed Claude Code version.
- [ ] Record whether a first launch in a fresh configuration directory blocks a
      non-interactive run. If it does, the login step seeds the state file beside the
      configuration directory and `docs/docker.md` says so. If it does not, the run mounts
      the configuration directory alone.

If bubblewrap is refused under `seccomp=unconfined`, apply the documented fallback,
`--cap-add SYS_ADMIN --security-opt apparmor=unconfined`, and record which was needed. If
both are refused the container cannot grant `Bash`, `docs/docker.md` records that as a
property of this host, and every other box here still stands.

## Phase 10: Documentation

Nothing durable may survive only in this file.

- [ ] `docs/docker.md`: replace the credentials section with the login prerequisite and the
      directory it uses, add the platform to the digest, correct the two requirements paths,
      drop the two smoke-case rows, and fill every remaining measurement from phase 9.
- [ ] `docs/library.md`: add the new modules to the ships table, add the configuration
      directory to the state table, and correct the `.env` text, which no longer carries a
      credential for this backend.
- [ ] `docs/cli.md`: correct the `--docker` preflight row, which names `ANTHROPIC_API_KEY`,
      and add the login to `setup`.
- [ ] `docs/running_evals.md`: mark the container backend, its Dockerfile, `parity.sh` and
      `plugins/smoke/` built.
- [ ] `docs/approaches.md`: correct anything the credential change makes false.
- [ ] `docs/environments.md`: correct the sentence placing both requirements files under
      `docs/data/`.
- [ ] `docs/README.md`: drop the `data/` rows, correct the provenance table, and correct the
      sentence saying a plan is deleted once implemented, which [`README.md`](README.md)
      contradicts.
- [ ] `scripts/README.md`: turn the `parity.sh` note into a row.
- [ ] `tests/README.md`: a row per new test file, and the integration tier's new
      preconditions.
- [ ] `plugins/README.md`: mark `smoke` built.
- [ ] `README.md`: add the container login to the sentence listing what a caller needs, and
      correct the Contributing block, whose integration line describes that tier as CoWork
      only.
- [ ] Re-read every touched page for a statement this plan made false.
- [ ] `plans/README.md`: mark this plan `implemented`.
