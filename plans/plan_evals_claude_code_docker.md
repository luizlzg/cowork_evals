# Plan: evals on Claude Code, in Docker

Build the container that reproduces the CoWork image, and run the eval runner inside it.

The design is [docs/docker.md](../docs/docker.md): why jammy reproduces the recorded
versions, the three non-apt sources, the architecture choice, the credential rule, the
mounts, the tagging scheme and the parity policy. Read it. This plan builds it and is then
deleted. Anything durable this plan learns goes into that page before the plan is removed.

Also read: [docs/runtime.md](../docs/runtime.md) for the inventory to match, and
[docs/running_evals.md](../docs/running_evals.md) for the runner it hosts.

**Depends on the mirrored-venv plan.** That work owns the case layout, the runner flags, the
gate and the log layout. This plan changes only where the runner executes. Do not start it
before that work merges.

Branch `evals-docker`, off `main`.

## Scope

| In scope                                        | Out of scope                          |
| ----------------------------------------------- | ------------------------------------- |
| The Dockerfile and the build script             | The case layout, the gate, the logs   |
| The parity check                                | An eval case for a real skill         |
| Running the existing runner in the container    | A CI job. Nothing here runs on CI     |
| Credential handling for a containerised run     | Driving CoWork                        |
| Documentation and tests                         |                                       |

## Phases

Follow the execution discipline in [README.md](README.md): one box, verified, ticked,
committed, before the next.

### Phase A: the image

- [ ] Write `docker/Dockerfile`: `FROM ubuntu:22.04`, the jammy apt set covering every
      component in the two tool tables of `docs/runtime.md` plus the Ubuntu font packages,
      LibreOffice from the upstream archive, Node.js from NodeSource, and the full 136 pins.
- [ ] Add `docker/.dockerignore` excluding `.venv`, `.venv_cowork`, `logs`, `.git`.
- [ ] Write `scripts/docker_build.sh` with the tagging scheme in `docs/docker.md`.
- [ ] Build it. Record the image size and both build times in `docs/docker.md`.
- [ ] Write `scripts/parity.py` to the gating policy in `docs/docker.md`, and run it inside
      the image.
- [ ] Fix every Python pin mismatch, then record the remaining non-Python deltas, the font
      family count and the platform built in `docs/docker.md`.

**Gate:** the image builds, `scripts/parity.py` exits 0, and the recorded deltas are
non-Python only.

### Phase B: running the harness inside it

- [ ] Add the Claude Code CLI to the image, pinned to the version recorded in
      `docs/plugin_eval.md`, and confirm `claude --version` reports it.
- [ ] Confirm `claude plugin eval` is enabled inside the container by running
      `docs/claude_code/eval_smoke/run.sh` there. A container cannot fetch server-side
      flags, so `CLAUDE_CODE_WALNUT_SPIRE=1` is expected to be required. Record the result
      in `docs/docker.md`.
- [ ] Write `scripts/eval_docker.sh <plugin>[/<skill>] [flags...]`: refuse without
      `ANTHROPIC_API_KEY`, create the host log directory, then run `scripts/eval.sh` inside
      the container with the mounts and uid mapping in `docs/docker.md`.
- [ ] Run `scripts/eval_docker.sh smoke/probe --allow-tools Bash`. It must exit 0 and its
      interpreter grader must report 3.10.
- [ ] Confirm the host log directory holds the same six artefacts as a local run, owned by
      the host user and not by root.
- [ ] Confirm the run did not modify `plugins/`: `git status` is clean.
- [ ] Write `scripts/eval_docker_all.sh`, reusing the same gate and cost ceilings.
- [ ] Record the container smoke case wall clock in `docs/docker.md` and in the cost table
      of `docs/running_evals.md`, beside the local number, so the slowdown is a measurement
      and not a claim.

**Gate:** the smoke case passes inside the container, log files are host-owned, the
repository is unmodified, and the sweep script runs.

### Phase C: close out

- [ ] Write `tests/test_parity.py` over recorded probe output in `tests/data/`: a pin
      mismatch exits 1, a tool version delta exits 0 and prints, a malformed probe exits 1.
- [ ] Write `tests/test_eval_docker.py` asserting the constructed command line: the mount
      list, the read-only flags, the uid mapping, and the refusal without a credential. Do
      not start a container in a test.
- [ ] Re-read `docs/docker.md` end to end. Every statement must be true of the built image,
      the status line updated, every measurement filled.
- [ ] Run every command in `docs/docker.md` and confirm each behaves as written.
- [ ] Add the container rows to `scripts/README.md`, and set the container runner to yes in
      the status table of `docs/running_evals.md`.
- [ ] Apply the public repository check in the root `README.md` to every file this plan
      added, the Dockerfile and any recorded probe output included.
- [ ] Confirm nothing outside `plans/` links to this plan, delete it, and remove its
      row from `plans/README.md`.

**Gate:** `docs/docker.md` describes a built image with no unfilled row, every command in it
was run, tests and lint are clean, and this file is deleted.
