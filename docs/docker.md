# Docker

A container that reproduces the CoWork image, so an eval run exercises the OS, the
architecture, LibreOffice, ImageMagick, pandoc, tesseract, the CLI utilities and the font
stack, not only the Python interpreter and its wheels.

The image inventory this container has to match is [runtime.md](runtime.md). The eval system
around it is [running_evals.md](running_evals.md) and the command that reaches it is
[cli.md](cli.md). The cheaper alternative is [environments.md](environments.md).

The container, the image digest, the argument lists, the parity probe and the fixture are
built. The `cowork_evals` command over them is not: today the image is built by
`scripts/image.sh` and a run goes through `cowork_evals.docker.Docker.run`. What is built
is the status table in [running_evals.md](running_evals.md).

## Usage

```bash
cowork_evals setup --docker                                   # build for EVAL_PLATFORM
cowork_evals check --docker                                   # daemon, image digest, credential
cowork_evals run --docker path/to/plugin/evals/<skill>        # one skill, in the container
cowork_evals run --docker path/to/repo                        # every plugin, in the container

scripts/image.sh                                              # development: build for EVAL_PLATFORM
scripts/image.sh --check                                      # development: the digest is present, no writes
scripts/parity.sh                                             # development: probe the image, compare
```

`run --docker` takes the same path argument and the same options as every other backend and
writes the same logs. `--dry-run` prints the `docker run` argument list one argument per line
and starts nothing. See [cli.md](cli.md).

`scripts/image.sh` and `scripts/parity.sh` are development tasks for this repository and are
not part of the command. `parity.sh` is how the image is proved to match
[runtime.md](runtime.md) before a release.

## Why the image can be close

The CoWork image is Ubuntu 22.04.5 (jammy), and every recorded non-Python version is the
version jammy ships: pandoc 2.9.2.1, tesseract 4.1.1, ImageMagick 6.9.11-60, ffmpeg 4.4.2,
poppler-utils 22.02.0, ghostscript 9.55.0, qpdf 10.6.3, git 2.34.1, OpenJDK 11.0.31,
Python 3.10.12. `apt-get install` from jammy therefore reproduces them, up to the point
releases jammy has taken since the capture: the measurement below found one, Java at
11.0.32.

Four things do not come from jammy apt, and each has one source:

| Component        | Recorded | jammy apt | Source                                                             |
| ---------------- | -------- | --------- | ------------------------------------------------------------------ |
| LibreOffice      | 26.2.5.2 | 7.3       | `LibreOffice_26.2.5_Linux_<arch>_deb.tar.gz`, upstream archive     |
| Node.js          | 22.23.2  | 12        | NodeSource `node_22.x`, pinned to `22.23.2-1nodesource1`           |
| pip              | 25.3     | 22.0.2    | `pip install --upgrade pip==25.3`                                  |
| uv               | 0.12.3   | absent    | The Astral installer, pinned to 0.12.3                             |

Both upstream sources are present for aarch64 and carry the recorded versions, checked
2026-09-08. The upstream release is named `26.2.5` in the path and the file name, and
`soffice --version` reports the fourth component: 26.2.5.2.

## The Python pins

The two requirements files, and the split between them, are
[environments.md](environments.md). In the image they come from two places, not one.

| Pins | Source                                        |
| ---- | --------------------------------------------- |
| 127  | `pip install -r requirements_installable.txt` |
| 9    | apt, as Ubuntu system packages                |

The nine live in `/usr/lib/python3/dist-packages` and are not on PyPI at those versions.
`command-not-found==0.3` and `unattended-upgrades==0.1` are egg versions carried inside apt
packages, unrelated to the deb version, which is the evidence that the recorded freeze came
from a system interpreter. `pip install -r requirements.txt` fails on them and must never
be run.

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

The upstream LibreOffice archive is named by the kernel architecture, not by Docker's, and
spells `amd64` two ways. The Dockerfile maps `TARGETARCH` to both.

| `TARGETARCH` | Archive directory | File name |
| ------------ | ----------------- | --------- |
| `arm64`      | `aarch64`         | `aarch64` |
| `amd64`      | `x86_64`          | `x86-64`  |

NodeSource and the uv installer detect the architecture themselves and need no mapping.

## The build context

The build context is the package's data directory, the two requirements files and nothing
else, and the Dockerfile is passed with `-f`. Nothing else is copied into a layer: the
plugins and the logs are mounts, made at run time, and no code from this package is ever
installed into the image.

A two-file context needs no `.dockerignore`, transfers nothing, and cannot put a working
tree into a public image layer. See [library.md](library.md).

## A host whose network inspects TLS

Three of the four upstream sources are fetched over HTTPS by the build:
`download.documentfoundation.org`, `deb.nodesource.com` and `astral.sh`. On a host behind
a TLS-inspecting proxy the container has no issuer for any of them and the build fails at
the first fetch. PyPI and the npm registry were not intercepted on the host measured below,
so the pins and the CLI install either way.

The build takes an extra root CA from `SSL_CERT_FILE`, which such a host already sets for
its own tooling. It is passed as a BuildKit secret, never through the build context, and
the Dockerfile installs it into the image CA store. Both the fetches above and the Claude
Code CLI inside the container then trust it: `claude.ai` is intercepted on that host too, so
the login route needs it as much as the build does.

| Layer                     | Reads it from                                    |
| ------------------------- | ------------------------------------------------ |
| `build_argv`              | `--secret id=extra_ca,src=$SSL_CERT_FILE`        |
| The Dockerfile            | `/run/secrets/extra_ca`, once, into the CA store |
| `run_argv`, `login_argv`  | `--env NODE_EXTRA_CA_CERTS`, because Node carries its own root store |

`SSL_CERT_FILE` unset, or naming a file that is not there, is a host that does not
intercept, and nothing is passed. The certificate itself never enters this repository: the
public repository rule in [../README.md](../README.md) covers it, and a corporate root names
the employer.

The image digest does not cover it. It is a property of the host that built the image, not
of the inventory the image reproduces.

## How Docker is driven

The `cowork_evals` process runs the `docker` CLI through `subprocess`. It does not use
`docker-py`, which is the usual way to reach Docker from Python.

| Fact                                                                                   | Consequence                                        |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| A cross-architecture `--platform` build goes through buildx. buildx is the CLI's builder; `docker-py` drives the daemon's classic builder | The SDK is weakest on the one build this page exists for |
| `docker context` resolves which daemon to talk to and the CLI reads it. `docker-py` takes `DOCKER_HOST`, and Rancher Desktop on its containerd backend exposes no Docker API socket at all | The CLI reaches both daemons [cli.md](cli.md) names |

Using the SDK for `run` and the CLI for `build` would be two mechanisms for one job.

What the SDK gives back is typed errors instead of an exit code, and no argument quoting.
The second is worth little here: `--dry-run` prints the argument list a run would use, so
that list is built either way. See [cli.md](cli.md).

## The Claude Code CLI

The harness is not part of the CoWork image, so it is not in the inventory above. The
container installs it as a global npm package, `@anthropic-ai/claude-code`, at the version
in the `CLAUDE_CODE_VERSION` build argument. The default is 2.1.259, the version
[plugin_eval.md](plugin_eval.md) is written against, and `CLAUDE_CODE_VERSION` in the
environment or in `.env` moves it. It is in the image digest, so two versions cannot share
one tag.

It is one deliberate delta against [runtime.md](runtime.md), which records corepack and npm
as the only npm globals. Parity does not read npm globals and does not fail on it. No other
global is added.

## Credentials

Two routes, because a laptop and a runner cannot authenticate the same way. A run takes
whichever is available, and the key wins when both are.

| Route                | For                                          | How                                            |
| -------------------- | -------------------------------------------- | ---------------------------------------------- |
| `ANTHROPIC_API_KEY`  | a CI runner, or any host with no interactive terminal | passed with `--env`. Nothing is mounted |
| A mounted login      | a developer's machine                        | mounted read-write from the host, below        |

The login happens once, in an interactive container that `setup --docker` starts when
neither route is available, and it writes a configuration directory this package owns:

| Host path                                   | Holds                                                |
| ------------------------------------------- | ---------------------------------------------------- |
| `~/.cache/cowork_evals/claude/.claude/`     | the configuration directory, including `.credentials.json` |
| `~/.cache/cowork_evals/claude/.claude.json` | the CLI state file                                   |

Both are mounted into the container home, read-write: the CLI refreshes its token and
rewrites its state file on every start. They are the only host paths a run mounts besides
the plugin and the log directory, and the container keeps nothing else. A run that uses the
key mounts neither.

- Never bake a credential into an image layer.
- Never mount the host `~/.claude` or `~/.claude.json`. That is the developer's own live
  session, inside a container that runs author-supplied prompts. The directory above is a
  separate login this package owns and can revoke on its own.
- A claude.ai login can publish a report. `--no-publish` is pinned, so none is published.
  See [running_evals.md](running_evals.md).
- `ANTHROPIC_API_KEY` comes from the environment or from `.env`, which is never committed.
  See [library.md](library.md).

Neither route available is a failed preflight, so it exits 3 and names both. See
[cli.md](cli.md).

`CLAUDE_CODE_WALNUT_SPIRE` is passed in with `--env`, because the process inside the
container is `claude plugin eval` itself with no wrapper in the way. A shell opened in the
container by hand must export it. See [plugin_eval.md](plugin_eval.md).

## Mounts

| Host path                                   | Container path        | Mode | Why                                            |
| ------------------------------------------- | --------------------- | ---- | ---------------------------------------------- |
| the plugin root                             | `/work/plugin`        | ro   | The plugin under test                          |
| the run's log dir                           | `/work/logs`          | rw   | The only path the run may write outside `/tmp` |
| `~/.cache/cowork_evals/claude/.claude/`     | `$HOME/.claude`       | rw   | The login, above                               |
| `~/.cache/cowork_evals/claude/.claude.json` | `$HOME/.claude.json`  | rw   | The login, above                               |

The plugin root is the nearest ancestor of the path argument holding
`.claude-plugin/plugin.json`, and the target the harness is given inside the container is
that path relative to it, under `/work/plugin`. A path with no plugin root above it is an
error.

Read-only everywhere except the log directory and the two credential paths. A case that
writes into the consumer's checkout is a defect and must fail rather than succeed quietly.
`--output-dir` points at `/work/logs`, so the harness's own output does not land in the
plugin directory and the read-only mount does not fail a correct run.

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
`os.userInfo()` raises rather than returning a stub. It does not on the image measured
below, so `--user <uid>:<gid>` is what the backend passes and the documented fallback, root
plus a `chown -R` of `/work/logs` on the way out, is not used.

The CoWork mirror is neither mounted nor built in the image: system `python3` is already 3.10
with the full pin set. The mirror rule holds unchanged here and is stated in
[running_evals.md](running_evals.md).

## The Bash sandbox

Granting `Bash` turns on the OS sandbox, and a host with no sandbox backend refuses the run
rather than running unconfined. See [plugin_eval.md](plugin_eval.md).

The image installs `bubblewrap`, 0.6.1 in jammy, and the container runs with
`--security-opt seccomp=unconfined` so unprivileged user namespaces are not filtered.
`bwrap` comes up under it on the host measured below, so the documented fallback,
`--cap-add SYS_ADMIN --security-opt apparmor=unconfined`, is not used.

A container that cannot grant `Bash` cannot run a case that shells out, which is most of
them.

## Image tagging

The image is tagged `cowork-evals:<digest>`, where `<digest>` is the first 12 characters of
the sha256 of the Dockerfile, both requirements files, the resolved `CLAUDE_CODE_VERSION`
and the resolved platform. Without the platform an `arm64` and an `amd64` image share one
tag. Every build input is in the digest, including the build argument, so two CLI versions
cannot share one tag and no change can be served from a stale image.

There is no `latest` tag. Nothing reads one: `run` and `check` resolve the digest tag, and a
`latest` left behind by an older build points at an image no command would choose.

## Parity

`scripts/parity.sh` is the development task: it runs one probe inside the container, with
the probe bind-mounted read-only, then compares what the probe wrote. It checks the OS
release, the architecture, every version in the runtime tables, `import uno`, the font
family count, and the full `pip freeze`.

It is a shell script like every other task under [../scripts/](../scripts/), and the
comparison runs on the host. Nothing from this package is installed into the image to do it.

No page under `docs/` is parsed. The pins come from the shipped `requirements.txt`, and the
non-Python versions are a table in `parity.py` that cites [runtime.md](runtime.md). A change
to that page is carried into the table by hand, in the same commit.

| Delta                                          | Result                 | Why                                                            |
| ---------------------------------------------- | ---------------------- | -------------------------------------------------------------- |
| A pin is missing or at a different version     | exit 1                 | It changes what a skill can import                             |
| A package is installed that is not a pin       | printed, does not fail | A transitive dependency of the tooling is not a fidelity break |
| A non-Python tool version differs              | printed, does not fail | A jammy point release moves a patch version and must not block |
| A tool recorded as not present is present      | exit 1                 | A skill can call it here and not in a session                  |
| `import uno` fails                             | exit 1                 | unoserver and headless conversion are broken                   |

The tools recorded as not present are `wkhtmltopdf`, `weasyprint`, `exiftool`, `docker` and
the `sqlite3` CLI.

The probe writes one JSON document. `tests/unit/test_parity.py` asserts over recorded copies
of it under `tests/data/docker/`, one per row of the table above, so the tests start no
container.

## What the container still does not reproduce

Stated once so no reader assumes otherwise: the CoWork model routing, the admin-applied
enterprise prompt, the CoWork MCP servers, the `/sessions/<session>` filesystem layout, the
vsock host RPC, and the session lifecycle. It is an image, not the deployed stack. For
those, see [cowork_driver.md](cowork_driver.md).

## Measurements

Taken on one host and true of that host. Each is a snapshot, dated, with the host written as
its OS, architecture and container runtime, never as a machine name. A reader on another
platform re-runs `scripts/parity.sh` and the integration tier rather than assuming these.

| Measurement                       | Value                                                   |
| --------------------------------- | ------------------------------------------------------- |
| Captured on                       | 2026-09-08                                              |
| Host                              | macOS on aarch64, Rancher Desktop, dockerd 29.5.3       |
| Platform built                    | `linux/arm64`, native                                   |
| Image size                        | 3.72 GB                                                 |
| Build time, cold                  | 5 min 30 s, `--no-cache`, native, over a proxy           |
| Build time, warm                  | under a second: the digest is present, so nothing runs  |
| Python pin mismatches             | 0 of 136                                                |
| Extra Python packages             | 0                                                       |
| Non-Python deltas                 | Java 11.0.32 against the recorded 11.0.31, a jammy point release |
| Font families in the image        | 111 against the recorded 118                            |
| `import uno` from system python3  | yes                                                     |
| Bash sandbox option needed        | `--security-opt seccomp=unconfined`. `bwrap` comes up under it |
| uid mapping option needed         | `--user <uid>:<gid>`. `claude --version` runs under a uid with no passwd entry |
| Claude Code CLI version installed | 2.1.259                                                 |
| Extra root CA needed              | yes on this host. Three upstream hosts inspect TLS      |

All 136 pins are present at the recorded version, the nine from apt included, so the
fidelity gain over the mirror is real. The two deltas above are printed by
`scripts/parity.sh` and neither fails it.

The font count is 7 families short. The image installs the Noto fallback faces rather than
`fonts-noto-core`, which alone adds 192 families over the record, so the remaining gap is
between one jammy font package and another rather than between two font stacks.
