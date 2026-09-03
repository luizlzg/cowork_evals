# CoWork Evals

The purpose of this repository is to create a system where we can run evals for Claude CoWork. 

There are two "typical" setups we analyze:
1. Claude Code: Running evals on a Claude Code. 
2. Run the evals on Claude Code directly

## Claude Code: Running evals on a Claude Code. 
- Advantage: This serves as a simple proxy for the Evals that would run on CoWork. 
- Problem: This approach is that, in a real co-work environment, the virtual machine has a different setup than our local develpment laptops, so Claude Code is not exactly the same as the CoWork environment.
- Solution 1 "venv": We can mitigate by setting up a virtual environment which is similar to the one that CoWork uses. Nevertheless there are some limitations, CoWork uses Ubuntu, and if you're developing on another laptop such as a Macintosh, then the setup will be different. 
- Solution 2 "Docker": Another approach is to use Docker to create a container that closely mirrors the CoWork environment. This can help ensure consistency across different development setups, regardless of the underlying operating system.

## Run the evals on Claude Code directly
- Advantage: This approach ensures that the evals are run in the actual CoWork environment, providing the most accurate results.
- Problem: As of now, CoWork does not provide a simple mechanism to connect to it and run Evals (that I'm aware of).
- Solution: We connect directly to the internal endpoints so we can run some of these Evals. 


## References

Sourced from an internal marketplace repository, which is not public. Absolute paths
redacted: this repository is public. The content that mattered was adapted into `docs/`.

| Source document            | Adapted into                            |
| -------------------------- | --------------------------------------- |
| `dev/environment.md`       | `docs/environments.md`                  |
| `dev/runtime.md`           | `docs/runtime.md`                       |
| `dev/data/requirements*`   | `docs/data/requirements*`               |
| `plan_evals_claude_code.md`| `docs/plugin_eval.md`, the venv plan    |
| `plan_run_cowork.md`       | `docs/cowork_desktop.md`, the CoWork plan |

## Tasks

Perform each task, mark them as completed immediately after done so we can continue at any point (we'll clear context often):

- [x] Create a directory structure for this project
  - [x] Create a lean CLAUDE.md

- [x] Documentation: `docs/`
  - [x] Create a 'docs' directory for documentation
  - [x] Copy the documentation into the 'docs' directory (at least the refered documents, but bring other documents if needed, e.g. list of packages used by CoWork's VM)
  - [x] Adapt the documentation, add `docs/README.md` which will be the index of the documentation
  - [x] Verify nothig personal, or company specific is in the documentation (redact any usernames, email addresses, or other sensitive information)

- [x] Create a venvs: 
  - [x] `venv`: The virtual environment for this repository (dir `.venv`)
  - [x] `venv_cowork`: The virtual environment that mirrors the CoWork environment (dir `.venv_cowork`)

- [x] Create plans:
  - [x] `plans/plan_evals_claude_code_venv_cowork.md`: Plan for running evals on Claude Code, using `venv_cowork`
  - [x] `plans/plan_evals_claude_code_docker.md`: Plan for running evals on Claude Code, using Docker
  - [x] `plans/plan_evals_claude_cowork.md`: Plan for running evals on Claude Cowork directly
  - [x] Update CLAUDE.md & docs accordingly

## Writing plans

- The plans should not repeat the documentation, they should point at it
- The plans must be self contained, and will run with clear context
- Each plan should be complete (no "open decision"), brief (no fluff, no fat, no fille language), STE (use simpleified technical english)
- Plans are implemented in separate branchses (from main) which are later merged back into main
- Testing and documentation should be included in each plan
- Plans should have checklist, which are checked immediately after completed, so we can clear context and restart at any point.

## IMPORTANT considerations

This will be an wide open, public repository (anyone in the planet will be able to see it)
Make sure no personal details are ever included in the repository (redact any usernames, email addresses, or other sensitive information)