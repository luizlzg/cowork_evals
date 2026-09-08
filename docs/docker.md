# Docker

A container that reproduces the CoWork image, so an eval run exercises the OS, the
architecture, LibreOffice, ImageMagick, pandoc, tesseract, the CLI utilities and the font
stack, not only the Python interpreter and its wheels.

The image inventory this container has to match is [runtime.md](runtime.md). The eval system
around it is [running_evals.md](running_evals.md) and the command that reaches it is
[cli.md](cli.md). The cheaper alternative is [environments.md](environments.md).

Design. Nothing here is built and the measurements at the end are not taken. What is built
is the status table in [running_evals.md](running_evals.md).

## Usage

```bash
cowork_evals setup --docker                                   # build for EVAL_PLATFORM
cowork_evals check --docker                                   # daemon, image digest, credential
cowork_evals run --docker path/to/plugin/evals/<skill>        # one skill, in the container
cowork_evals run --docker path/to/repo                        # every plugin, in the container

scripts/parity.sh                                             # development: probe the image, compare
```

`run --docker` takes the same path argument and the same options as every other backend and
writes the same logs. `--dry-run` prints the `docker run` argument list one argument per line
and starts nothing. See [cli.md](cli.md).

`scripts/parity.sh` is a development task for this repository, not part of the command. It
is how the image is proved to match [runtime.md](runtime.md) before a release.

## Why the image can be close

The CoWork image is Ubuntu 22.04.5 (jammy), and every recorded non-Python version is the
version jammy ships: pandoc 2.9.2.1, tesseract 4.1.1, ImageMagick 6.9.11-60, ffmpeg 4.4.2,
poppler-utils 22.02.0, ghostscript 9.55.0, qpdf 10.6.3, git 2.34.1, OpenJDK 11.0.31,
Python 3.10.12. `apt-get install` from jammy therefore reproduces them exactly.

Four things do not come from jammy apt, and each has one source:

| Component        | Recorded | jammy apt | Source                                                             |
| ---------------- | -------- | --------- | ------------------------------------------------------------------ |
| LibreOffice      | 26.2.5.2 | 7.3       | `LibreOffice_26.2.5.2_Linux_<arch>_deb.tar.gz`, upstream archive   |
| Node.js          | 22.23.2  | 12        | NodeSource `node_22.x`, pinned to `22.23.2-1nodesource1`           |
| pip              | 25.3     | 22.0.2    | `pip install --upgrade pip==25.3`                                  |
| uv               | 0.12.3   | absent    | The Astral installer, pinned to 0.12.3                             |

Both upstream sources are present for aarch64 and carry the recorded versions, checked
2026-09-03.

## The Python pins

The two requirements files, and the split between them, are
[environments.md](environments.md). In the image they come from two places, not one.

| Pins | Source                                                 |
| ---- | ------------------------------------------------------ |
| 127  | `pip install -r docs/data/requirements_installable.txt` |
| 9    | apt, as Ubuntu system packages                         |

The nine live in `/usr/lib/python3/dist-packages` and are not on PyPI at those versions.
`command-not-found==0.3` and `unattended-upgrades==0.1` are egg versions carried inside apt
packages, unrelated to the deb version, which is the evidence that the recorded freeze came
from a system interpreter. `pip install -r docs/data/requirements.txt` fails on them and
must never be run.

| Pin                          | apt package           | jammy deb version   |
| ---------------------------- | --------------------- | ------------------- |
| `command-not-found==0.3`     | `command-not-found`   | 22.04.0             |
| `dbus-python==1.2.18`        | `python3-dbus`        | 1.2.18-3build1      |
| `distro-info==1.1+ubuntu0.2` | `python3-distro-info` | 1.1ubuntu0.2        |
| `pipx==1.0.0`                | `pipx`                | 1.0.0-1             |
| `PyGObject==3.42.1`          | `python3-gi`          | 3.42.1-0ubuntu1     |
| `pyinotify==0.9.6`           | `python3-pyinotify`   | 0.9.6-1.3           |
| `python-apt==2.4.0+ubuntu4.1`| `python3-apt`         | 2.4.0ubuntu4.1      |
| `ufw==0.36.1`                | `ufw`                 | 0.36.1-4ubuntu0.1   |
| `unattended-upgrades==0.1`   | `unattended-upgrades` | 2.8ubuntu1          |

`pip freeze` inside the built image reports every pin, because pip sees `dist-packages`.
That is the fidelity gain over the mirror, which cannot hold the nine.

Measured on `ubuntu:22.04` `linux/arm64` on 2026-09-03, a snapshot: apt installs the nine
above, `python3 -V` reports 3.10.12, and `pip freeze` reports all nine at the recorded pin
strings exactly. Jammy's python3.10 carries no `EXTERNALLY-MANAGED` marker, so pip installs
into the system interpreter without a flag.

## unoserver and the UNO bindings

`unoserver==3.7` is one of the 127 pins and needs `import uno` from the interpreter it runs
under. Jammy's `python3-uno` is 1:7.3.7, tied to the `libreoffice` 1:7.3.7 it ships with, so
it cannot supply the bindings against 26.2.
The upstream deb set installs pyuno under its own `program` directory, so the image puts
that directory on `PYTHONPATH`.

Parity checks `import uno` and `unoserver --version`, because document conversion is the
capability the container exists to prove. A `soffice --version` check alone passes while
conversion is broken.

## Architecture

The recorded image is `aarch64`. `--platform linux/arm64` matches it natively on an ARM Mac
and needs qemu emulation elsewhere, which is correct but several times slower.

The build takes `--platform` from `EVAL_PLATFORM`, default `linux/arm64`. The parity report
records the platform actually used, so an x86 run is never mistaken for an aarch64 one.

The upstream LibreOffice tarball is named by the kernel architecture, not by Docker's. The
Dockerfile maps `TARGETARCH`: `arm64` to `aarch64`, `amd64` to `x86-64`. NodeSource and the
uv installer detect the architecture themselves and need no mapping.

## The build context

The build context is the package's data directory, the two requirements files and nothing
else, and the Dockerfile is passed with `-f`. Nothing else is copied into a layer: the
plugins and the logs are mounts, made at run time, and no code from this package is ever
installed into the image.

A two-file context needs no `.dockerignore`, transfers nothing, and cannot put a working
tree into a public image layer. See [library.md](library.md).

## The Claude Code CLI

The harness is not part of the CoWork image, so it is not in the inventory above. The
container installs it as a global npm package, `@anthropic-ai/claude-code`, at the version
in the `CLAUDE_CODE_VERSION` build argument. The default is 2.1.259, the version
[plugin_eval.md](plugin_eval.md) is written against.

It is one deliberate delta against [runtime.md](runtime.md), which records corepack and npm
as the only npm globals. Parity does not read npm globals and does not fail on it. No other
global is added.

## Credentials

The container authenticates with `ANTHROPIC_API_KEY`, passed at run time with
`--env ANTHROPIC_API_KEY`. The value comes from the environment or from `.env`, which is
never committed. See [library.md](library.md).

- Never bake a credential into an image layer.
- Never mount the host `~/.claude` or `~/.claude.json`. The harness copies credentials into
  its own per-run sandbox, and mounting the host profile puts a live OAuth token inside a
  container that runs author-supplied prompts.
- API key auth cannot publish a report to claude.ai. The runner passes `--no-publish`
  anyway, so nothing changes.

An unset `ANTHROPIC_API_KEY` is a failed preflight, so it exits 3 and names the variable.
See [cli.md](cli.md).

`CLAUDE_CODE_WALNUT_SPIRE` is passed in with `--env` alongside the credential, because the
process inside the container is `claude plugin eval` itself with no wrapper in the way. A
shell opened in the container by hand must export it. See
[plugin_eval.md](plugin_eval.md).

## Mounts

| Host path            | Container path        | Mode | Why                                            |
| -------------------- | --------------------- | ---- | ---------------------------------------------- |
| the plugin root      | `/work/plugin`        | ro   | The plugin under test                          |
| the run's log dir    | `/work/logs`          | rw   | The only path the run may write outside `/tmp` |

Read-only everywhere except the log directory. A case that writes into the consumer's
checkout is a defect and must fail rather than succeed quietly. `--output-dir` points at
`/work/logs`, so the harness's own output does not land in the plugin directory and the
read-only mount does not fail a correct run.

The container holds nothing from this package. The `cowork_evals` process stays on the host,
builds this argument list, names the run directory, writes the `latest` symlink, prunes old
runs, records `env.txt` and runs the gate over the result document the container leaves
behind. One place does all of that for all three backends. See [library.md](library.md).

Only the run's own log directory is mounted, not the whole log root, because the host owns
every other path under it.

The container runs with the host user's numeric uid and gid, so log files are not
root-owned. That uid has no passwd entry, so `HOME` is set explicitly to a writable path
under `/tmp`, created in the image world-writable.

A uid with no passwd entry is the one thing here that can stop the CLI: Node's
`os.userInfo()` raises rather than returning a stub. The fallback is to run as root and
`chown -R` `/work/logs` to the host uid and gid on the way out, which keeps the ownership
property that the uid mapping exists for. The measurement below records which was needed.

The CoWork mirror is neither mounted nor built in the image: system `python3` is already 3.10
with the full pin set. The mirror rule holds unchanged here and is stated in
[running_evals.md](running_evals.md).

## The Bash sandbox

Granting `Bash` turns on the OS sandbox, and a host with no sandbox backend refuses the run
rather than running unconfined. See [plugin_eval.md](plugin_eval.md).

The image installs `bubblewrap`, 0.6.1 in jammy, and the container runs with
`--security-opt seccomp=unconfined` so unprivileged user namespaces are not filtered. The
fallback, if that is still refused, is
`--cap-add SYS_ADMIN --security-opt apparmor=unconfined`.

A container that cannot grant `Bash` cannot run a case that shells out, which is most of
them. The measurement below records which option was needed.

## Image tagging

The image is tagged `cowork-evals:<digest>` and also `cowork-evals:latest`, where `<digest>`
is the first 12 characters of the sha256 of the Dockerfile, both requirements files and the
resolved `CLAUDE_CODE_VERSION`.
Every build input is in the digest, including the build argument, so two CLI versions cannot
share one tag and no change can be served from a stale image.

## Parity

`scripts/parity.sh` is the development task: it runs one probe inside the container, then
compares the JSON the probe writes against [runtime.md](runtime.md) and
`data/requirements.txt`. It checks the OS release, the architecture, every version in the
runtime tables, `import uno`, the font family count, and the full `pip freeze`.

It is a shell script like every other task under [../scripts/](../scripts/), and the
comparison runs on the host. Nothing from this package is installed into the image to do it.

| Delta                                          | Result                 | Why                                                            |
| ---------------------------------------------- | ---------------------- | -------------------------------------------------------------- |
| A pin is missing or at a different version     | exit 1                 | It changes what a skill can import                             |
| A package is installed that is not a pin       | printed, does not fail | A transitive dependency of the tooling is not a fidelity break |
| A non-Python tool version differs              | printed, does not fail | A jammy point release moves a patch version and must not block |
| A tool recorded as not present is present      | exit 1                 | A skill can call it here and not in a session                  |
| `import uno` fails                             | exit 1                 | unoserver and headless conversion are broken                   |

The tools recorded as not present are `wkhtmltopdf`, `weasyprint`, `exiftool`, `docker` and
the `sqlite3` CLI.

The probe writes one JSON document. `tests/test_parity.py` asserts over recorded copies of
it under `tests/data/`, so the tests start no container.

## What the container still does not reproduce

Stated once so no reader assumes otherwise: the CoWork model routing, the admin-applied
enterprise prompt, the CoWork MCP servers, the `/sessions/<session>` filesystem layout, the
vsock host RPC, and the session lifecycle. It is an image, not the deployed stack. For
those, see [cowork_driver.md](cowork_driver.md).

## Measurements

| Measurement                         | Value            |
| ----------------------------------- | ---------------- |
| Platform built                      | not yet measured |
| Image size                          | not yet measured |
| Build time, cold                    | not yet measured |
| Build time, warm                    | not yet measured |
| Python pin mismatches               | not yet measured |
| Extra Python packages               | not yet measured |
| Non-Python deltas                   | not yet measured |
| Font families in the image          | not yet measured |
| `import uno` from system python3    | not yet measured |
| Bash sandbox option needed          | not yet measured |
| uid mapping option needed           | not yet measured |
| Claude Code CLI version installed   | not yet measured |
| Smoke case, container, wall clock   | not yet measured |
| Smoke case, container, `costUsd`    | not yet measured |
