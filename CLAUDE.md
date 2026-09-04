# CLAUDE.md

`cowork_evals`: a system for running evals against Claude CoWork skills and plugins.
`README.md` says what it is, and `docs/` says how it works.

## Where things are written

Each directory has a `README.md` that indexes it and owns the rules for it. Read the index
before changing anything under it. Never restate one of these in another file; link to it.

| Index               | Owns                                                     |
| ------------------- | -------------------------------------------------------- |
| `README.md`         | What the repo is, and the public repository rule         |
| `docs/README.md`    | Reference material: boundary, command, runtime, harness  |
| `plans/README.md`   | How a plan is structured and executed                    |
| `plugins/README.md` | The fixture plugins, and what they are not               |
| `scripts/README.md` | Every development task, and the shell conventions        |
| `tests/README.md`   | What is a test here, and what is not                     |

## Working rules

- **This is a library, not a consumer.** No eval for a shipped plugin is written here. The
  repository that owns the plugins installs this package and points it at its own tree.
  `plugins/` holds fixtures for this repository's own tests, nothing more. See
  `docs/library.md`.
- **One command.** Everything a consumer does goes through `cowork_evals`, and a consumer
  never invokes `claude plugin eval`. Never add a second entry point or a per-backend
  executable. The surface is `docs/cli.md`.
- **Shipped code is a Python package** under `src/cowork_evals/`: standard library only, no
  runtime dependencies, and 3.10 compatible because it is somebody else's development
  dependency. **Development tasks are shell scripts** under `scripts/`, are never shipped,
  and have no build system and no Makefile.
- **One case format, three backends.** Every eval is written in the `claude plugin eval`
  case format, and the same case tree runs on the mirrored venv, in Docker, and on CoWork.
  Never add a second format or a per-backend variant of a case. The format is
  `docs/eval_format.md`. Which backend honours which field is `docs/approaches.md`.
- **Two environments, never mixed.** `.venv` is Python 3.14 repository tooling. Code that
  must behave like a CoWork session runs under the 3.10 CoWork mirror through
  `scripts/cowork_run.sh`. Never run `uv run` under the mirror. See
  `docs/environments.md`.
- **A plan is the state while it exists.** Tick a box only when it is verified, then
  commit. Do not batch ticks. A cleared context resumes from the plan file.
- **A plan is deleted once implemented, so nothing durable may live only in one.** A plan
  links to `docs/`. Documentation never links to a plan. Anything a plan establishes that
  outlives the work is written into `docs/` before the plan is removed.
- NEVER sign commits or PRs as Claude.

## Writing rules

These apply to every file in the repository: documentation, plans, comments, commit
messages.

Audience is expert engineers and Claude Code. Readers build Claude Code plugins for a
living. They know what a skill, plugin, command, agent, hook, MCP server, context window,
LLM, test and CI are, and they have read the official Claude Code documentation. Assume all
of it.

- Never define a term.
- Never motivate a practice. State it.
- Simplified Technical English. No filler, no corporate register.
- One idea per sentence. Tables for anything with more than two attributes.
- State what is true of this repository, and verify before writing.
- Record the capture date of any measured fact, and call it a snapshot.
- Sentence case headings. No emojis, no em dashes.
