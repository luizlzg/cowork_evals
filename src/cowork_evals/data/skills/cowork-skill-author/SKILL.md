---
name: cowork-skill-author
description: 'Authors and reviews Claude CoWork skills and plugins, and checks their code against the CoWork runtime: Python 3.10 and its packages, the installed commands, Node packages and environment variables. TRIGGER when: user says "create a skill", "new skill", "review skill", "check skill", "validate skill", "skill audit", or asks whether plugin code runs in a CoWork session. NOT for writing eval cases, which is cowork-evals.'
---

# CoWork skill author

Authors new skills and reviews existing ones against the Agent Skills spec and against the
CoWork session they run in. A CoWork session is an Ubuntu 22.04 aarch64 VM with Python
3.10.12, a fixed set of packages and commands, and 16 environment variables. Code in a skill
uses what is there, and nothing else.

This skill is structural. It scaffolds the plugin and the skill, writes the frontmatter, the
body and the scripts, and checks them. Writing and running eval cases is the `cowork-evals`
skill. Asking a live session a question is the `cowork-ask` skill.

| Reference                   | Holds                                                                |
| --------------------------- | -------------------------------------------------------------------- |
| `references/structure.md`   | The plugin and skill tree, and what each directory is for            |
| `references/frontmatter.md` | Every frontmatter field, and what the description has to do         |
| `references/body.md`        | The `SKILL.md` body and its progressive-disclosure budget            |
| `references/cli.md`         | The shell wrapper and the Python package, for a skill with code      |
| `references/runtime.md`     | Python, commands, Node and environment variables in a CoWork session |
| `references/pip_freeze.txt` | `pip freeze` in a session: every Python package and its version      |
| `references/checklist.md`   | The review checklist, sections A to H                                |

## Does it run in a session

Read `references/runtime.md` before writing an import, a command or a variable read. Then
settle it on the Docker image, which reproduces the CoWork image:

```bash
cowork_evals test --docker <plugin>/tests     # the plugin's tests, on the session's Python and packages
cowork_evals run --docker <plugin>/evals      # the skills end to end, in the session environment
```

`test` runs the Python the tests reach, on the session's interpreter and packages. `run` gives
every `Bash` call the session's commands and environment variables. Code that neither reaches
is not checked by either.

## Author a new skill

1. Gather requirements: what the skill does, whether it needs scripts, what triggers it, and
   what must not trigger it.
2. Scaffold the plugin shell if the plugin does not exist, per `references/structure.md`:
   `.claude-plugin/plugin.json`, `skills/`, and `agents/`, `commands/` or `hooks/` only when
   used, `tests/` for the plugin's pytest suite, and `evals/<skill>/` for its eval cases.
3. Scaffold the skill directory, `<plugin>/skills/<skill>/`, per `references/structure.md`.
4. Write `SKILL.md`: frontmatter per `references/frontmatter.md`, body per
   `references/body.md`.
5. If the skill has scripts, write the wrapper and the package per `references/cli.md`, and
   keep every import, command and variable within `references/runtime.md`. Nothing installs
   at run time.
6. If the skill carries code, write its tests in `<plugin>/tests/` and run them with
   `cowork_evals test --docker <plugin>/tests`.
7. Write the eval cases in `<plugin>/evals/<skill>/`: at least a case where the skill fires
   and a case where it must not. The `cowork-evals` skill holds the format.
8. Run `references/checklist.md`. Fix every failure before reporting done.

## Review an existing skill

1. Identify the target: a skill name, or every skill in the plugin.
2. Locate the plugin shell: the `.claude-plugin/plugin.json` above the skill, the plugin's
   `tests/`, and `evals/<skill>/`. A skill under no plugin cannot be installed.
3. Run `references/checklist.md`, every applicable item, A to H. Read the files. Items outside
   the skill directory, the tests, the evals and the manifest, are the ones a listing of the
   skill does not show.
4. Run `cowork_evals test --docker <plugin>/tests`.
5. Report a pass and fail table by section. For each failure, state what is wrong and the
   fix. Report warnings apart from failures: a warning is a question, not a defect.
6. Apply the fixes the user asks for, then run the checklist and the tests again.

## Rules

- The Agent Skills spec is https://agentskills.io/specification.
- Measure the description: `echo -n '<description>' | wc -c`.
- For a skill with scripts, run the wrapper: `<wrapper> --help` exits 0.
- `claude plugin validate <plugin> --strict` checks the manifests and that each `SKILL.md`
  frontmatter parses. It reads no frontmatter field and nothing outside the manifests.
- When a question about the session is still open, `cowork_evals ask --cowork` settles it:
  ask the session to run the import or the command, and read what it did.
