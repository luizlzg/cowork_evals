# Docker

A container that reproduces the CoWork image, so an eval run exercises the OS, the
architecture, LibreOffice, ImageMagick, pandoc, tesseract, the CLI utilities and the font
stack, not only the Python interpreter and its wheels.

The image inventory this container has to match is [runtime.md](runtime.md). The runner it
hosts is [running_evals.md](running_evals.md). The cheaper alternative is
[environments.md](environments.md).

## Status

Not built. The design below is settled; the measurements are not taken.

## Why the image can be close

The CoWork image is Ubuntu 22.04.5 (jammy), and every recorded non-Python version is the
version jammy ships: pandoc 2.9.2.1, tesseract 4.1.1, ImageMagick 6.9.11-60, ffmpeg 4.4.2,
poppler-utils 22.02.0, ghostscript 9.55.0, qpdf 10.6.3, git 2.34.1, OpenJDK 11.0.31,
Python 3.10.12. `apt-get install` from jammy therefore reproduces them exactly.

Three things do not come from jammy apt, and each has one source:

| Component       | Recorded | jammy apt | Source                                                      |
| --------------- | -------- | --------- | ----------------------------------------------------------- |
| LibreOffice     | 26.2.5.2 | 7.3       | The upstream LibreOffice `.deb` archive, pinned to 26.2.5.2 |
| Node.js         | 22.23.2  | 12        | NodeSource 22.x, pinned                                     |
| Python packages | 136 pins | n/a       | `pip install -r docs/data/requirements.txt`                 |

The container installs the **full** 136 pins, not the 127 the local mirror manages. The nine
that cannot build on a laptop are Ubuntu system packages and install normally on jammy.
That is the fidelity gain over the mirror, and the reason the container exists.

## Architecture

The recorded image is `aarch64`. `--platform linux/arm64` matches it natively on an ARM Mac
and needs qemu emulation elsewhere, which is correct but several times slower.

The build takes `--platform` from `EVAL_PLATFORM`, default `linux/arm64`. The parity report
records the platform actually used, so an x86 run is never mistaken for an aarch64 one.

## Credentials

The container authenticates with `ANTHROPIC_API_KEY`, passed at run time with
`--env ANTHROPIC_API_KEY`.

- Never bake a credential into an image layer.
- Never mount the host `~/.claude` or `~/.claude.json`. The harness copies credentials into
  its own per-run sandbox, and mounting the host profile puts a live OAuth token inside a
  container that runs author-supplied prompts.
- API key auth cannot publish a report to claude.ai. The runner passes `--no-publish`
  anyway, so nothing changes.

The runner exits 2 with that reason when `ANTHROPIC_API_KEY` is unset.

## Mounts

| Host path            | Container path  | Mode | Why                                            |
| -------------------- | --------------- | ---- | ---------------------------------------------- |
| `plugins/`           | `/work/plugins` | ro   | The plugins under test                         |
| `scripts/`           | `/work/scripts` | ro   | The runner                                     |
| `logs/evals/<stamp>` | `/work/logs`    | rw   | The only path the run may write outside `/tmp` |

Read-only everywhere except the log directory. A case that writes into the repository is a
defect and must fail rather than succeed quietly.

The container runs as a non-root user with the host user's numeric uid and gid, so log files
are not created root-owned.

## Image tagging

The image is tagged `cowork-evals:<sha256 of the requirements file, first 12>` and also
`cowork-evals:latest`. The content-addressed tag means a requirements change cannot be
served from a stale image.

## Parity

`scripts/parity.py` probes the container and compares it against [runtime.md](runtime.md):
the OS release, the architecture, every version in the two tool tables, the font family
count, and the full pip freeze against `data/requirements.txt`.

| Delta            | Result                    | Why                                                              |
| ---------------- | ------------------------- | ---------------------------------------------------------------- |
| Python pin       | exit 1                    | It changes what a skill can import                               |
| Non-Python tool  | printed, does not fail    | A jammy point release moves a patch version and must not block   |

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
| Non-Python deltas                   | not yet measured |
| Font families in the image          | not yet measured |
| Smoke case, container, wall clock   | not yet measured |
