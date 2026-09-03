# Approaches

Three ways to run an eval against a CoWork skill. They answer different questions. None
replaces another.

| Approach                   | Runs on                      | Proves                                     | Design                                  |
| -------------------------- | ---------------------------- | ------------------------------------------ | --------------------------------------- |
| Claude Code, mirrored venv | Local `claude`, Python 3.10  | Skill logic, activation, hook gates        | [running_evals.md](running_evals.md)    |
| Claude Code, Docker        | Local `claude`, Ubuntu 22.04 | The above plus rendering, OCR, fonts, CLIs | [docker.md](docker.md)                  |
| CoWork, driven directly    | The real CoWork VM           | The deployed stack, end to end             | [cowork_driver.md](cowork_driver.md)    |

## Claude Code as a proxy for CoWork

`claude plugin eval` loads one plugin into a fresh isolated session, runs each case, and
scores it with graders. It is the only harness that knows how to load a plugin, so it is the
harness this repository uses. See [plugin_eval.md](plugin_eval.md).

What it gets right: the skill files under test are the ones that ship, activation is decided
by the real model, and hook gates fire.

What it gets wrong: it is not CoWork. Different model routing, no admin-applied enterprise
prompt, no CoWork MCP servers, and the host is a development laptop rather than an Ubuntu
22.04 aarch64 VM. See [runtime.md](runtime.md) for the size of that gap.

Two ways to narrow the host half of the gap:

**The mirrored virtual environment.** `.venv_cowork` pins Python 3.10 and the exact wheel
set a session provides. It catches an import that does not exist on the image and an API
that changed between versions. It reproduces the interpreter and the wheels and nothing
else, so on macOS the OS, the architecture, LibreOffice, ImageMagick, pandoc, tesseract and
the font stack all still differ. Cheap, fast, and the default.

**Docker.** A container built from `ubuntu:22.04` with the same interpreter, the same
wheels, and the same document, image and OCR tooling. It closes the OS, CLI and font gap
regardless of the developer's laptop. On an ARM Mac it also matches the aarch64
architecture. It costs an image build and a slower run, so it is the pre-release gate rather
than the iteration loop.

## CoWork, driven directly

The most accurate result, because it is the deployed stack. CoWork exposes no scriptable
entry point, so the only route is to drive the desktop application: submit a prompt through
its `claude://` URL scheme, press Return with a synthetic keystroke, and read the
transcript, audit log and outputs the session writes to the host filesystem. See
[cowork_desktop.md](cowork_desktop.md).

The costs are real and are not reduced by better engineering:

- It couples to application internals that no release promises to keep.
- It needs a macOS Accessibility grant, so it cannot run headless or on CI.
- It drives a live signed-in account, so a case can reach real mail and real documents.
- Every run leaves a permanent session in that account's history.
- One case costs a VM boot plus a full agentic run, so a sweep is minutes per case.

It is the pre-release confirmation, run by a person on purpose. It is never a commit gate.

## Which to use when

| Moment              | Approach                                                    |
| ------------------- | ----------------------------------------------------------- |
| Writing a case      | Claude Code, mirrored venv, one case, one run               |
| Before opening a PR | Claude Code, mirrored venv, the touched plugin's full suite |
| Before a release    | Docker for every plugin, then CoWork for a smoke set        |
